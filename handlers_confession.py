import random
import logging
from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

from database import db
from bot_config import AAU_CAMPUSES, AAU_DEPARTMENTS, MAX_CONFESSION_LENGTH, COIN_REWARDS

logger = logging.getLogger(__name__)
router = Router()

# ---------- States ----------
class ConfessionState(StatesGroup):
    selecting_campus = State()
    selecting_department = State()
    writing_confession = State()
    confirming_confession = State()

# ---------- UX microcopy ----------
CAMPUS_PROMPTS = [
    "🏫 Which campus does your crush call home?",
    "📍 Pin their campus for us!",
    "👀 Where do they usually hang out?"
]
DEPT_PROMPTS = [
    "📚 What’s their department?",
    "🏷️ Pick their department from the list:",
    "🧭 Department time — where do they study?"
]
WRITE_PROMPTS = [
    "🔥 Final step — drop your confession!",
    "💭 Be real, be bold — write your confession:",
    "💌 Tell us what’s on your heart:"
]
TOO_SHORT_RESPONSES = [
    "😅 That’s too short — at least 10 characters.",
    "📢 Give us more to work with — 10+ characters please.",
    "📝 Tiny whispers don’t post well — add a bit more."
]
BREAKERS = [
    "─────────────── ✨ ───────────────",
    "💘 Confession mode engaged…",
    "⚡ Speak your truth, softly or loudly.",
    "🌟 Let it out — someone might be smiling.",
]

# ---------- Constants for pagination ----------
ITEMS_PER_PAGE = 4   # total items per page
COLUMNS = 2          # buttons per row

# ---------- Reply keyboard for main menu (adjust to your app) ----------
def main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💘 Mutual Matches"), KeyboardButton(text="👀 Who Liked Me")],
            [KeyboardButton(text="❤️ My Likes"), KeyboardButton(text="💌 Crush Confession")],
        ],
        resize_keyboard=True
    )

# ---------- Paginated inline keyboards ----------
def paginated_keyboard(
    items,
    prefix: str,
    page: int,
    columns: int = COLUMNS,
    items_per_page: int = ITEMS_PER_PAGE
) -> InlineKeyboardMarkup:
    """
    Build a paginated keyboard:
    - Works with both lists and dictionaries.
    - prefix: 'conf_campus' or 'conf_dept'
    - page: current page index (0-based)
    """

    # ✅ Handle both dicts and lists
    if isinstance(items, dict):
        items = list(items.keys())  # use dict keys (names) for buttons
    elif not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or dictionary")

    total = len(items)
    total_pages = max(1, (total + items_per_page - 1) // items_per_page)
    page = max(0, min(page, total_pages - 1))

    start = page * items_per_page
    end = min(start + items_per_page, total)
    sliced = items[start:end]

    # 🔘 Build buttons
    rows = []
    row = []
    for item in sliced:
        row.append(
            InlineKeyboardButton(
                text=str(item),
                callback_data=f"{prefix}_select_{item}"
            )
        )
        if len(row) == columns:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # 🔄 Pagination controls
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Prev", callback_data=f"{prefix}_page_{page-1}"
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{page+1}/{total_pages}", callback_data=f"{prefix}_noop"
        )
    )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Next ➡️", callback_data=f"{prefix}_page_{page+1}"
            )
        )
    if nav_row:
        rows.append(nav_row)

    # 🔙 Contextual Back / Cancel buttons
    if prefix == "conf_campus":
        rows.append(
            [InlineKeyboardButton(text="❌ Cancel", callback_data="conf_cancel")]
        )
    else:
        rows.append([
            InlineKeyboardButton(text="🔙 Back", callback_data="conf_back_to_campus"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="conf_cancel"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)



def preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Submit", callback_data="conf_submit")],
        [InlineKeyboardButton(text="✏️ Edit", callback_data="conf_edit")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="conf_cancel")]
    ])
    
# ---------- Entry ----------
@router.message(F.text == "💌 Crush Confession")
async def start_confession_msg(message: Message, state: FSMContext):
    await state.clear()
    intro = (
        "💌 Crush Confession Time!\n\n"
        "Confess anonymously and we’ll post it to the channel 📢\n"
        "If your crush sees it and likes you back… it’s a match! 🔥\n\n"
        f"You’ll earn {COIN_REWARDS.get('confession', 5)} coins for posting ✨\n\n"
        f"{random.choice(BREAKERS)}\n\n"
        f"{random.choice(CAMPUS_PROMPTS)}"
    )
    kb = paginated_keyboard(AAU_CAMPUSES, prefix="conf_campus", page=0)
    
    # 👇 show only back-to-main-menu reply keyboard
    await message.answer(intro, reply_markup=back_to_main_menu_kb())
    await message.answer("Pick a campus:", reply_markup=kb)
    await state.set_state(ConfessionState.selecting_campus)
    await state.update_data(campus_page=0)


def back_to_main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Back to Main Menu")]],
        resize_keyboard=True
    )

# Handle the back-to-main-menu reply button
@router.message(F.text == "🔙 Back to Main Menu", StateFilter(ConfessionState))
async def confession_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Back to main menu!", reply_markup=main_menu_reply_keyboard())


# ---------- Campus pagination + selection ----------
@router.callback_query(F.data.startswith("conf_campus_page_"), StateFilter(ConfessionState.selecting_campus))
async def campus_page_nav(callback: CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split("conf_campus_page_")[1])
    except Exception:
        await callback.answer("Invalid page 💀")
        return
    await state.update_data(campus_page=page)
    kb = paginated_keyboard(AAU_CAMPUSES, prefix="conf_campus", page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("conf_campus_select_"), StateFilter(ConfessionState.selecting_campus))
async def campus_select(callback: CallbackQuery, state: FSMContext):
    campus = callback.data.split("conf_campus_select_")[1]
    await state.update_data(target_campus=campus)

    text = (
        f"✅ Campus: {campus}\n"
        f"{random.choice(BREAKERS)}\n\n"
        f"{random.choice(DEPT_PROMPTS)}"
    )
    dept_page = 0
    kb = paginated_keyboard(AAU_DEPARTMENTS, prefix="conf_dept", page=dept_page)
    await callback.message.edit_text(text, reply_markup=kb)
    await state.set_state(ConfessionState.selecting_department)
    await state.update_data(dept_page=dept_page)
    await callback.answer()

@router.callback_query(F.data == "conf_campus_noop", StateFilter(ConfessionState.selecting_campus))
async def campus_noop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

# ---------- Department pagination + selection ----------
@router.callback_query(F.data.startswith("conf_dept_page_"), StateFilter(ConfessionState.selecting_department))
async def dept_page_nav(callback: CallbackQuery, state: FSMContext):
    try:
        page = int(callback.data.split("conf_dept_page_")[1])
    except Exception:
        await callback.answer("Invalid page 💀")
        return
    await state.update_data(dept_page=page)
    kb = paginated_keyboard(AAU_DEPARTMENTS, prefix="conf_dept", page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("conf_dept_select_"), StateFilter(ConfessionState.selecting_department))
async def dept_select(callback: CallbackQuery, state: FSMContext):
    dept = callback.data.split("conf_dept_select_")[1]
    await state.update_data(target_department=dept)

    data = await state.get_data()
    text = (
        f"✅ Campus: {data['target_campus']}\n"
        f"✅ Department: {dept}\n\n"
        f"{random.choice(BREAKERS)}\n\n"
        f"{random.choice(WRITE_PROMPTS)}\n"
        f"(Max {MAX_CONFESSION_LENGTH} characters)"
    )
    await callback.message.edit_text(text)
    await state.set_state(ConfessionState.writing_confession)
    await callback.answer()

@router.callback_query(F.data == "conf_dept_noop", StateFilter(ConfessionState.selecting_department))
async def dept_noop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

# ---------- Back / Cancel ----------
@router.callback_query(F.data == "conf_back_to_campus", StateFilter(ConfessionState.selecting_department))
async def back_to_campus(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get("campus_page", 0)
    text = (
        "🔙 Back to campus selection.\n\n"
        f"(Currently: {data.get('target_campus', 'none')})\n\n"
        f"{random.choice(CAMPUS_PROMPTS)}"
    )
    kb = paginated_keyboard(AAU_CAMPUSES, prefix="conf_campus", page=page)
    await callback.message.edit_text(text, reply_markup=kb)
    await state.set_state(ConfessionState.selecting_campus)
    await callback.answer()

@router.callback_query(F.data == "conf_cancel", StateFilter(ConfessionState))
async def confession_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Confession cancelled.", reply_markup=main_menu_reply_keyboard())
    await callback.answer()

# ---------- Confession input + preview ----------
@router.message(StateFilter(ConfessionState.writing_confession))
async def process_confession(message: Message, state: FSMContext):
    confession_text = (message.text or "").strip()

    if len(confession_text) < 10:
        await message.answer(random.choice(TOO_SHORT_RESPONSES))
        return

    if len(confession_text) > MAX_CONFESSION_LENGTH:
        await message.answer(f"📝 Too long! Keep it under {MAX_CONFESSION_LENGTH} characters.")
        return

    await state.update_data(confession_text=confession_text)

    preview = (
        f"📝 Your confession draft:\n\n"
        f"{confession_text}\n\n"
        "Submit or edit?"
    )
    await message.answer(preview, reply_markup=preview_keyboard())
    await state.set_state(ConfessionState.confirming_confession)

@router.callback_query(F.data == "conf_edit", StateFilter(ConfessionState.confirming_confession))
async def confession_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = (
        f"✏️ Editing your confession.\n\n"
        f"✅ Campus: {data.get('target_campus')}\n"
        f"✅ Department: {data.get('target_department')}\n\n"
        f"(Max {MAX_CONFESSION_LENGTH} characters)\n\n"
        "Send your updated confession as a message:"
    )
    await callback.message.edit_text(text)
    await state.set_state(ConfessionState.writing_confession)
    await callback.answer()

# ---------- Submission ----------
@router.callback_query(F.data == "conf_submit", StateFilter(ConfessionState.confirming_confession))
async def confession_submit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    confession_text = data.get("confession_text", "")
    campus = data.get("target_campus")
    department = data.get("target_department")

    if not confession_text or not campus or not department:
        await callback.answer("Missing details — please restart confession.", show_alert=True)
        await state.clear()
        return

    confession_data = {
        'campus': campus,
        'department': department,
        'text': confession_text,
        'status': 'pending'
    }

    try:
        confession_id = await db.create_confession(callback.from_user.id, confession_data)
    except Exception as e:
        logger.error(f"Error creating confession: {e}")
        confession_id = None

    if confession_id:
        reward = COIN_REWARDS.get('confession', 5)
        try:
            await db.add_coins(callback.from_user.id, reward)
        except Exception as e:
            logger.warning(f"Could not add coins: {e}")

        success_text = (
            "✅ Confession submitted!\n\n"
            "Admins will review and post it to the channel soon. 📢\n"
            f"🪙 +{reward} coins added.\n\n"
            "Want to do more?"
        )
        await callback.message.edit_text(success_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton(text="💌 New Confession", callback_data="conf_restart")]
        ]))
    else:
        fail_text = (
            "⚠️ Something went wrong.\n"
            "Please try again later."
        )
        await callback.message.edit_text(fail_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton(text="💌 Retry Confession", callback_data="conf_restart")]
        ]))

    await state.clear()
    await callback.answer()

# ---------- Restart shortcut ----------
@router.callback_query(F.data == "conf_restart")
async def confession_restart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await start_confession_msg(callback.message, state)
    await callback.answer()

# ---------- Guards against random text in selection steps ----------
@router.message(StateFilter(ConfessionState.selecting_campus))
async def guard_during_campus(message: Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("campus_page", 0)
    await message.answer("😅 Pick a campus from the buttons below.", reply_markup=paginated_keyboard(AAU_CAMPUSES, "conf_campus", page))

@router.message(StateFilter(ConfessionState.selecting_department))
async def guard_during_dept(message: Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("dept_page", 0)
    await message.answer("😅 Pick a department from the buttons below.", reply_markup=paginated_keyboard(AAU_DEPARTMENTS, "conf_dept", page))
