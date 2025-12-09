from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import db
from handlers_main import get_back_main_keyboard

router = Router()
HISTORY_PAGE_SIZE = 5

# --- Helper: generate referral link ---
def generate_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

# --- Invite Friends Menu ---
def get_invite_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Referral History"), KeyboardButton(text="🔗 Share Link")],
            [KeyboardButton(text="🔙 Main Menu")]
        ],
        resize_keyboard=True
    )

@router.message(F.text == "👥 Invite Friends")
async def referral_system(message: Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    referral_link = generate_referral_link(bot_info.username, user_id)
    stats = await db.get_user_stats(user_id)

    text = (
        "👥 <b>Invite Your Friends!</b> 🔥\n\n"
        "Earn <b>50🪙</b> for every friend who joins using your link.\n\n"
        f"📊 You’ve referred: <b>{stats.get('referrals', 0)}</b> friends\n\n"
        f"🔗 Your referral link:\n{referral_link}\n\n"
        "Share it everywhere and grow your coin stash! 📢"
    )

    # Inline keyboard for one‑tap share
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔗 Share Link",
                switch_inline_query=(
    "🔥 I’m on AAUPulse — the heartbeat of campus love 🔥\n\n"
    "It’s where AAU students shoot their shot 😏\n"
    "Swipe your vibe. Match your crush. Start your story 💕\n\n"
    f"👉 Join through my link and let’s vibe together:\n{referral_link}\n\n"
    "Your match might already be waiting 👀 Don’t sleep on it."
)

            )
        ]
    ])

    # First message: stats + inline share button
    await message.answer(text, reply_markup=inline_kb, parse_mode="HTML")

    # Second message: persistent reply keyboard for navigation
    await message.answer("⬇️ Use the menu below to navigate:", reply_markup=get_invite_keyboard())


# --- Referral History Rendering ---
async def render_referral_history(user_id: int, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    history = await db.get_referrals(user_id, offset=page*HISTORY_PAGE_SIZE, limit=HISTORY_PAGE_SIZE+1)

    if not history:
        return "📭 <b>No referrals yet!</b>\nShare your link to start earning coins.", InlineKeyboardMarkup(inline_keyboard=[])

    text = "📜 <b>Your Referral History</b>\n\n"
    for row in history[:HISTORY_PAGE_SIZE]:
        referred_id = row["referred_id"]
        created = row["created_at"]
        text += f"👤 User ID: {referred_id} — +50🪙\n<span class='tg-spoiler'>{created}</span>\n\n"

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"ref_history_{page-1}"))
    if len(history) > HISTORY_PAGE_SIZE:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"ref_history_{page+1}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
    return text, keyboard

# --- Entry point from reply keyboard ---
@router.message(F.text == "📜 Referral History")
async def show_referral_history_message(message: Message):
    text, keyboard = await render_referral_history(message.from_user.id, page=0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# --- Pagination via inline buttons ---
@router.callback_query(F.data.startswith("ref_history_"))
async def show_referral_history_callback(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    text, keyboard = await render_referral_history(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()



@router.message(F.text == "🔗 Share Link")
async def share_referral_link(message: Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    text = (
    "🔥 I’m on AAUPulse — the heartbeat of campus love 🔥\n\n"
    "It’s where AAU students shoot their shot 😏\n"
    "Swipe your vibe. Match your crush. Start your story 💕\n\n"
    f"👉 Join through my link and let’s vibe together:\n{referral_link}\n\n"
    "Your match might already be waiting 👀 Don’t sleep on it."
)


    # Send the cinematic invite text back to the user so they can forward it
    await message.answer(
        "📢 Forward this message to your friends and groups to invite them:",
        parse_mode="HTML"
    )
    await message.answer(text, parse_mode="HTML")
