import logging
import json
import random
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from bot_config import LIKE_CONFIRMATIONS, PASS_CONFIRMATIONS
from database import db
from utils import format_profile_text, calculate_vibe_compatibility, vibe_label
from handlers_main import show_main_menu # Import the main menu function

logger = logging.getLogger(__name__)
router = Router()

class MatchingState(StatesGroup):
    browsing = State()
    filter_selection = State()
    # Adding a state for waiting for filter input if needed in the future

# --- Navigation Helpers ---

def get_matching_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for the initial matching menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        # Use two columns for the main actions
        [
            InlineKeyboardButton(text="🔥 Start Swiping", callback_data="start_swiping"),
            InlineKeyboardButton(text="🎯 Filter Matches", callback_data="filter_matches")
        ],
        [
            InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu_from_matching")
        ]
    ])

def get_out_of_candidates_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for when a user runs out of profiles."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Change Filters", callback_data="filter_matches")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu_from_matching")]
    ])

def get_filter_summary_text(filters: dict) -> str:
    """Formats the current filters into a user-friendly string."""
    if not filters:
        return "✨ Current Filter: None (You see everyone!)"

    filter_parts = []
    
    if 'campus' in filters:
        filter_parts.append(f"🏫 Campus: `{filters['campus']}`")
    if 'dept' in filters:
        filter_parts.append(f"📚 Department: `{filters['dept']}`")
    if 'year' in filters:
        filter_parts.append(f"🎓 Year: `{filters['year']}`")
    
    # If the vibe_min filter is ever implemented, you can add it here too.
    
    return "✨ Current Filters:\n" + "\n".join(filter_parts)


# --- Handlers ---
import logging
import json
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# IMPORTANT: Import ReplyKeyboard and KeyboardButton
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

from database import db
# Assuming these utilities are imported and available
from utils import format_profile_text, calculate_vibe_compatibility
from handlers_main import show_main_menu # Import the main menu function

logger = logging.getLogger(__name__)
router = Router()

class MatchingState(StatesGroup):
    browsing = State()
    filter_selection = State()
    # Note: State for filter input may be needed for full filter implementation

# --- Keyboard Helpers ---

def get_swiping_reply_keyboard() -> ReplyKeyboardMarkup:
    """Returns the custom Reply Keyboard for swiping and navigation."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❤️ Like"), KeyboardButton(text="👋 Skip")],
          [KeyboardButton(text="🎯 Change Filters"), KeyboardButton(text="🔙 Main Menu")]

        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="✨ Swipe or refine your vibe..."
    )

def get_filter_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the Inline Keyboard for filter selection (replaces the old one)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Filter by Campus", callback_data="filter_campus")],
        [InlineKeyboardButton(text="🎓 Filter by Year", callback_data="filter_year")],
        [InlineKeyboardButton(text="✨ Clear All Filters", callback_data="clear_filters")],
        [InlineKeyboardButton(text="🔥 Back to Swiping", callback_data="start_swiping_from_filter")] # New callback
    ])


def get_out_of_matches_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard shown when user runs out of candidates."""
    return ReplyKeyboardMarkup(
       keyboard=[
    [KeyboardButton(text="🎯 Change Filters"), KeyboardButton(text="👥 Invite Friends")],
    [KeyboardButton(text="🔙 Main Menu")]
       ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="✨ No more profiles — choose your next step..."
    )
# --- Core Swiping Logic ---

@router.message(F.text == "❤️ Find Matches") 
async def start_matching_flow(message: Message, state: FSMContext):
    """Entry point for matching flow."""
    await state.clear()
    await message.answer(
        "Loading profiles... get ready to swipe! 🔥", 
        reply_markup=get_swiping_reply_keyboard()
    )
    await show_candidate(message, state, message.from_user.id, initial_call=True)



async def show_candidate(message: Message, state: FSMContext, viewer_id: int, initial_call: bool = False):
    """
    Fetches the next candidate, updates the index (with wrap-around),
    and sends the new profile view with cinematic flair.
    """
    await state.set_state(MatchingState.browsing)

    data = await state.get_data()
    candidates = data.get('candidates')
    filters = data.get('filters', {})
    current_index = data.get('current_index', 0)

    # 1. Fetch candidates if needed
    if candidates is None or initial_call:
        candidates = await db.get_matches_for_user(viewer_id, filters)
        if not candidates:
            await message.answer(
                "😅 Looks like you’ve seen everyone for now!\n\n"
                "✨ You can adjust your filters, invite more friends to grow the pool, "
                "or head back to the main menu.",
                reply_markup=get_out_of_matches_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await state.set_state(None)
            return

            
        current_index = 0
        await state.update_data(candidates=candidates, current_index=0)

    if current_index >= len(candidates):
        # No more candidates left
        await message.answer(
            "😅 Looks like you’ve seen everyone for now!\n\n"
            "✨ You can adjust your filters, invite more friends to grow the pool, "
            "or head back to the main menu.",
            reply_markup=get_out_of_matches_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(None)
        return


    candidate = candidates[current_index]

    # --- Vibe score ---
    viewer = await db.get_user(viewer_id)
    viewer_vibe = json.loads(viewer.get('vibe_score', '{}') or '{}')
    candidate_vibe = json.loads(candidate.get('vibe_score', '{}') or '{}')
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

    # --- Interests ---
    viewer_interests = await db.get_user_interests(viewer_id)
    candidate_interests = await db.get_user_interests(candidate["id"])

    # --- Reveal state (check if match exists and revealed) ---
    match_row = await db.get_match_between(viewer_id, candidate["id"])
    is_revealed = True

    profile_text = await format_profile_text(
        candidate,
        vibe_score=vibe_score,
        show_full=False,
        viewer_interests=viewer_interests,
        candidate_interests=candidate_interests,
        revealed=is_revealed  # 👈 this one flag handles both cases
    )

    # --- Breaker line ---
    breakers = [
        "─────────────── ✨ ───────────────",
        "💘 Another crush appears...",
        "🎭 A new face steps into the spotlight",
        "⚡ Fresh profile unlocked!",
        "🌟 Who’s this? Let’s find out..."
    ]
    try:
        await message.answer(random.choice(breakers))
    except Exception:
        pass

    # --- Progress indicator ---
    total = len(candidates)
    profile_text += f"\n\n🎬 Scene {current_index+1} - keep swiping ➡️"

    # --- Send profile ---
    try:
        if candidate.get("photo_file_id") and is_revealed:
            await message.answer_photo(
                photo=candidate["photo_file_id"],
                caption=profile_text,
                reply_markup=get_swiping_reply_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                profile_text,
                reply_markup=get_swiping_reply_keyboard(),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error showing candidate: {e}")
        await message.answer(profile_text, reply_markup=get_swiping_reply_keyboard(), parse_mode=ParseMode.HTML)
        
    
    await state.update_data(current_index=current_index)



@router.message(F.text == "❤️ Like", MatchingState.browsing)
async def handle_like_message(message: Message, state: FSMContext):
    liker_id = message.from_user.id
    data = await state.get_data()
    candidates = data.get('candidates', [])
    current_index = data.get('current_index', 0)

    if not candidates or current_index >= len(candidates):
        await message.answer("🔄 Refreshing your candidate pool...")
        return await show_candidate(message, state, liker_id, initial_call=True)

    liked_id = candidates[current_index]['id']
    result = await db.add_like(liker_id, liked_id)

    # 🎬 Cinematic confirmation
    await message.answer(
        random.choice(LIKE_CONFIRMATIONS),
        reply_markup=get_swiping_reply_keyboard(),
        parse_mode=ParseMode.HTML
    )
    from handlers_likes import celebrate_match, notify_like
    print(f"add_like result: {result}")

    if result["status"] == "match":
        await celebrate_match(message.bot, liker_id, liked_id, result["match_id"], context="swipe", liked_before=True)
    elif result["status"] == "liked":
        await notify_like(message.bot, liker_id, liked_id)
    else:
        await message.answer("😅 Couldn’t save your like. Try again later.")

    await state.update_data(current_index=current_index + 1)

    # Smooth transition
    await message.answer("➡️ Finding your next vibe...")
    await show_candidate(message, state, liker_id)
    
    
@router.message(F.text == "👋 Skip", MatchingState.browsing)
async def handle_pass_message(message: Message, state: FSMContext):
    """Handles the '💔 Pass' button press with cinematic feedback."""
    liker_id = message.from_user.id

    # 🎬 Cinematic confirmation
    await message.answer(random.choice(PASS_CONFIRMATIONS), reply_markup=get_swiping_reply_keyboard())

    data = await state.get_data()
    candidates = data.get('candidates', [])
    current_index = data.get('current_index', 0)

    if candidates and current_index < len(candidates):
        passed_id = candidates[current_index]['id']
        # Record the pass in DB
        await db.add_pass(liker_id, passed_id)

    await state.update_data(current_index=current_index + 1)

    # Smooth transition to next candidate
    await message.answer("➡️ Finding your next vibe...")
    await show_candidate(message, state, liker_id)
# --- Filter Handlers (Updated for Reply Keyboard flow) ---

@router.message(F.text == "🎯 Change Filters")
async def start_filter_selection(message: Message, state: FSMContext):
    """Starts the filter selection process."""
    data = await state.get_data()
    filters = data.get('filters', {})
    
    # We must hide the Reply Keyboard and show the Inline Filter Keyboard
    await message.answer(
        "🎯 **Current Filters**\n\n"
        f"{get_filter_summary_text(filters)}\n\n"
        "Select a filter to change:",
        reply_markup=get_filter_menu_keyboard() # Use Inline Keyboard for filter selection
    )
    await state.set_state(MatchingState.filter_selection)
    
@router.callback_query(F.data == "start_swiping_from_filter", MatchingState.filter_selection)
async def back_to_swiping_callback(callback: CallbackQuery, state: FSMContext):
    """Returns to swiping after filter selection/clear."""
    await callback.message.edit_text("Resuming swiping with new filters! 🔥")
    await state.set_state(MatchingState.browsing) 
    
    # Use initial_call=True to re-fetch candidates based on potentially new filters
    await show_candidate(callback.message, state, callback.from_user.id, initial_call=True)
    await callback.answer()

# --- Navigation Back to Main Menu ---

@router.message(F.text == "🔙 Main Menu")
async def main_menu_from_matching_message(message: Message, state: FSMContext):
    """Clears state and returns to the main menu (Reply Keyboard handler)."""
    await state.clear() 
    await show_main_menu(message) 


@router.callback_query(F.data == "filter_matches")
async def filter_matches(callback: CallbackQuery, state: FSMContext):
    # Retrieve current filters to display them
    data = await state.get_data()
    filters = data.get('filters', {})
    filter_summary = get_filter_summary_text(filters)

    try:
        from bot_config import AAU_CAMPUSES, AAU_DEPARTMENTS, YEARS # Import configuration
    except ImportError:
        # Fallback if running in a context where bot_config isn't available
        AAU_CAMPUSES = ["Campus A", "Campus B"]
        AAU_DEPARTMENTS = ["CS", "EE"]
        YEARS = ["1st", "2nd"]
        
    # Enhanced keyboard for filter menu (grouped and better icons)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Group filters into two columns
        [
            InlineKeyboardButton(text="🏫 Campus", callback_data="filter_campus"),
            InlineKeyboardButton(text="📚 Department", callback_data="filter_dept")
        ],
        [
            InlineKeyboardButton(text="🎓 Year", callback_data="filter_year"),
            InlineKeyboardButton(text="🗑️ Clear All Filters", callback_data="clear_filters")
        ],
        [InlineKeyboardButton(text="🔙 Back to Swiping", callback_data="start_swiping_from_filter")]
    ])

    await callback.message.edit_text(
        f"🎯 Set your filters:\n\n"
        f"{filter_summary}\n\n"
        "Choosing filters helps narrow down your search for the perfect match! 👀",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "filter_campus")
async def filter_by_campus(callback: CallbackQuery, state: FSMContext):
    from bot_config import AAU_CAMPUSES # Import configuration
    data = await state.get_data()
    current_filter = data.get('filters', {}).get('campus', 'None')

    keyboard = [
        [InlineKeyboardButton(text=f"{campus} {'✅' if campus == current_filter else ''}", callback_data=f"setfilter_campus_{campus}")]
        for campus in AAU_CAMPUSES
    ]
    # Use "⬅️ Back to Filters" for consistency
    keyboard.append([InlineKeyboardButton(text="⬅️ Back to Filters", callback_data="filter_matches")])

    await callback.message.edit_text(
        f"Select Campus 🏫 (Current: `{current_filter}`)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "filter_dept")
async def filter_by_department(callback: CallbackQuery, state: FSMContext):
    from bot_config import AAU_DEPARTMENTS # Import configuration
    data = await state.get_data()
    current_filter = data.get('filters', {}).get('dept', 'None')

    # Present departments in multiple columns if there are many for better UX
    inline_keyboard = []
    row = []
    for i, dept in enumerate(AAU_DEPARTMENTS):
        text = f"{dept} {'✅' if dept == current_filter else ''}"
        row.append(InlineKeyboardButton(text=text, callback_data=f"setfilter_dept_{dept}"))
        if (i + 1) % 2 == 0 or i == len(AAU_DEPARTMENTS) - 1: # 2 columns
            inline_keyboard.append(row)
            row = []

    # If the last row isn't complete, append it (shouldn't happen with the logic above, but safe to include)
    if row:
        inline_keyboard.append(row)

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Back to Filters", callback_data="filter_matches")])

    await callback.message.edit_text(
        f"Select Department 📚 (Current: `{current_filter}`)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "filter_year")
async def filter_by_year(callback: CallbackQuery, state: FSMContext):
    from bot_config import YEARS # Import configuration
    data = await state.get_data()
    current_filter = data.get('filters', {}).get('year', 'None')

    keyboard = [
        [InlineKeyboardButton(text=f"{year} {'✅' if year == current_filter else ''}", callback_data=f"setfilter_year_{year}")]
        for year in YEARS
    ]
    keyboard.append([InlineKeyboardButton(text="⬅️ Back to Filters", callback_data="filter_matches")])

    await callback.message.edit_text(
        f"Select Academic Year 🎓 (Current: `{current_filter}`)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("setfilter_"))
async def set_filter(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("setfilter_")[1].split("_", 1)
    filter_type = parts[0] 
    filter_value = parts[1]

    data = await state.get_data()
    filters = data.get('filters', {})
    filters[filter_type] = filter_value

    await state.update_data(filters=filters)

    await callback.answer(f"Filter set: {filter_value} ✅")
    # Return to the filter selection menu
    await filter_matches(callback, state)

@router.callback_query(F.data == "clear_filters")
async def clear_filters(callback: CallbackQuery, state: FSMContext):
    await state.update_data(filters={})
    await callback.answer("All filters cleared! ✨")
    await filter_matches(callback, state)

# --- Navigation Back to Main Menu ---

@router.callback_query(F.data == "main_menu_from_matching")
async def main_menu_from_matching_callback(callback: CallbackQuery, state: FSMContext):
    """
    Clears the matching state and calls the main menu function from handlers_main.
    This replaces the 'main_menu' inline handler within the matching flow.
    """
    await state.clear()
    
    # Try to delete the current message, which might be a photo caption or a text message
    try:
        # Use callback.message.edit_text with an empty reply_markup to clear buttons 
        # before deleting, which is sometimes safer than direct deletion.
        await callback.message.edit_text("Returning to Main Menu...")
        await callback.message.delete()
    except Exception:
        pass # Ignore deletion errors
        
    # Call the existing show_main_menu function imported from handlers_main
    await show_main_menu(callback.message)
    await callback.answer("Returning to Main Menu 🔙")
