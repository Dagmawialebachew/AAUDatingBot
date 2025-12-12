# handlers_admin.py
# Unified, paste-ready admin panel with FSM, pagination, broadcast,
# and fully integrated ban/unban flows (with templates, notes, and unban requests).

import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from handlers_main import get_main_menu_keyboard
import logging
from datetime import date
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID, COIN_REWARDS
from database import db
from services.content_builder import build_match_drop_text
from services.match_queue_service import MatchQueueService
router = Router()

logger = logging.getLogger(__name__)

# --- Admins ---
ADMIN_IDS = [1131741322]  # add more admin user IDs as needed

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- FSM States ---
class AdminBroadcastFSM(StatesGroup):
    waiting_text = State()
    confirm_send = State()

class AdminModerationFSM(StatesGroup):
    waiting_user_id = State()
    waiting_action = State()       # "ban" or "unban"
    waiting_reason = State()       # note/reason (template or custom)
    confirm_action = State()

class AdminUserListFSM(StatesGroup):
    browsing_page = State()        # page index (int)


# --- Constants and helpers ---
USERS_PER_PAGE = 5

BAN_TEMPLATES = [
    "Spam or promotional content",
    "Explicit or inappropriate profile photo",
    "Harassment or offensive language",
    "Fake or misleading identity",
    "Solicitation or scams",
]

UNBAN_TEMPLATES = [
    "Issue resolved; please follow community guidelines",
    "Warning lifted; keep it respectful",
    "Appeal accepted; thanks for your patience",
    "We reviewed and reinstated access",
]


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Confessions"), KeyboardButton(text="📊 Stats")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="👥 User Management")],
            [KeyboardButton(text="🗂️ Browse Users"), KeyboardButton(text="⚙️ Scheduler Controls")],
            [KeyboardButton(text="🔙 Exit Admin Mode")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🔐 Admin controls..."
    )

def user_card_text(u: dict) -> str:
    username = f"@{u['username']}" if u.get("username") else "—"
    banned = "🚫 BANNED" if u.get("is_banned") else "✅ Active"
    campus = u.get("campus") or "—"
    dept = u.get("department") or "—"
    year = u.get("year") or "—"
    bio = u.get("bio") or ""
    bio_line = f"💭 “{bio}”" if bio else "💭 No bio yet"
    coins = u.get("coins", 0)
    return (
        f"─────────────── ✨ ───────────────\n"
        f"🆔 {u['id']} • {banned}\n"
        f"👤 {u.get('name','Unknown')} ({username})\n"
        f"📍 {campus} | {dept}\n"
        f"🎓 {year}\n\n"
        f"{bio_line}\n"
        f"💰 Coins: {coins}"
    )

def get_user_admin_kb(user_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⛔ Ban", callback_data=f"admin_ban_{user_id}_{page}"),
            InlineKeyboardButton(text="✅ Unban", callback_data=f"admin_unban_{user_id}_{page}"),
        ],
        [InlineKeyboardButton(text="🔎 View full row", callback_data=f"admin_view_{user_id}_{page}")],
        [InlineKeyboardButton(text="⬅️ Prev Page", callback_data=f"users_page_{page-1}"),
         InlineKeyboardButton(text="➡️ Next Page", callback_data=f"users_page_{page+1}")]
    ])

def get_ban_templates_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=reason, callback_data=f"mod_note_{reason}")]
            for reason in BAN_TEMPLATES[:4]]
    rows.append([InlineKeyboardButton(text=BAN_TEMPLATES[4], callback_data=f"mod_note_{BAN_TEMPLATES[4]}")])
    rows.append([InlineKeyboardButton(text="✍️ Custom note", callback_data="mod_note_custom")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="mod_note_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_unban_templates_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=reason, callback_data=f"mod_note_{reason}")]
            for reason in UNBAN_TEMPLATES[:4]]
    rows.append([InlineKeyboardButton(text="✍️ Custom note", callback_data="mod_note_custom")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="mod_note_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Entry Point ---
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Admin only!")
        return
    await message.answer("🔐 Welcome to the Admin Panel", reply_markup=get_admin_main_menu())


# --- Exit Admin Mode ---
@router.message(F.text == "🔙 Exit Admin Mode")
async def exit_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Exited admin mode.", reply_markup=get_main_menu_keyboard())


# --- Confessions Panel ---
def get_confessions_panel(confession_id: int = None) -> InlineKeyboardMarkup:
    if confession_id:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_conf_{confession_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_conf_{confession_id}")
            ],
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])

@router.message(F.text == "📋 Confessions")
async def admin_confessions_menu(message: Message):
    if not is_admin(message.from_user.id):
        return

    confessions = await db.get_pending_confessions()
    if not confessions:
        await message.answer("✅ No pending confessions.", reply_markup=get_admin_main_menu())
        return
    from handlers_confession import CONFESSION_TEMPLATES

    confession = confessions[0]
    campus = confession.get("campus", "Unknown")
    department = confession.get("department", "Unknown")
    text = confession["text"]

    # 🔀 Pick template based on known/unknown fields
    if campus == "Unknown" and department == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["fully_anon"])
    elif campus == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["anon_campus"])
    elif department == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["anon_dept"])
    else:
        template = random.choice(CONFESSION_TEMPLATES["known"])

    formatted_text = template.format(
        id=confession["id"],
        campus=campus,
        department=department,
        text=text
    )

    review_text = (
        f"📋 Confession Review (ID: {confession['id']})\n\n"
        f"{formatted_text}\n\n"
        f"Pending confessions: {len(confessions)}"
    )

    await message.answer(review_text, reply_markup=get_confessions_panel(confession['id']))


@router.callback_query(F.data.startswith("approve_conf_"))
async def approve_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")

    confession_id = int(callback.data.split("_")[-1])
    confession = await db.get_confession(confession_id)
    from handlers_confession import CONFESSION_TEMPLATES
    if not confession:
        return await callback.answer("Confession not found 💀")

    campus = confession.get("campus", "Unknown")
    department = confession.get("department", "Unknown")
    text = confession["text"]

    # 🔀 Pick template based on known/unknown fields
    if campus == "Unknown" and department == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["fully_anon"])
    elif campus == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["anon_campus"])
    elif department == "Unknown":
        template = random.choice(CONFESSION_TEMPLATES["anon_dept"])
    else:
        template = random.choice(CONFESSION_TEMPLATES["known"])

    channel_text = template.format(
        id=confession_id,
        campus=campus,
        department=department,
        text=text
    )

    try:
        sent = await callback.bot.send_message(CHANNEL_ID, channel_text)
        await db.update_confession_status(confession_id, "approved", sent.message_id)

        # 🪙 Add coins after approval
        reward = COIN_REWARDS.get("confession", 5)
        try:
            await db.add_coins(
                    confession["sender_id"],
                    reward,
                    tx_type="confession",
                    description=f"Confession #{confession_id} approved"
                )
            # Notify user privately
            await callback.bot.send_message(
                confession["sender_id"],
                f"✅ Your confession #{confession_id} was approved!\n\n"
                f"🪙 +{reward} coins have been added to your balance.\n\n"
                "Check out @AAUPulse to see it live!"
            )
        except Exception as e:
            logger.warning(f"Could not add coins or notify user: {e}")

        await callback.message.edit_text(
    f"✅ Confession #{confession_id} approved.\n\n"
    f"{callback.message.text}"
)

        await callback.message.edit_reply_markup(reply_markup=None)

        await callback.answer("Approved!")
    except Exception as e:
        logger.error(f"Error posting confession: {e}")
        await callback.answer("Failed to post 💀")

# --- Stats Panel ---
@router.message(F.text == "📊 Stats")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = await db.get_global_stats()
    text = (
        f"📊 Bot Statistics\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"✅ Active Users: {stats['active_users']}\n"
        f"🔥 Total Matches: {stats['total_matches']}\n"
        f"💌 Total Confessions: {stats['total_confessions']}\n"
        f"⏳ Pending Confessions: {stats['pending_confessions']}\n"
    )
    await message.answer(text, reply_markup=get_admin_main_menu())



REJECT_REASONS = {
    "spam": "❌ Your confession was rejected because it looked like spam or irrelevant content.",
    "offensive": "❌ Your confession contained offensive or inappropriate language.",
    "duplicate": "❌ Your confession was rejected because it was a duplicate of an earlier one.",
    "low_quality": "❌ Your confession didn’t meet the quality guidelines (too short, unclear, etc.).",
    "other": "❌ Your confession was rejected by the admins."
}



@router.callback_query(F.data.startswith("reject_conf_"))
async def reject_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")

    confession_id = int(callback.data.split("_")[-1])
    confession = await db.get_confession(confession_id)
    if not confession:
        return await callback.answer("Confession not found 💀")

    # Update DB status
    await db.update_confession_status(confession_id, "rejected")

    # Build reason keyboard
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Spam", callback_data=f"reject_reason_spam_{confession_id}"),
            InlineKeyboardButton(text="🗑 Offensive", callback_data=f"reject_reason_offensive_{confession_id}")
        ],
        [
            InlineKeyboardButton(text="📋 Duplicate", callback_data=f"reject_reason_duplicate_{confession_id}"),
            InlineKeyboardButton(text="⚠️ Low Quality", callback_data=f"reject_reason_low_quality_{confession_id}")
        ],
        [InlineKeyboardButton(text="❓ Other", callback_data=f"reject_reason_other_{confession_id}")]
    ])

    await callback.message.edit_text(
        f"❌ Confession #{confession_id} rejected.\n\nPick a reason to notify the user:",
        reply_markup=kb
    )
    await callback.answer("Marked as rejected")


@router.callback_query(F.data.startswith("reject_reason_"))
async def reject_reason(callback: CallbackQuery):
    parts = callback.data.split("_")
    reason_key = parts[2]
    confession_id = int(parts[-1])

    confession = await db.get_confession(confession_id)
    if not confession:
        return await callback.answer("Confession not found 💀")

    reason_text = REJECT_REASONS.get(reason_key, REJECT_REASONS["other"])

    try:
        await callback.bot.send_message(
            confession["sender_id"],
            f"{reason_text}\n\nConfession #{confession_id}."
        )
    except Exception as e:
        logger.warning(f"Could not notify user of rejection: {e}")

    await callback.message.edit_text(
        f"❌ Confession #{confession_id} rejected and user notified.\nReason: {reason_key}"
    )
    await callback.answer("User notified ✅")

# --- Broadcast with FSM & confirmation ---
@router.message(F.text == "📢 Broadcast")
async def broadcast_prompt(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminBroadcastFSM.waiting_text)
    await message.answer("✍️ Send the broadcast message (HTML allowed).")

@router.message(AdminBroadcastFSM.waiting_text)
async def broadcast_preview(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(text=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm Send", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="broadcast_cancel")]
    ])
    await message.answer(f"Preview:\n\n{text}", reply_markup=kb, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_send(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    data = await state.get_data()
    text = data.get("text", "")
    user_ids = await db.get_all_active_user_ids()
    success, fail = 0, 0
    for uid in user_ids:
        try:
            await callback.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            success += 1
        except Exception:
            fail += 1
    await state.clear()
    await callback.message.answer(f"✅ Broadcast complete!\nSuccess: {success}\nFailed: {fail}")
    await callback.answer("Sent")

@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Broadcast canceled.")
    await callback.answer()


# --- User Management menu ---
def get_user_management_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Ban / ✅ Unban", callback_data="admin_mod_enter")],
        [InlineKeyboardButton(text="🗂️ Browse Users", callback_data="admin_browse_enter")],
        [InlineKeyboardButton(text="🗑️ Delete User", callback_data="admin_user_delete")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])

@router.message(F.text == "👥 User Management")
async def user_management_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👥 User Management Panel", reply_markup=get_user_management_panel())

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.answer("🔐 Back to Admin Menu", reply_markup=get_admin_main_menu())
    await callback.answer()


# --- Browsing Users ---
@router.callback_query(F.data == "admin_browse_enter")
async def browse_users_entry_cb(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    await state.set_state(AdminUserListFSM.browsing_page)
    await state.update_data(page=0)
    await show_users_page(callback, page=0)
    await callback.answer()

@router.message(F.text == "🗂️ Browse Users")
async def browse_users_entry(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminUserListFSM.browsing_page)
    await state.update_data(page=0)
    await show_users_page(message, page=0)

async def show_users_page(target, page: int):
    total = await db.count_users()
    page = max(0, page)
    offset = page * USERS_PER_PAGE
    users = await db.get_users_page(offset=offset, limit=USERS_PER_PAGE)

    chat_id = target.message.chat.id if hasattr(target, "message") else target.chat.id

    if not users:
        await target.bot.send_message(chat_id, f"No users on page {page+1}.")
        return

    for u in users:
        caption = user_card_text(u)
        kb = get_user_admin_kb(u["id"], page)
        try:
            if u.get("photo_file_id"):
                await target.bot.send_photo(
                    chat_id=chat_id,
                    photo=u["photo_file_id"],
                    caption=caption,
                    reply_markup=kb,
                    parse_mode=ParseMode.HTML
                )
            else:
                await target.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=kb,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Admin page send error for user {u.get('id')}: {e}")
            await target.bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=kb,
                parse_mode=ParseMode.HTML
            )

    pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    nav_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Prev", callback_data=f"users_page_{page-1}"),
         InlineKeyboardButton(text="➡️ Next", callback_data=f"users_page_{page+1}")]
    ])
    await target.bot.send_message(chat_id, f"Page {page+1}/{pages}", reply_markup=nav_kb)

@router.callback_query(F.data.startswith("users_page_"))
async def users_page(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    page = int(callback.data.split("_")[-1])
    page = max(0, page)
    await state.update_data(page=page)
    await show_users_page(callback, page)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_view_"))
async def admin_view_full_row(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    _, _, uid, _page = callback.data.split("_")
    uid = int(uid)
    user = await db.get_user(uid)
    if not user:
        return await callback.answer("User not found")
    fields = [
        f"id={user.get('id')}",
        f"username={user.get('username')}",
        f"name={user.get('name')}",
        f"gender={user.get('gender')}",
        f"seeking_gender={user.get('seeking_gender')}",
        f"campus={user.get('campus')}",
        f"department={user.get('department')}",
        f"year={user.get('year')}",
        f"coins={user.get('coins')}",
        f"is_active={user.get('is_active')}",
        f"is_banned={user.get('is_banned')}",
        f"created_at={user.get('created_at')}",
    ]
    await callback.message.answer("🧾 Full row\n" + "\n".join(fields))
    await callback.answer()


# --- Moderation FSM (Ban/Unban with note & confirmation) ---
@router.callback_query(F.data == "admin_mod_enter")
async def moderation_enter(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    await state.set_state(AdminModerationFSM.waiting_user_id)
    await callback.message.answer("Enter user ID:")
    await callback.answer()

@router.message(AdminModerationFSM.waiting_user_id)
async def moderation_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        return await message.answer("Please enter a valid numeric user ID.")
    user = await db.get_user(uid)
    if not user:
        return await message.answer("User not found.")
    await state.update_data(user_id=uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Ban", callback_data="mod_choose_ban"),
         InlineKeyboardButton(text="✅ Unban", callback_data="mod_choose_unban")]
    ])
    await message.answer(user_card_text(user), reply_markup=kb, parse_mode=ParseMode.HTML)

@router.callback_query(F.data.in_(["mod_choose_ban", "mod_choose_unban"]))
async def moderation_choose(callback: CallbackQuery, state: FSMContext):
    action = "ban" if callback.data.endswith("ban") else "unban"
    await state.update_data(action=action)
    await state.set_state(AdminModerationFSM.waiting_reason)

    kb = get_ban_templates_kb() if action == "ban" else get_unban_templates_kb()
    await callback.message.answer("Select a note to send to the user, or choose Custom:", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("mod_note_"))
async def moderation_note_select(callback: CallbackQuery, state: FSMContext):
    note = callback.data.replace("mod_note_", "")
    if note == "custom":
        await callback.message.answer("✍️ Type your custom note:")
        await callback.answer()
        return
    await state.update_data(note=note)
    await show_moderation_preview(callback, state)

@router.callback_query(F.data == "mod_note_back")
async def moderation_note_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = data.get("user_id")
    user = await db.get_user(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Ban", callback_data="mod_choose_ban"),
         InlineKeyboardButton(text="✅ Unban", callback_data="mod_choose_unban")]
    ])
    await callback.message.answer(user_card_text(user), reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.message(AdminModerationFSM.waiting_reason)
async def moderation_reason(message: Message, state: FSMContext):
    note = message.text.strip()
    await state.update_data(note=note)
    await show_moderation_preview(message, state)

async def show_moderation_preview(target, state: FSMContext):
    data = await state.get_data()
    uid = data.get("user_id")
    action = data.get("action")
    note = data.get("note", "")
    user = await db.get_user(uid)

    preview = (
        f"Action: {'⛔ BAN' if action=='ban' else '✅ UNBAN'}\n"
        f"User: {uid} • {user.get('name','Unknown')} (@{user.get('username','—')})\n\n"
        f"📝 Note to user:\n{note}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm", callback_data="mod_confirm")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="mod_cancel")]
    ])

    try:
        await target.message.answer(preview, reply_markup=kb)
    except AttributeError:
        await target.answer(preview, reply_markup=kb)

@router.callback_query(F.data == "mod_cancel")
async def moderation_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Moderation canceled.")
    await callback.answer()

@router.callback_query(F.data == "mod_confirm")
async def moderation_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    data = await state.get_data()
    uid = data["user_id"]
    action = data["action"]
    note = data.get("note", "")

    try:
        if action == "ban":
            # Unified helper (stores note if supported)
            ok = await db.set_user_banned(uid, True)  # change to (uid, True, note) if your helper supports note
            if not ok:
                raise RuntimeError("DB set_user_banned failed")

            try:
                await callback.bot.send_message(uid, f"🚫 You’ve been banned.\n\n📝 Note from admin:\n{note}")
            except Exception:
                pass
            await callback.message.answer(f"User {uid} banned. Note sent.")
        else:
            ok = await db.set_user_banned(uid, False)  # change to (uid, False) plus note as context if you store
            if not ok:
                raise RuntimeError("DB set_user_banned failed")

            card = (
                "✅ You’ve been unbanned\n\n"
                "Here’s the context so you’re informed:\n"
                f"• Previous ban reason: {note}\n\n"
                "Please keep the community respectful. Reach out if you have questions."
            )
            try:
                await callback.bot.send_message(uid, card)
            except Exception:
                pass
            await callback.message.answer(f"User {uid} unbanned. Card sent.")
    except Exception as e:
        logger.error(f"Moderation error: {e}")
        await callback.message.answer("Failed to apply moderation.")

    await state.clear()
    await callback.answer("Done")


# --- Inline ban/unban from the paginated browser (route into FSM) ---
@router.callback_query(F.data.startswith("admin_ban_"))
async def list_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    _, _, uid, _page = callback.data.split("_")
    uid = int(uid)
    await state.set_state(AdminModerationFSM.waiting_reason)
    await state.update_data(user_id=uid, action="ban")
    await callback.message.answer("Select a ban note:", reply_markup=get_ban_templates_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("admin_unban_") & ~F.data.startswith("admin_unban_request_"))
async def list_unban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    _, _, uid, _page = callback.data.split("_")
    uid = int(uid)
    await state.set_state(AdminModerationFSM.waiting_reason)
    await state.update_data(user_id=uid, action="unban")
    await callback.message.answer("Select an unban note:", reply_markup=get_unban_templates_kb())
    await callback.answer()


# --- Delete user (optional; safer to soft-disable) ---
@router.callback_query(F.data == "admin_user_delete")
async def delete_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    await callback.message.answer("Enter user ID to permanently delete: (consider soft disable instead)")
    await callback.answer()

# (intentionally no direct delete implementation to avoid accidents)


# --- Unban request flow (user -> admin group) ---
# In-memory tracker for per-day unban requests
unban_requests_today = {}  # {user_id: {"date": date, "count": int}}

@router.message(F.text == "🙏 Request Unban")
async def request_unban(message: Message):
    user_id = message.from_user.id
    today = date.today()

    # Check and update count
    record = unban_requests_today.get(user_id)
    if record and record["date"] == today:
        if record["count"] >= 2:
            await message.answer("⚠️ You have reached the daily limit of 2 unban requests. Try again tomorrow.")
            return
        record["count"] += 1
    else:
        unban_requests_today[user_id] = {"date": today, "count": 1}

    # Fetch full profile
    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ Could not fetch your profile for review.")
        return

    caption = user_card_text(user)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Unban User", callback_data=f"admin_unban_request_{user_id}")],
        [InlineKeyboardButton(text="❌ Ignore Request", callback_data=f"admin_ignore_request_{user_id}")]
    ])

    # Send to admin group with photo if available
    if user.get("photo_file_id"):
        await message.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=user["photo_file_id"],
            caption=f"📨 Unban request from user {user_id} (@{message.from_user.username or '—'})\n\n{caption}",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
    else:
        await message.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"📨 Unban request from user {user_id} (@{message.from_user.username or '—'})\n\n{caption}",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )

    await message.answer("🙏 Your unban request has been submitted to the admins. Please wait for review.")

@router.callback_query(F.data.startswith("admin_unban_request_"))
async def admin_unban_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    user_id = int(callback.data.split("_")[-1])
    ok = await db.set_user_banned(user_id, False)
    if ok:
        await callback.answer("✅ User unbanned")
        await callback.message.answer(f"User {user_id} has been unbanned.")
        try:
            await callback.bot.send_message(user_id, "✅ Your unban request was approved. Welcome back!")
        except Exception:
            pass
    else:
        await callback.answer("❌ Failed", show_alert=True)

@router.callback_query(F.data.startswith("admin_ignore_request_"))
async def admin_ignore_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    user_id = int(callback.data.split("_")[-1])
    await callback.answer("❌ Request ignored")
    await callback.message.answer(f"Unban request from user {user_id} was ignored.")
    try:
        await callback.bot.send_message(user_id, "❌ Your unban request was reviewed but not approved.")
    except Exception:
        pass



# handlers/admin_handlers.py

from typing import List, Dict, Any, Optional, Set
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services.match_queue_service import MatchQueueService
from services.content_builder import build_match_drop_text
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID
from database import Database  # your DB wrapper / pool type


# --- FSM states ---
class AdminStates(StatesGroup):
    awaiting_delete_id = State()
    awaiting_broadcast_text = State()

# --- Keyboards ---
def get_admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Confessions"), KeyboardButton(text="📊 Stats")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="👥 User Management")],
            [KeyboardButton(text="🗂️ Browse Users"), KeyboardButton(text="⚙️ Scheduler Controls")],
            [KeyboardButton(text="🔙 Exit Admin Mode")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🔐 Admin controls..."
    )

def get_scheduler_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡️ Post Now"), KeyboardButton(text="🗑 Delete Match")],
            [KeyboardButton(text="⏹ Stop Scheduler"), KeyboardButton(text="▶ Start Scheduler")],
            [KeyboardButton(text="📋 List Queue"), KeyboardButton(text="🔙 Back to Admin Menu")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="⚙️ Scheduler controls..."
    )

# In-memory scheduler flag (consider persisting for restarts)
scheduler_running = True

# --- Open scheduler menu (safe delete_reply_markup) ---
@router.message(F.text == "⚙️ Scheduler Controls")
async def open_scheduler_menu(message: Message, bot: Bot):
    # Send the scheduler menu; try to remove reply markup from the user's message if possible
    await message.answer("Scheduler controls:", reply_markup=get_scheduler_menu())
    try:
        # Only attempt to remove markup if the message is editable by the bot
        await message.delete_reply_markup()
    except Exception:
        # Ignore errors (message not editable, already edited, etc.)
        pass

# --- Back to admin menu ---
@router.message(F.text == "🔙 Back to Admin Menu")
async def back_to_admin_menu(message: Message):
    await message.answer("Admin menu:", reply_markup=get_admin_main_menu())

# --- Force-post top due item ---
@router.message(F.text == "⚡️ Post Now")
async def admin_post_now(message: Message, bot: Bot):
    service = MatchQueueService(db, bot)
    items = await service.get_due_items()
    if not items:
        await message.answer("No due matches right now.")
        return

    ranked = sorted(items, key=lambda i: service.compute_score(i), reverse=True)
    item = ranked[0]
    try:
        text = build_match_drop_text(item)
        await bot.send_message(CHANNEL_ID, text)
        await service.mark_sent(item["id"])
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"⚡️ FORCE POSTED\nQueue ID: {item['id']}\nBy: {message.from_user.id}"
        )
        await message.answer(f"Force posted queue ID {item['id']}")
    except Exception as e:
        await service.record_error(item["id"], str(e))
        await message.answer(f"Error posting item {item['id']}: {e}")
        
        
# --- Delete Match (stateful) ---
@router.message(F.text == "🗑 Delete Match")
async def admin_delete_match_prompt(message: Message, state: FSMContext):
    await state.set_state(AdminStates.awaiting_delete_id)
    await message.answer("Send me the Queue ID to delete (or type Cancel):", reply_markup=None)

@router.message(AdminStates.awaiting_delete_id, F.text.lower() == "cancel")
async def admin_delete_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Delete cancelled.", reply_markup=get_scheduler_menu())

@router.message(AdminStates.awaiting_delete_id, F.text.regexp(r"^\d+$"))
async def admin_delete_match_confirm(message: Message, state: FSMContext):
    from bot import bot
    queue_id = int(message.text.strip())
    service = MatchQueueService(db, bot)
    try:
        deleted = await service.delete_item(queue_id)
    except Exception as e:
        await message.answer("Error while deleting. Check logs.", reply_markup=get_scheduler_menu())
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"🟥 DELETE ERROR\nQueue ID: {queue_id}\nError: {e}\nBy: {message.from_user.id}"
        )
        await state.clear()
        return

    if deleted:
        await message.answer(f"✅ Deleted queue item {queue_id}", reply_markup=get_scheduler_menu())
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"🗑 MATCH DELETED\nQueue ID: {queue_id}\nAction by: {message.from_user.id}"
        )
    else:
        await message.answer("❌ Queue item not found.", reply_markup=get_scheduler_menu())
    await state.clear()

@router.message(AdminStates.awaiting_delete_id)
async def admin_delete_invalid(message: Message, state: FSMContext):
    await message.answer("Please send a numeric Queue ID or type Cancel.")

# --- Stop / Start Scheduler ---
scheduler_running = True  # global flag

@router.message(F.text == "⏹ Stop Scheduler")
async def admin_stop_scheduler(message: Message):
    from bot import bot
    global scheduler_running
    scheduler_running = False
    await message.answer("Scheduler stopped.", reply_markup=get_scheduler_menu())
    await bot.send_message(
        ADMIN_GROUP_ID,
        f"⏹ Scheduler stopped by admin {message.from_user.id}"
    )

@router.message(F.text == "▶ Start Scheduler")
async def admin_start_scheduler(message: Message):
    from bot import bot
    global scheduler_running
    scheduler_running = True
    await message.answer("Scheduler started.", reply_markup=get_scheduler_menu())
    await bot.send_message(
        ADMIN_GROUP_ID,
        f"▶ Scheduler started by admin {message.from_user.id}"
    )

# --- List Queue (all pending) ---
@router.message(F.text == "📋 List Queue")
async def admin_list_queue(message: Message):
    from bot import bot
    service = MatchQueueService(db, bot)
    items = await service.get_all_pending()
    if not items:
        await message.answer("Queue is empty.", reply_markup=get_scheduler_menu())
        return

    lines = []
    for i in items[:50]:
        special = i.get("special_type") or "—"
        vibe = i.get("vibe_score") or 0
        next_time = i.get("next_post_time")
        lines.append(f"ID {i['id']} • Vibe {vibe:.0f} • {special} • {next_time}")

    summary = "\n".join(lines)
    await message.answer(
        f"📋 Pending Matches (first {len(lines)}):\n{summary}",
        reply_markup=get_scheduler_menu()
    )
    await bot.send_message(
        ADMIN_GROUP_ID,
        f"📋 Admin {message.from_user.id} viewed queue list."
    )