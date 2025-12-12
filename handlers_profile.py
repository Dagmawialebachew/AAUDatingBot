from datetime import date
import random
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
# ... other imports
from aiogram.enums import ParseMode
import logging
import json
from typing import Callable, Dict, List, Tuple, Optional, Union
# Assuming these imports are available in the bot's environment
from database import db
from bot_config import AAU_CAMPUSES, AAU_DEPARTMENTS, ADMIN_GROUP_ID, INTEREST_CATEGORIES, YEARS, GENDERS, VIBE_QUESTIONS, MAX_BIO_LENGTH
from utils import calculate_vibe_compatibility, format_profile_text, validate_bio, download_and_resize_image

logger = logging.getLogger(__name__)
router = Router()


# async def show_main_menu(message: Message):
#     user = await db.get_user(message.from_user.id)

#     if not user:
#         await message.answer("Use /start to create your profile first! 🚀")
#         return

#     await db.record_daily_login(message.from_user.id)

#     text = (
#         f"Yo {user['name']}! 👋\n\n"
#         f"🪙 Coins: {user['coins']}\n\n"
#         f"What's the move? 😏"
#     )

#     await message.answer(text, reply_markup=get_main_menu_keyboard())




# def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="❤️ Find Matches"), KeyboardButton(text="💖 My Crushes")],
#             [KeyboardButton(text="✏️ Edit Profile"), KeyboardButton(text="💌 Crush Confession")],
#             [KeyboardButton(text="🏆 Leaderboard"), KeyboardButton(text="📢 Campus Feed")],
#             [KeyboardButton(text="🪙 Coins & Shop"), KeyboardButton(text="👥 Invite Friends")],
#             [KeyboardButton(text="🎮 Mini Games")]
#         ],
#         resize_keyboard=True
#     )


# --- FSM States for Initial Setup ---
class ProfileSetup(StatesGroup):
    gender = State()
    seeking_gender = State()
    campus = State()
    department = State()
    department_custom = State()
    year = State()
    name = State()
    bio = State()
    photo = State()
    vibe_quiz = State()
    interests = State()

# --- FSM States for Quick Profile Edits ---
class EditProfile(StatesGroup):
    editing_name = State()
    editing_bio = State()
    editing_photo = State()
    editing_gender = State()
    editing_seeking = State()
    vibe_quiz_restart_q = State()
    editing_academic = State()
    editing_campus = State()
    editing_department = State()
    editing_year = State()
    editing_custom_department = State()
    editing_interests = State()

# --- Keyboard Helpers (Unchanged, as they are clean) ---


def get_gender_keyboard():
    # Create two on the top row, one below
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👦♂️ Male", callback_data="gender_male"),
            InlineKeyboardButton(text="👩♀️ Female", callback_data="gender_female"),
        ],
     
    ])
    return keyboard


def get_seeking_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👦♂️ Males", callback_data="seeking_male"),
            InlineKeyboardButton(text="👩♀️ Females", callback_data="seeking_female"),
        ],
        [
            InlineKeyboardButton(text="⚧ Anyone", callback_data="seeking_any"),
        ],
    ])
    return keyboard



def get_campus_keyboard():
    rows = []
    campus_items = list(AAU_CAMPUSES.items())

    # 3 buttons per row
    for i in range(0, len(campus_items), 3):
        row = []
        for display, value in campus_items[i:i+3]:
            row.append(InlineKeyboardButton(text=display, callback_data=f"campus_{value}"))
        rows.append(row)

    # Optional Back button (to previous step, e.g. seeking gender)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_department_keyboard():
    rows = []
    dept_items = list(AAU_DEPARTMENTS.items())

    # 3 buttons per row
    for i in range(0, len(dept_items), 3):
        row = []
        for display, value in dept_items[i:i+3]:
            row.append(InlineKeyboardButton(text=display, callback_data=f"dept_{value}"))
        rows.append(row)

    # Optional Back button (to campus step)

    return InlineKeyboardMarkup(inline_keyboard=rows)



@router.message(F.text == "✍️ Edit Name/Bio")
async def open_edit_name_bio_tab(message: Message, state: FSMContext):
    """Replace keyboard with Edit Name / Change Bio options."""
    await message.answer(
        "✍️ What would you like to edit?",
        reply_markup=get_edit_name_bio_keyboard()
    )

# Listener for back to main edit menu from the second-level menu
@router.message(F.text == "⬅️ Back")
async def back_to_main_edit_tab(message: Message, state: FSMContext):
    await show_edit_profile_menu_from_main(message, state, edit=False)

    
def get_year_keyboard():
    rows = []
    year_items = list(YEARS.items())

    # 2 buttons per row
    for i in range(0, len(year_items), 2):
        row = []
        for display, value in year_items[i:i+2]:
            row.append(InlineKeyboardButton(text=display, callback_data=f"year_{value}"))
        rows.append(row)

    # Optional Back button

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_vibe_keyboard(question_idx: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(opt), callback_data=f"vibe_{question_idx}_{i}")
                for i, opt in enumerate(VIBE_QUESTIONS[question_idx]['options'])
            ]
        ]
    )
    return keyboard
# --- Main Edit Profile Keyboard ---
def get_edit_profile_main_keyboard() -> ReplyKeyboardMarkup:
    """
    First-level menu: core edits, buttons side by side.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✍️ Edit Name/Bio"),
                KeyboardButton(text="📸 Change Photo")
            ],
            [
                KeyboardButton(text="🔄 Change Identity"),
                KeyboardButton(text="➡️ More")
            ],
            [
                KeyboardButton(text="🔙 Back to Main Menu")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )



# Second-level menu for Edit Name / Change Bio
def get_edit_name_bio_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Edit Name"), KeyboardButton(text="✍️ Change Bio")],
            [KeyboardButton(text="⬅️ Back")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )
def get_edit_profile_more_keyboard() -> ReplyKeyboardMarkup:
    """
    Second-level menu: extras, side by side
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💫 Retake Vibe Quiz"),
                KeyboardButton(text="🎓 Change Academic Info")
            ],
            [
                KeyboardButton(text="🎯 Edit Interests")
            ],
            [
                KeyboardButton(text="⬅️ Back")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True
    )



def get_edit_profile_more_inline_keyboard() -> InlineKeyboardMarkup:
    """Second-level edit menu for InlineKeyboardMarkup."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💫 Retake Vibe Quiz", callback_data="edit_vibe"),
            InlineKeyboardButton(text="🎓 Change Academic Info", callback_data="edit_academic")
        ],
        [
            InlineKeyboardButton(text="🎯 Edit Interests", callback_data="edit_interests"),
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_main_edit")
        ]
    ])

@router.message(F.text == "➡️ More")
async def open_more_edit_tab(message: Message, state: FSMContext):
    """Show the second-level edit menu as a new message."""
    await message.answer(
        "🎛️ Additional Profile Options",
        reply_markup=get_edit_profile_more_keyboard()
    )

# Handle the "Back" button
@router.callback_query(F.data == "back_main_edit")
async def back_to_main_edit_tab(callback: CallbackQuery, state: FSMContext):
    """Return to the main edit menu by editing the bot's message."""
    try:
        # Try to edit the message
        await show_edit_profile_menu_from_main(callback.message, state, edit=True)
    except Exception as e:
        # Fallback: send a new message if edit fails
        await show_edit_profile_menu_from_main(callback.message, state, edit=False)
        logger.warning(f"Failed to edit message, sent new one instead: {e}")

    await callback.answer()


def get_academic_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏫 Campus", callback_data="academic_campus")],
            [InlineKeyboardButton(text="📚 Department", callback_data="academic_department")],
            [InlineKeyboardButton(text="🎓 Year", callback_data="academic_year")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="academic_cancel")]
        ]
    )
# --- New Reply Keyboard Entry Point ---


async def show_edit_profile_menu_from_main(message: Message, state: FSMContext, edit: bool = False):
    """
    Show the user's profile in edit mode with stats, coins, status,
    interests (priority to shared), profile completeness and rating.
    """
    await state.clear()
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user:
        await message.answer("Error: Profile data not found. Use /start to create one.")
        return

    # Get user stats
    stats = await db.get_user_stats(user_id)

    # --- Status ---

    # --- Interests ---
    candidate_interests = await db.get_user_interests(user_id)

    # Fetch shared interests (intersection with all other users)
    shared_interests = []
    other_user_ids = await db.get_other_user_ids(user_id)
    for other_id in other_user_ids:
        other_interests = await db.get_user_interests(other_id)
        shared_interests += list(set(candidate_interests) & set(other_interests))
    shared_interests = list(dict.fromkeys(shared_interests))  # Remove duplicates, keep order

    # Prioritize shared interests, then add others
    final_interests = shared_interests[:3]
    if len(final_interests) < 3:
        for i in candidate_interests:
            if i not in final_interests:
                final_interests.append(i)
            if len(final_interests) >= 3:
                break

    interests_text = " | ".join(final_interests) if final_interests else "No interests yet."


    # --- Profile Completeness ---
    completeness_score = 0
    fields = ["name", "bio", "campus", "department", "year", "photo_file_id", "status", "coins"]
    for f in fields:
        if user.get(f):
            completeness_score += 1
    completeness_percent = int(completeness_score / len(fields) * 100)

    # Assign a rating
    if completeness_percent >= 90:
        completeness_label = "🌟 Excellent"
    elif completeness_percent >= 70:
        completeness_label = "⚡ Good"
    elif completeness_percent >= 50:
        completeness_label = "✨ Fair"
    else:
        completeness_label = "🔹 Needs Work"

        # --- Build profile text ---
    profile_text = (
        f"👤 **{user['name']}**\n"
        f"📍 {user['campus']} | {user['department']}\n"
        f"🎓 {user['year']}\n\n"
        f"💭 {user['bio']}\n\n"
        f"✨ Interests ({len(final_interests)}/3):\n{interests_text}\n\n"
         f"📊 **Your Stats:**\n"
        f"❤️ {stats['likes_received']} people liked you\n"
        f"💫 {stats['likes_sent']} likes sent\n"
        f"🔥 {stats['matches']} matches\n\n"
        f"🪙 **{user['coins']} Coins**\n\n"
        f"⚡ Profile Complete: {completeness_percent}% — {completeness_label}\n\n"
    )


    # --- Send message ---
    if user.get("photo_file_id"):
        await message.answer_photo(
            photo=user['photo_file_id'],
            caption=profile_text,
            reply_markup=get_edit_profile_main_keyboard(),

            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            profile_text,
            reply_markup=get_edit_profile_main_keyboard(),

            parse_mode=ParseMode.MARKDOWN
        )

@router.message(F.text == "🔙 Back to Main Menu")
async def back_to_main_menu_from_edit_reply(message: Message, state: FSMContext):
    """Clears state and returns to the main menu (Reply Keyboard handler)."""
    await state.clear()
    from handlers_main import show_main_menu
 
    await show_main_menu(message) 

@router.message(F.text == "✍️ Change Bio")
async def start_edit_bio_reply(message: Message, state: FSMContext):
    """Triggers the bio edit FSM state, with an inline Cancel button."""
    user = await db.get_user(message.from_user.id)
    current_bio = user.get('bio', 'No bio set.')

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_bio")]
    ])

    await message.answer(
        (
            f"📝 **Current Bio:**\n`{current_bio}`\n\n"
            f"Type your **NEW** bio below! 👇\n"
            f"(Max {MAX_BIO_LENGTH} characters)"
        ),
        reply_markup=cancel_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    await state.set_state(EditProfile.editing_bio)


@router.message(F.text == "📝 Edit Name")
async def start_edit_name_reply(message: Message, state: FSMContext):
    """Triggers the name edit FSM state, with an inline Cancel button."""
    user = await db.get_user(message.from_user.id)
    current_name = user.get('name', 'No name set.')

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_name")]
    ])

    await message.answer(
        (
            f"📝 **Current Name:**\n`{current_name}`\n\n"
            f"Type your **NEW** name below! 👇\n"
            "(2-30 characters)"
        ),
        reply_markup=cancel_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    await state.set_state(EditProfile.editing_name)

@router.callback_query(F.data == "cancel_edit_name")
async def cancel_edit_name(callback: CallbackQuery, state: FSMContext):
    """Cancels name editing and clears FSM state."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Name update canceled.",
      
    )
    await callback.answer("Canceled.")

# --- Complete editing name ---
@router.message(EditProfile.editing_name)
async def complete_edit_name(message: Message, state: FSMContext):
    """Receives and saves the new name."""
    name = message.text.strip()

    if len(name) < 2 or len(name) > 30:
        cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_name")]
        ])
        await message.answer(
            "Name should be 2-30 characters... try again 📝",
            reply_markup=cancel_markup
        )
        return

    # Save to DB
    await db.update_user(message.from_user.id, {'name': name})
    await state.clear()

    await message.answer(
        f"✅ Name updated to: {name} 👌",
        reply_markup=None
    )

    # Show updated profile
    user = await db.get_user(message.from_user.id)
    stats = await db.get_user_stats(message.from_user.id)
    await _render_profile_view(message, user, stats)

@router.message(F.text == "📸 Change Photo")
async def start_edit_photo_reply(message: Message, state: FSMContext):
    """Triggers the photo edit FSM state, with an inline Cancel button."""
    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_photo")]
    ])

    await message.answer(
        (
            "📸 Send your **NEW** profile photo below! 👇\n\n"
            "Make it a good one — first impressions matter 👀"
        ),
        reply_markup=cancel_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(EditProfile.editing_photo)

@router.callback_query(F.data == "cancel_edit_photo")
async def cancel_edit_photo(callback: CallbackQuery, state: FSMContext):
    """Handles inline Cancel button press during photo editing."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Photo update canceled.",
        
    )
    await callback.answer("Canceled.")


@router.callback_query(F.data == "cancel_edit_bio")
async def cancel_edit_bio(callback: CallbackQuery, state: FSMContext):
    """Handles inline Cancel button press during bio editing."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Bio editing canceled.",
      
    )
    await callback.answer("Canceled.")

@router.message(Command("cancel"), StateFilter(EditProfile))
async def cmd_cancel_edit(message: Message, state: FSMContext):
    """Allows users to cancel any ongoing profile edit."""
    await state.clear()
    await message.answer("❌ Edit cancelled. Returning to profile...")
    await cmd_profile(message) # Show the profile view

# --- Reusable Profile View Function ---

async def _render_profile_view(source: Union[Message, CallbackQuery], user: Dict, stats: Dict):
    """
    Centralized function to display the user's profile, handling both text and photo.
    It prefers to use the source's `message` object for action.
    """
    message = source.message if isinstance(source, CallbackQuery) else source

    profile_text = (
        f"👤 **{user['name']}**\n"
        f"📍 {user['campus']} | {user['department']}\n"
        f"🎓 {user['year']}\n\n"
        f"💭 {user['bio']}\n\n"
        f"📊 **Your Stats:**\n"
        f"❤️ {stats['likes_received']} people liked you\n"
        f"💫 {stats['likes_sent']} likes sent\n"
        f"🔥 {stats['matches']} matches\n\n"
        f"🪙 **{user['coins']} Coins**"
    )

  

    if user.get('photo_file_id'):
        # Send a new photo message (or edit if source is a photo, though sending new is safer on /profile)
        await message.answer_photo(
            photo=user['photo_file_id'],
            caption=profile_text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Send a new text message
        await message.answer(
            profile_text, 
            parse_mode=ParseMode.MARKDOWN
        )

# --- Reusable Vibe Quiz Helper ---

async def _advance_vibe_quiz_step(
    callback: CallbackQuery, 
    state: FSMContext, 
    question_idx: int, 
    answer_idx: int,
    is_edit_flow: bool
) -> Tuple[bool, int]:
    """
    Processes a vibe quiz answer, saves it, and advances the quiz state.

    :returns: Tuple (is_complete, next_idx)
    """
    data = await state.get_data()
    vibe_answers = data.get('vibe_answers', {})

    question = VIBE_QUESTIONS[question_idx]
    vibe_answers[question['trait']] = answer_idx
    await state.update_data(vibe_answers=vibe_answers)

    next_idx = question_idx + 1

    if next_idx < len(VIBE_QUESTIONS):
        next_question = VIBE_QUESTIONS[next_idx]
        caption_or_text = f"Question {next_idx + 1}/{len(VIBE_QUESTIONS)}\n\n{next_question['q']}"

        # Safely edit message depending on type
        await safe_edit(callback, caption_or_text, keyboard=get_vibe_keyboard(next_idx))

        await state.update_data(vibe_question_idx=next_idx)
        return False, next_idx
    else:
        # Quiz complete
        return True, next_idx
# --- Initial Profile Setup Handlers (Cleaned up a bit) ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if message.text and message.text.startswith('/start ref_'):
        try:
            referrer_id = int(message.text.split('ref_')[1])
            if referrer_id != user_id: # Don't let users refer themselves
                await state.update_data(referrer_id=referrer_id)
        except ValueError:
            logger.warning(f"Invalid referrer ID received: {message.text}")

    if user:
        from handlers_main import show_main_menu
        await show_main_menu(message)
    else:
        await message.answer(
    "🔥 Yooo, welcome to AAUPulse! 🔥\n\n"
    "The heartbeat of AAU — where students shoot their shot 😏\n\n"
    "Before you start swiping, let’s lock in your vibe.\n"
    "No cap, it takes just 2 minutes 💯\n\n"
    "Ready to start your journey? Let’s gooo 🚀"
)

        await message.answer(
            "First up... What's your gender? 👀",
            reply_markup=get_gender_keyboard()
        )
        await state.set_state(ProfileSetup.gender)

@router.callback_query(F.data.startswith("gender_"), StateFilter(ProfileSetup.gender))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split("gender_")[1]
    await state.update_data(gender=gender)

    # Auto-assign seeking gender instead of asking
    if gender == "male":
        await state.update_data(seeking_gender="female")
    elif gender == "female":
        await state.update_data(seeking_gender="male")
    else:
        # For "other", you can decide whether to default to "any" or skip
        await state.update_data(seeking_gender="any")

    # Jump straight to campus selection
    await callback.message.edit_text(
        f"Aight, {gender} it is! ✅\n\nWhich campus you reppin'? 🏫",
        reply_markup=get_campus_keyboard()
    )
    await state.set_state(ProfileSetup.campus)
    await callback.answer()


# ... (Other setup handlers: process_seeking, process_campus, process_department, process_custom_department, process_year, process_name, process_bio remain largely the same) ...

@router.callback_query(F.data.startswith("seeking_"), StateFilter(ProfileSetup.seeking_gender))
async def process_seeking(callback: CallbackQuery, state: FSMContext):
    seeking = callback.data.split("seeking_")[1]
    await state.update_data(seeking_gender=seeking)

    await callback.message.edit_text(
        "Bet! 💯\n\nWhich campus you reppin'? 🏫",
        reply_markup=get_campus_keyboard()
    )
    await state.set_state(ProfileSetup.campus)
    await callback.answer()

@router.callback_query(F.data.startswith("campus_"), StateFilter(ProfileSetup.campus))
async def process_campus(callback: CallbackQuery, state: FSMContext):
    campus = callback.data.split("campus_")[1]
    await state.update_data(campus=campus)

    await callback.message.edit_text(
        f"{campus} gang! 🔥\n\nWhat's your department? 📚",
        reply_markup=get_department_keyboard()
    )
    await state.set_state(ProfileSetup.department)
    await callback.answer()

@router.callback_query(F.data.startswith("dept_"), StateFilter(ProfileSetup.department))
async def process_department(callback: CallbackQuery, state: FSMContext):
    dept = callback.data.split("dept_")[1]

    if dept == "Other":
        await callback.message.edit_text(
            "No worries! Type your department name below 👇"
        )
        await state.set_state(ProfileSetup.department_custom)
    else:
        await state.update_data(department=dept)
        await callback.message.edit_text(
            f"{dept} student! Respect 🙌\n\nWhat year you in? 🎓",
            reply_markup=get_year_keyboard()
        )
        await state.set_state(ProfileSetup.year)

    await callback.answer()

@router.message(StateFilter(ProfileSetup.department_custom))
async def process_custom_department(message: Message, state: FSMContext):
    dept = message.text.strip()

    if len(dept) < 2:
        await message.answer("Bruh... that's not a department 💀 Try again:")
        return

    await state.update_data(department=dept)
    await message.answer(
        f"{dept} it is! ✅\n\nWhat year you in? 🎓",
        reply_markup=get_year_keyboard()
    )
    await state.set_state(ProfileSetup.year)

@router.callback_query(F.data.startswith("year_"), StateFilter(ProfileSetup.year))
async def process_year(callback: CallbackQuery, state: FSMContext):
    year = callback.data.split("year_")[1]
    await state.update_data(year=year)

    await callback.message.edit_text(
        f"{year}! 🎉\n\nWhat should we call you? (Your name or nickname) 📝"
    )
    await state.set_state(ProfileSetup.name)
    await callback.answer()

@router.message(StateFilter(ProfileSetup.name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2 or len(name) > 30:
        await message.answer("Name should be 2-30 characters... try again 📝")
        return

    await state.update_data(name=name)
    await message.answer(
        f"Yooo {name}! 👋\n\n"
        f"Now the fun part... Write a short bio about yourself!\n\n"
        f"Make it funny, make it YOU 💯\n"
        f"(Max {MAX_BIO_LENGTH} characters)"
    )
    await state.set_state(ProfileSetup.bio)

@router.message(StateFilter(ProfileSetup.bio))
async def process_bio(message: Message, state: FSMContext):
    bio = message.text.strip()

    valid, error_msg = validate_bio(bio, MAX_BIO_LENGTH)
    if not valid:
        await message.answer(error_msg)
        return

    await state.update_data(bio=bio)
    await message.answer(
        "Yooo that bio hits different! 🔥\n\n"
        "Last step... Send a pic! 📸\n\n"
        "Make it a good one, this is your first impression 👀"
    )
    await state.set_state(ProfileSetup.photo)

@router.message(StateFilter(ProfileSetup.photo), F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id

    await state.update_data(photo_file_id=file_id)

    await message.answer(
        "Hold up... let me get to know you better 😏\n\n"
        "Quick vibe check! Answer these questions 👇"
    )

    question = VIBE_QUESTIONS[0]
    # Use edit_text for setup flow because we are editing the text message right before the quiz starts
    await message.answer(
        f"Question 1/{len(VIBE_QUESTIONS)}\n\n{question['q']}",
        reply_markup=get_vibe_keyboard(0)
    )

    await state.update_data(vibe_answers={}, vibe_question_idx=0)
    await state.set_state(ProfileSetup.vibe_quiz)

@router.message(StateFilter(ProfileSetup.photo))
async def process_photo_invalid(message: Message):
    await message.answer(
        "Bruh... upload an actual photo 📸\n\n"
        "No documents, stickers, or whatever 💀"
    )


def get_interest_categories_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    """Top-level categories with 2 per row, plus Done/Skip."""
    rows = []
    row_size = 2

    for i, cat in enumerate(INTEREST_CATEGORIES):
        btn = InlineKeyboardButton(
            text=cat["category"],
            callback_data=f"cat_{i}"
        )
        if i % row_size == 0:
            rows.append([btn])
        else:
            rows[-1].append(btn)

    # Action row
    rows.append([
        InlineKeyboardButton(text="✅ Done", callback_data="interests_done"),
        InlineKeyboardButton(text="⏭️ Skip", callback_data="interests_skip")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_interest_options_keyboard(category_idx: int, selected: List[str]) -> InlineKeyboardMarkup:
    """Show interests inside a category, with ✅ toggles and Back button."""
    options = INTEREST_CATEGORIES[category_idx]["options"]
    buttons = []
    row_size = 2

    for i, opt in enumerate(options):
        mark = "✅ " if opt in selected else ""
        btn = InlineKeyboardButton(text=f"{mark}{opt}", callback_data=f"interest_{opt}")
        if i % row_size == 0:
            buttons.append([btn])
        else:
            buttons[-1].append(btn)

    buttons.append([InlineKeyboardButton(text="🔙 Back to Categories", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



@router.callback_query(F.data.startswith("cat_"), StateFilter(ProfileSetup.interests))
async def open_category(callback: CallbackQuery, state: FSMContext):
    """Open a specific category and show its interests with summary + counter."""
    idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("interests", [])

    # Build summary line with counter
    if selected:
        summary = (
            f"✨ <b>Selected so far ({len(selected)}/7):</b>\n"
            + " • " + "\n • ".join(selected) + "\n\n"
        )
    else:
        summary = "✨ <i>No interests selected yet.</i>\n\n"

    await callback.message.edit_text(
        f"{INTEREST_CATEGORIES[idx]['category']}\n\n"
        f"{summary}"
        "Pick what resonates with you 👇",
        reply_markup=get_interest_options_keyboard(idx, selected),
        parse_mode="HTML"
    )
    await state.update_data(current_category=idx)
    await callback.answer()


@router.callback_query(F.data == "back_to_categories", StateFilter(ProfileSetup.interests))
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Return to categories view with live counter."""
    data = await state.get_data()
    selected = data.get("interests", [])
    await callback.message.edit_text(
        f"🎯 Select your interests ({len(selected)}/7)\n\nChoose a category to dive in 👇",
        reply_markup=get_interest_categories_keyboard(selected)
    )
    await callback.answer()




    
@router.callback_query(F.data.startswith("vibe_"), StateFilter(ProfileSetup.vibe_quiz))
async def process_vibe_answer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    question_idx = int(parts[1])
    answer_idx = int(parts[2])
    
    # Advance quiz step
    is_complete, _ = await _advance_vibe_quiz_step(callback, state, question_idx, answer_idx, is_edit_flow=False)

    if is_complete:
        # Transition into interests selection
        await callback.message.edit_text(
            "🔥 <b>Vibe check complete!</b>\n\n"
            "Now let’s add some flavor to your profile... 🎶⚽📚\n\n"
            "Pick up to <b>7 interests</b> that define your vibe 👇",
            reply_markup=get_interest_categories_keyboard([]),
            parse_mode="HTML"
        )
        await state.set_state(ProfileSetup.interests)
        await callback.answer()
        return

    await callback.answer()



@router.callback_query(F.data.startswith("interest_"), StateFilter(ProfileSetup.interests))
async def process_interest(callback: CallbackQuery, state: FSMContext):
    """Toggle an interest on/off inside the current category."""
    interest = callback.data.split("interest_")[1]
    data = await state.get_data()
    selected = data.get("interests", [])
    category_idx = data.get("current_category")  # track which category we’re in

    MAX_INTERESTS = 7

    if interest in selected:
        selected.remove(interest)
        action = "Removed"
    else:
        if len(selected) >= MAX_INTERESTS:
            await callback.answer(
                f"🚦 Whoa, easy there!\nYou can only pick <b>{MAX_INTERESTS}</b> interests.\nCurate your vibe ✨",
                show_alert=True,
                parse_mode="HTML"
            )
            return
        selected.append(interest)
        action = "Added"

    await state.update_data(interests=selected)

    # Build summary line with counter
    if selected:
        summary = (
            f"✨ <b>Selected so far ({len(selected)}/{MAX_INTERESTS}):</b>\n"
            + " • " + "\n • ".join(selected) + "\n\n"
        )
    else:
        summary = "✨ <i>No interests selected yet.</i>\n\n"

    # ✅ Update only the keyboard, not the whole text
    await callback.message.edit_reply_markup(
        reply_markup=get_interest_options_keyboard(category_idx, selected)
    )

    # Keep the text the same, but still show the action feedback
    await callback.answer(f"{action} {interest}")



def _format_overlap_count(count: int) -> str:
    """Format overlap counts cinematically."""
    if count < 6:
        return f"shared with some people"
    elif count < 20:
        return "shared with dozens of people"
    elif count < 100:
        return "shared with over 100  people"
    elif count < 1000:
        return "shared with hundreds of people"
    else:
        return f"shared with {count//1000}K+ people"

@router.callback_query(F.data.in_(["interests_done", "interests_skip"]), StateFilter(ProfileSetup.interests))
async def finish_interests(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    # If skipped, interests = []
    interests = data.get("interests", []) if callback.data == "interests_done" else []
   
    # Create user
    user_data = {
        'id': user_id,
        'username': callback.from_user.username,
        'name': data['name'],
        'gender': data['gender'],
        'seeking_gender': data['seeking_gender'],
        'campus': data['campus'],
        'department': data['department'],
        'year': data['year'],
        'bio': data['bio'],
        'photo_file_id': data['photo_file_id'],
        'vibe_score': json.dumps(data['vibe_answers']),
        'coins': 120
    }
    success = await db.create_user(user_data)

    if success:
        # --- Personalized teaser if interests chosen ---
        if interests:
            await db.set_user_interests(user_id, interests)

            chosen = random.choice(interests)
            query = """
                SELECT COUNT(DISTINCT i.user_id) AS overlap_count
                FROM interests i
                JOIN interest_catalog ic ON i.interest_id = ic.id
                WHERE ic.name = $1
            """
            row = await db.pool.fetchrow(query, chosen)
            overlap_count = row["overlap_count"] if row else 0

            teaser_text = (
        f"✨ { _format_overlap_count(overlap_count).capitalize() } here are into <b>{chosen}</b> too!\n\n"
        "Your vibe’s syncing fast… 🔗"
    )
            await callback.message.answer(teaser_text, parse_mode="HTML")

        # --- Referral handling ---
        if data.get('referrer_id'):
            referrer_id = data['referrer_id']
            success_ref = await db.add_referral(referrer_id, user_id)
            if success_ref:
                ref_user = await db.get_user(referrer_id)
                new_balance = ref_user.get("coins", 0)
                stats = await db.get_user_stats(referrer_id)
                total_referrals = stats.get("referrals", 0)

                try:
                    await callback.bot.send_message(
                        referrer_id,
                        (
                            "🎉 <b>Referral Success!</b>\n\n"
                            "👥 A new friend just joined <b>AAUPulse</b> using your link!\n\n"
                            "💰 You earned <b>+50🪙</b>\n"
                            f"🏦 Balance: {new_balance}🪙\n"
                            f"📊 Total Referrals: {total_referrals}\n\n"
                            "Keep sharing your link to rack up more rewards 🚀"
                        ),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Could not notify referrer {referrer_id}: {e}")

        await callback.message.answer(
            
    "🎉 <b>YOOO YOU'RE IN!</b> 🎉\n\n"
    f"Welcome to <b>AAUPulse</b>, {data['name']}! 🔥\n\n"
    "✨ Your vibe is live, your interests are locked.\n"
    "💰 You’re starting with <b>120 coins</b> to flex.\n\n"
    "Now it’s time to find your first match 😏\n\n"
    "👉 <b>❤️ Find Matches </b>\n\n",
            parse_mode="HTML"
        )
        await callback.message.edit_reply_markup(reply_markup=None)

        # Call show_main_menu with a fresh Message context
        from handlers_main import show_main_menu
        await show_main_menu(callback.message, user_id=user_id)

        profile_text = await format_profile_text(
            user_data,
            vibe_score=calculate_vibe_compatibility({}, json.loads(user_data['vibe_score'])),
            show_full=True,
            candidate_interests=await db.get_user_interests(user_id),
            revealed=True
        )
        profile_text = f"🆔 User ID: {user_id}\n\n{profile_text}"

        # Inline buttons for admin actions
        actions_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛔ Ban User", callback_data=f"admin_ban_{user_id}")],
            [InlineKeyboardButton(text="✅ Unban User", callback_data=f"admin_unban_{user_id}")]
        ])

        # Send to admin group
        from bot_config import ADMIN_NEW_USER_GROUP_ID
        if user_data.get("photo_file_id"):
            await callback.bot.send_photo(
                chat_id=ADMIN_NEW_USER_GROUP_ID,
                photo=user_data["photo_file_id"],
                caption=profile_text,
                reply_markup=actions_kb,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.bot.send_message(
                chat_id=ADMIN_NEW_USER_GROUP_ID,
                text=profile_text,
                reply_markup=actions_kb,
                parse_mode=ParseMode.HTML
            )

    else:
        await callback.message.answer("💀 Something went wrong.\nTry again with /start")

    await state.clear()
    await callback.answer()

unban_requests_today = {} 
# --- View Profile Handlers (Uses the new helper) ---
@router.message(F.text == "🙏 Request Unban")
async def request_unban(message: Message):
    user_id = message.from_user.id
    today = date.today()

    # Check and update request count
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
    from handlers_admin import user_card_text
    caption = user_card_text(user)
    # reuse your helper
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

    # Confirm to user
    await message.answer("🙏 Your unban request has been submitted to the admins. Please wait for review.")

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("You don't have a profile! Use /start to create one 🚀")
        return

    stats = await db.get_user_stats(message.from_user.id)
    
    # Use the centralized helper for display
    await _render_profile_view(message, user, stats)

@router.callback_query(F.data == "view_profile")
async def view_profile_callback(callback: CallbackQuery):
    """
    This handler ensures we can correctly call cmd_profile from an inline callback 
    by fetching the user details and using the reusable render function.
    """
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Profile error. Use /start to create one 🚀")
        await callback.answer()
        return
        
    stats = await db.get_user_stats(callback.from_user.id)
    await _render_profile_view(callback, user, stats)
    await callback.answer()

# --- EDIT PROFILE MENU ---

@router.callback_query(F.data == "edit_profile")
async def edit_profile_menu(callback: CallbackQuery, state: FSMContext):
    """Shows the main menu for specific profile edits."""
    # Ensure any previous state is cleared before starting a new edit flow
    await state.clear() 
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Change Bio", callback_data="edit_field_bio"),
            InlineKeyboardButton(text="📸 Change Photo", callback_data="edit_field_photo")
        ],
        [
            InlineKeyboardButton(text="💫 Retake Vibe Quiz", callback_data="edit_field_vibe")
        ],
        [
            InlineKeyboardButton(text="🔄 Change Identity", callback_data="edit_field_gender_seeking")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Profile", callback_data="view_profile")
        ]
    ])

    await callback.message.edit_caption(
        caption="Aight, time for a **glow-up!** ✨\n\n"
                "What needs fixing in your profile? 👇\n\n"
                "_If you change your photo, you may need to navigate back to this message to see the buttons._", # Added guidance
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# --- Edit Bio Flow ---
@router.callback_query(F.data == "edit_field_bio")
async def start_edit_bio(callback: CallbackQuery, state: FSMContext):
    """Initiates the bio editing process with an inline Cancel button."""
    user = await db.get_user(callback.from_user.id)
    current_bio = user.get('bio', 'No bio set.')

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_bio")]
    ])

    await callback.message.edit_caption(
        caption=(
            f"📝 **Current Bio:**\n`{current_bio}`\n\n"
            f"Type your **NEW** bio below! 👇\n"
            f"(Max {MAX_BIO_LENGTH} characters)"
        ),
        reply_markup=cancel_markup
    )
    await state.set_state(EditProfile.editing_bio)
    await callback.answer()
    
@router.callback_query(F.data == "cancel_edit_bio")
async def cancel_edit_bio(callback: CallbackQuery, state: FSMContext):
    """Cancels bio editing and clears FSM state."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Bio update canceled.",
        
    )
    await callback.answer("Canceled.")

@router.message(EditProfile.editing_bio)
async def complete_edit_bio(message: Message, state: FSMContext):
    """Receives and saves the new bio."""
    bio = message.text.strip()
    valid, error_msg = validate_bio(bio, MAX_BIO_LENGTH)

    if not valid:
        cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_bio")]
        ])
        
        await message.answer(
            error_msg + "\n\nTry again!",
            reply_markup=cancel_markup
        )
        return


    await db.update_user(message.from_user.id, {'bio': bio})
    await state.clear()

    await message.answer(
        "✅ Bio updated! That bio is fire 🔥\n\n"
        "Check out your new look:",
        reply_markup=None
    )
    await cmd_profile(message) # Show the updated profile

# --- Edit Photo Flow ---

@router.callback_query(F.data == "edit_field_photo")
async def start_edit_photo(callback: CallbackQuery, state: FSMContext):
    """Initiates the photo editing process with an inline Cancel button."""
    
    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_photo")]
    ])

    await callback.message.edit_caption(
        caption=(
            "📸 Send your **NEW** profile photo below! 👇\n\n"
            "Make it a good one, first impressions matter 👀"
        ),
        reply_markup=cancel_markup
    )
    await state.set_state(EditProfile.editing_photo)
    await callback.answer()


@router.message(EditProfile.editing_photo, F.photo)
async def complete_edit_photo(message: Message, state: FSMContext):
    """Receives and saves the new photo file ID."""
    photo = message.photo[-1]
    file_id = photo.file_id

    await db.update_user(message.from_user.id, {'photo_file_id': file_id})
    await state.clear()

    await message.answer(
        "✅ Photo updated! Lookin' fresh! 😎\n\n"
        "Check out your new look:",
        reply_markup=None
    )
    await cmd_profile(message)
    
 

@router.message(EditProfile.editing_photo)
async def complete_edit_photo_invalid(message: Message):
    """Handles invalid input during photo edit with an inline Cancel button."""
    
    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit_photo")]
    ])
    
    await message.answer(
        "Bruh... upload an actual photo 📸\n\n"
        "No documents, stickers, or whatever 💀 Try again!",
        reply_markup=cancel_markup
    )



# --- Retake Vibe Quiz Flow (Uses the new helper) ---




@router.message(F.text == "💫 Retake Vibe Quiz")
async def start_retake_vibe_quiz_reply(message: Message, state: FSMContext):
    """Starts the vibe quiz retake flow by providing the first inline keyboard."""
    await state.update_data(vibe_answers={}, vibe_question_idx=0)

    question = VIBE_QUESTIONS[0]

    await message.answer(
        (
            "💫 **Vibe Check Reset!** 💫\n\n"
            "This will change who you match with. Answer honestly!\n\n"
            f"Question 1/{len(VIBE_QUESTIONS)}\n\n{question['q']}"
        ),
        reply_markup=get_vibe_keyboard(0),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(EditProfile.vibe_quiz_restart_q)


@router.callback_query(F.data.startswith("vibe_"), EditProfile.vibe_quiz_restart_q)
async def process_retake_vibe_answer(callback: CallbackQuery, state: FSMContext):
    """Processes answers for the retaken vibe quiz."""
    parts = callback.data.split("_")
    question_idx = int(parts[1])
    answer_idx = int(parts[2])

    # Use the reusable helper to advance the quiz (is_edit_flow=True)
    is_complete, _ = await _advance_vibe_quiz_step(callback, state, question_idx, answer_idx, is_edit_flow=True)

    if is_complete:
        # Quiz Complete: Save the new vibe score
        data = await state.get_data()
        await db.update_user(callback.from_user.id, {'vibe_score': json.dumps(data['vibe_answers'])})
        await state.clear()

        await safe_edit(
    callback,
    "✅ Vibe Quiz updated! Your new vibe is LOCKED IN! 🔒\n\n"
    "This should shake up your matches! 😏",
    keyboard=None
)
        # Send a new message to display the profile, as editing a caption to show a new photo is complicated
        user = await db.get_user(callback.from_user.id)
        stats = await db.get_user_stats(callback.from_user.id)
        # Pass the callback to the render function, which uses callback.message
        await _render_profile_view(callback, user, stats)
        
    await callback.answer()




# --- Edit Gender/Seeking Flow ---


# --- Helper for safe edits ---
async def safe_edit(callback: CallbackQuery, text: str, keyboard=None):
    """Edit a message safely depending on whether it's media or plain text."""
    msg = callback.message
    try:
        if getattr(msg, 'photo', None) or getattr(msg, 'media_group_id', None):
            await msg.edit_caption(caption=text, reply_markup=keyboard)
        else:
            await msg.edit_text(text=text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"safe_edit failed: {e}")
        # fallback: send a new message
        await msg.answer(text, reply_markup=keyboard)


# --- Start Change Identity flow ---
@router.message(F.text == "🔄 Change Identity")
async def start_edit_identity_reply(message: Message, state: FSMContext):
    # Fetch current gender from DB
    user = await db.get_user(message.from_user.id)
    current_gender = user.get("gender") or "Not set"

    await message.answer(
        f"🔄 **Change Identity** 🔄\n\n"
        f"Your current gender is: *{current_gender}*\n\n"
        "Let's update it — what's your gender now? 👀",
        reply_markup=get_gender_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(EditProfile.editing_gender)

# --- Process Gender Selection (only) ---
@router.callback_query(F.data.startswith("gender_"))
async def process_edit_gender(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != EditProfile.editing_gender:
        await callback.answer("This action is no longer valid 😅", show_alert=True)
        return

    gender = callback.data.split("gender_")[1]

    # Update DB directly
    await db.update_user(callback.from_user.id, {"gender": gender})
    await state.clear()

    # Fetch updated profile
    user = await db.get_user(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)

    # Confirm update
    await safe_edit(callback, f"✅ Gender updated to {gender}! 🔥", keyboard=None)

    # Show updated profile view
    await _render_profile_view(callback, user, stats)
    await callback.answer()

# # --- Catch-all fallback for unhandled callbacks ---
# @router.callback_query()
# async def fallback_callback(callback: CallbackQuery):
#     await callback.answer("Oops… Something went wrong 😅 Try again.", show_alert=True)
#     logger.info(f"Unhandled callback: {callback.data}, state={await callback.bot.get_chat(callback.from_user.id)}")



# --- Academic Edit Flow ---
@router.message(F.text == "🎓 Change Academic Info")
async def start_edit_academic(message: Message, state: FSMContext):
    """Start editing academic info"""
    await message.answer(
        "🎓 Let's update your academic info! Pick a field below:",
        reply_markup=get_academic_inline_keyboard()
    )
    await state.set_state(EditProfile.editing_academic)


# --- Academic Callbacks ---
@router.callback_query(F.data == "academic_campus", EditProfile.editing_academic)
async def edit_academic_campus(callback: CallbackQuery, state: FSMContext):
    # Show campus selection inline keyboard (your existing campus options)
    await callback.message.edit_text(
        "🏫 Select your campus:",
        reply_markup=get_campus_keyboard()  # Implement this with your campuses
    )
    await state.set_state(EditProfile.editing_campus)
    await callback.answer()


@router.callback_query(F.data == "academic_department", EditProfile.editing_academic)
async def edit_academic_department(callback: CallbackQuery, state: FSMContext):
    # Show department selection inline keyboard
    await callback.message.edit_text(
        "📚 Select your department:",
        reply_markup=get_department_keyboard()  # Implement with your department options + 'Other'
    )
    await state.set_state(EditProfile.editing_department)
    await callback.answer()


@router.callback_query(F.data == "academic_year", EditProfile.editing_academic)
async def edit_academic_year(callback: CallbackQuery, state: FSMContext):
    # Show year selection inline keyboard
    await callback.message.edit_text(
        "🎓 Select your year:",
        reply_markup=get_year_keyboard()  # Implement with years options
    )
    await state.set_state(EditProfile.editing_year)
    await callback.answer()
    
    
    

@router.callback_query(F.data == "academic_cancel")
async def cancel_edit_academic(callback: CallbackQuery, state: FSMContext):
    """Cancel academic info editing and go back to main edit menu."""
    await state.clear()

    # Send a new message with main ReplyKeyboard
    await callback.message.answer(
        "❌ Academic info update canceled.\n\nBack to your profile edit menu:",
        reply_markup=get_edit_profile_main_keyboard()  # This is ReplyKeyboardMarkup
    )

    await callback.answer("Canceled.")
# --- Example: Process Campus Selection ---
@router.callback_query(F.data.startswith("campus_"), EditProfile.editing_campus)
async def process_campus_edit(callback: CallbackQuery, state: FSMContext):
    campus = callback.data.split("campus_")[1]
    await state.update_data(campus=campus)
    await db.update_user(callback.from_user.id, {"campus": campus})

    # Confirm and go back to academic menu
    await callback.message.edit_text(
        f"🏫 Campus updated to {campus}!\n\nPick another field or cancel:",
        reply_markup=get_academic_inline_keyboard()
    )
    await state.set_state(EditProfile.editing_academic)
    await callback.answer()


# --- Example: Process Department Selection ---
@router.callback_query(F.data.startswith("dept_"), EditProfile.editing_department)
async def process_department_edit(callback: CallbackQuery, state: FSMContext):
    dept = callback.data.split("dept_")[1]

    if dept == "Other":
        await callback.message.edit_text("Type your department name below 👇")
        await state.set_state(EditProfile.editing_custom_department)
    else:
        await state.update_data(department=dept)
        await db.update_user(callback.from_user.id, {"department": dept})
        await callback.message.edit_text(
            f"📚 Department updated to {dept}!\n\nPick another field or cancel:",
            reply_markup=get_academic_inline_keyboard()
        )
        await state.set_state(EditProfile.editing_academic)
    await callback.answer()


@router.message(EditProfile.editing_custom_department)
async def process_custom_department_edit(message: Message, state: FSMContext):
    dept = message.text.strip()
    if len(dept) < 2:
        await message.answer("Bruh... that's not a valid department 💀 Try again:")
        return

    await state.update_data(department=dept)
    await db.update_user(message.from_user.id, {"department": dept})

    await message.answer(
        f"📚 Department updated to {dept}!\n\nPick another field or cancel:",
        reply_markup=get_academic_inline_keyboard()
    )
    await state.set_state(EditProfile.editing_academic)


# --- Example: Process Year Selection ---
@router.callback_query(F.data.startswith("year_"), EditProfile.editing_year)
async def process_year_edit(callback: CallbackQuery, state: FSMContext):
    year = callback.data.split("year_")[1]
    await state.update_data(year=year)
    await db.update_user(callback.from_user.id, {"year": year})

    await callback.message.edit_text(
        f"🎓 Year updated to {year}!\n\nPick another field or cancel:",
        reply_markup=get_academic_inline_keyboard()
    )
    await state.set_state(EditProfile.editing_academic)
    await callback.answer()
    
    # --- Interests Callbacks (Edit Flow) ---
    
    
def get_edit_interest_categories_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    """Top-level categories with 2 per row, plus Done/Skip row."""
    rows: list[list[InlineKeyboardButton]] = []
    row_size = 2

    for i, cat in enumerate(INTEREST_CATEGORIES):
        btn = InlineKeyboardButton(text=cat["category"], callback_data=f"edit_cat_{i}")
        if i % row_size == 0:
            rows.append([btn])
        else:
            rows[-1].append(btn)

    # Action row: Done + Skip
    rows.append([
        InlineKeyboardButton(text="✅ Done", callback_data="edit_interests_done"),
        InlineKeyboardButton(text="⏭️ Skip", callback_data="edit_interests_skip"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_edit_interest_options_keyboard(category_idx: int, selected: list[str]) -> InlineKeyboardMarkup:
    """Interests inside a category, with ✅ toggles, plus Done/Back."""
    options = INTEREST_CATEGORIES[category_idx]["options"]
    buttons: list[list[InlineKeyboardButton]] = []
    row_size = 2

    for i, opt in enumerate(options):
        mark = "✅ " if opt in selected else ""
        btn = InlineKeyboardButton(text=f"{mark}{opt}", callback_data=f"interest_{opt}")
        if i % row_size == 0:
            buttons.append([btn])
        else:
            buttons[-1].append(btn)

    # Action row: Done + Back
    buttons.append([
        InlineKeyboardButton(text="✅ Done", callback_data="edit_interests_done"),
        InlineKeyboardButton(text="🔙 Back to Categories", callback_data="back_to_edit_categories"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Entry points (message commands/buttons) ---

@router.message(Command("edit_interests"))
@router.message(F.text == "🎯 Edit Interests")
async def edit_interests(message: Message, state: FSMContext):
    """Enter edit interests mode (batch selection; save on Done)."""
    user_id = message.from_user.id
    current_interests = await db.get_user_interests(user_id)

    text = (
        "🎯 <b>Edit Your Interests</b>\n\n"
        f"✨ Currently selected ({len(current_interests)}/7):\n"
    )
    if current_interests:
        text += " • " + "\n • ".join(current_interests) + "\n\n"
    else:
        text += "<i>No interests selected yet.</i>\n\n"

    text += "Choose a category, toggle interests, then tap <b>✅ Done</b>."

    await message.answer(
        text,
        reply_markup=get_edit_interest_categories_keyboard(current_interests or []),
        parse_mode=ParseMode.HTML
    )
    # Keep everything in memory until Done
    await state.set_state(EditProfile.editing_interests)
    await state.update_data(interests=current_interests or [], current_category=None)


# --- Navigation callbacks ---

@router.callback_query(F.data.startswith("edit_cat_"), EditProfile.editing_interests)
async def open_edit_category(callback: CallbackQuery, state: FSMContext):
    """Open a category; no DB writes here."""
    idx = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("interests", []) or []

    summary = (
        f"✨ <b>Selected so far ({len(selected)}/7):</b>\n"
        + (" • " + "\n • ".join(selected) + "\n\n" if selected else "")
    ) or "✨ <i>No interests selected yet.</i>\n\n"

    await callback.message.edit_text(
        f"{INTEREST_CATEGORIES[idx]['category']}\n\n"
        f"{summary}"
        "Pick what resonates with you, then tap <b>✅ Done</b> 👇",
        reply_markup=get_edit_interest_options_keyboard(idx, selected),
        parse_mode=ParseMode.HTML
    )
    await state.update_data(current_category=idx)
    await callback.answer()


@router.callback_query(F.data == "back_to_edit_categories", EditProfile.editing_interests)
async def back_to_edit_categories(callback: CallbackQuery, state: FSMContext):
    """Return to categories with live counter; still no DB write."""
    data = await state.get_data()
    selected = data.get("interests", []) or []
    await callback.message.edit_text(
        f"🎯 Select your interests ({len(selected)}/7)\n\n"
        "Toggle freely, then tap <b>✅ Done</b> to save.",
        reply_markup=get_edit_interest_categories_keyboard(selected),
        parse_mode=ParseMode.HTML
    )
    await state.update_data(current_category=None)
    await callback.answer()


# --- Toggle callbacks (state-only, fast) ---

@router.callback_query(F.data.startswith("interest_"), EditProfile.editing_interests)
async def toggle_interest_edit(callback: CallbackQuery, state: FSMContext):
    """Toggle interest in memory; save later on Done."""
    interest = callback.data.split("interest_")[1]
    data = await state.get_data()
    selected = (data.get("interests") or []).copy()
    category_idx = data.get("current_category")
    user_id = callback.from_user.id

    MAX_INTERESTS = 7

    # Handle add/remove in memory
    if interest in selected:
        selected.remove(interest)
        action = "Removed"
    else:
        if len(selected) >= MAX_INTERESTS:
            await callback.answer(
                f"🚦 Max {MAX_INTERESTS} interests. Curate your vibe ✨",
                show_alert=True
            )
            return
        selected.append(interest)
        action = "Added"

    # Update FSM only (no DB yet)
    await state.update_data(interests=selected)

    # Refresh current category keyboard to reflect ✅ marks
    if category_idx is not None:
        summary = (
            f"✨ <b>Selected so far ({len(selected)}/{MAX_INTERESTS}):</b>\n"
            + (" • " + "\n • ".join(selected) + "\n\n" if selected else "")
        ) or "✨ <i>No interests selected yet.</i>\n\n"

        await callback.message.edit_text(
            f"{INTEREST_CATEGORIES[category_idx]['category']}\n\n"
            f"{summary}"
            "Tap <b>✅ Done</b> to save, or keep toggling 👇",
            reply_markup=get_edit_interest_options_keyboard(category_idx, selected),
            parse_mode=ParseMode.HTML
        )

    await callback.answer(f"{action} {interest}")


# --- Done / Skip (single DB write, exit cleanly) ---

@router.callback_query(F.data == "edit_interests_done", EditProfile.editing_interests)
async def finish_edit_interests(callback: CallbackQuery, state: FSMContext):
    """Persist selected interests once; return to profile editing."""
    data = await state.get_data()
    user_id = callback.from_user.id
    selected = data.get("interests", []) or []

    try:
        await db.set_user_interests(user_id, selected)
    except Exception as e:
        logger.error(f"Error saving interests for user {user_id}: {e}")
        await callback.answer("Could not save interests 💀", show_alert=True)
        return

    # Confirm and exit
    await callback.message.edit_text(
        "✅ Interests updated!\n\nReturning to profile editing…",
        parse_mode=ParseMode.HTML,
        reply_markup=None
    )
    await state.clear()

    # Bring user back to profile editing menu (or main menu)
    from handlers_main import show_main_menu
    await show_main_menu(callback.message, user_id=user_id)
    await callback.answer("Saved ✅")


@router.callback_query(F.data == "edit_interests_skip", EditProfile.editing_interests)
async def skip_edit_interests(callback: CallbackQuery, state: FSMContext):
    """Discard changes; return to profile editing."""
    await callback.message.edit_text(
        "⏭️ Skipped. No changes made.\n\nReturning to profile editing…",
        parse_mode=ParseMode.HTML,
        reply_markup=None
    )
    await state.clear()

    from handlers_main import show_main_menu
    await show_main_menu(callback.message, user_id=callback.from_user.id)
    await callback.answer("Skipped ⏭️")

def get_interests_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤝 View Shared Interests")],
            [KeyboardButton(text="📊 View Trending Interests")],
            [KeyboardButton(text="🔙 Back to Main Menu")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "📊 Interest & Trends")
async def open_interests_menu(message: Message, state: FSMContext):
    await message.answer(
        "✨ What do you want to explore?\n\n"
        "• See which interests you share with others\n"
        "• Or check out the hottest trending interests right now",
        reply_markup=get_interests_menu_keyboard()
    )

@router.message(F.text == "🤝 View Shared Interests")
async def view_shared_interests(message: Message):
    user_id = message.from_user.id
    user_interests = await db.get_user_interests(user_id)

    if not user_interests:
        await message.answer(
            "😅 You haven’t picked any interests yet.\n\n"
            "Add some first so we can show your overlaps!",
            reply_markup=get_interests_menu_keyboard()
        )
        return

    query = """
        SELECT ic.name, COUNT(DISTINCT i2.user_id) AS overlap_count
        FROM interests i1
        JOIN interests i2 ON i1.interest_id = i2.interest_id
        JOIN interest_catalog ic ON i1.interest_id = ic.id
        WHERE i1.user_id = $1 AND i2.user_id != $2
        GROUP BY ic.name
        ORDER BY overlap_count DESC
        LIMIT 5
    """
    rows = await db._db.fetch(query, user_id, user_id)

    if not rows:
        text = (
            "🤔 Nobody shares your interests yet… but that makes you unique!\n\n"
            "Keep them set — matches will come."
        )
    else:
        text = "🤝 <b>Your Shared Interests</b>\n\n"
        for row in rows:
            text += f"• {row['name']} → shared with {row['overlap_count']} people\n"
        text += "\n✨ These overlaps boost your match vibes!"

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_interests_menu_keyboard())

@router.message(F.text == "📊 View Trending Interests")
async def view_trending_interests(message: Message):
    trending = await db.get_trending_interests(limit=10)

    if not trending:
        text = "😅 No trending interests yet… be the first to set yours!"
    else:
        text = "📊 <b>Top Trending Interests</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for idx, row in enumerate(trending, start=1):
            medal = medals[idx-1] if idx <= 3 else f"{idx}."
            text += f"{medal} {row['name']} — {row['count']} people\n"
        text += "\n✨ Jump in and add some of these to boost your matches!"

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_interests_menu_keyboard())
