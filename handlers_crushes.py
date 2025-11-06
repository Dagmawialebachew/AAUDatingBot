import json
import logging
import random
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

from database import db
from handlers_main import show_main_menu 
# Assuming you have a separate file for chat logic, otherwise define ChatState here
from handlers_chat import start_chat, ChatState # Placeholder: Must be implemented/imported
from utils import calculate_vibe_compatibility, format_profile_text 

logger = logging.getLogger(__name__)
router = Router()

# --- FSM States for List/Pagination Context ---
class CrushState(StatesGroup):
    viewing_matches = State()
    viewing_admirers = State()
    viewing_likes = State()

# --- Constants ---
PAGE_SIZE = 5

# --- Keyboard Helpers ---

def get_crush_dashboard_keyboard() -> ReplyKeyboardMarkup:
    """Returns the main Crush Dashboard Reply Keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💘 Mutual Matches")],
            [KeyboardButton(text="👀 Who Liked Me"), KeyboardButton(text="❤️ My Likes")],
            [KeyboardButton(text="🔙 Main Menu")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def _generate_list_pagination_keyboard(
    data_list: list, 
    current_page: int, 
    list_type: str, 
    user_id: int,   # 👈 pass this in
) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard for pagination and item selection.
    """
    total_pages = (len(data_list) + PAGE_SIZE - 1) // PAGE_SIZE
    start_index = current_page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(data_list))
    
    keyboard_buttons = []
    
    # 1. Item Selection Buttons (2 columns)
    row = []
    for item in data_list[start_index:end_index]:
        # FIX for KeyError: 'user' - Determine the user object based on list_type
        item_user = item['user'] if list_type == 'matches' else item 
       
        
        if list_type == 'matches':
            initiator_id = item.get("initiator_id")
      
            # If revealed OR viewer is the initiator → show name
            if item.get("revealed") or initiator_id == user_id:
                text = f"💬 {item_user['name']}"
            else:
                text = "🎭 Anonymous Match"

            callback_data = f"chat_{item['match_id']}_{current_page}"
        elif list_type == 'admirers':
            # Show only first 4 characters of the name
            safe_name = item_user['name'][:4] + "…" if item_user.get('name') else "Anon…"
            text = f"👤 {safe_name}"
            callback_data = f"viewprofile_{item_user['id']}_admirers_{current_page}"
        else:  # 'likes'
            text = f"👤 {item_user['name']}"
            callback_data = f"viewprofile_{item_user['id']}_likes_{current_page}"
            
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row:
        keyboard_buttons.append(row)

    # 2. Pagination Controls
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"page_{list_type}_{current_page - 1}"))
    
    nav_row.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{list_type}_{current_page + 1}"))
        
    if nav_row:
        keyboard_buttons.append(nav_row)

    # 3. Back Button to Dashboard
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="crush_dashboard")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)



from aiogram.utils.text_decorations import html_decoration as hd

async def _render_crush_list_view(
    source: Message | CallbackQuery,
    state: FSMContext,
    user_id: int,
    list_type: str,
    page: int = 0
):
    """General function to fetch data, set state, and render the paginated list."""

    message = source.message if isinstance(source, CallbackQuery) else source

    list_data = []
    title = ""
    current_state = None

    if list_type == 'matches':
        list_data = await db.get_user_matches(user_id)
        title = "💘 Mutual Matches"
        current_state = CrushState.viewing_matches
    elif list_type == 'admirers':
        list_data = await db.get_who_liked_me(user_id)
        title = "👀 People Who Liked You"
        current_state = CrushState.viewing_admirers
    elif list_type == 'likes':
        list_data = await db.get_my_likes(user_id)
        title = "❤️ People You Liked"
        current_state = CrushState.viewing_likes

    # --- Handle empty lists gracefully ---
    if not list_data:
        no_data_messages = {
            'matches': "😢 No mutual matches yet.\n\nStart swiping — someone special might be waiting! ❤️",
            'admirers': "🙈 No one has liked you yet (that you know of 😉)\n\nKeep swiping and someone will!",
            'likes': "💔 You haven’t liked anyone recently.\n\nMaybe give some hearts out? ❤️"
        }

        if isinstance(source, CallbackQuery):
            try:
                await source.message.delete()
            except Exception:
                pass

        await message.answer(
            no_data_messages[list_type],
            reply_markup=get_crush_dashboard_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(None)
        return

    # Save state
    await state.set_state(current_state)
    await state.update_data(current_list_data=list_data, current_page=page)

    # Pagination
    start_index = page * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(list_data))

    list_summary = ""
    for idx, item in enumerate(list_data[start_index:end_index]):
        user = item['user'] if list_type == 'matches' else item
        safe_name = hd.quote(user.get("name", "Unknown"))
        # Limit to first 4 characters, append ellipsis if longer
        full_name = user.get("name", "Unknown")
        safe_name = hd.quote(full_name[:4] + "…" if len(full_name) > 4 else full_name)


        if list_type == 'matches':
            initiator_id = item.get("initiator_id")
            print('here is intiator id', initiator_id)
            print('here is user id', user_id)
            # If revealed OR viewer is the initiator → treat as revealed
            if item.get("revealed") or initiator_id == user_id:
                status = "✅ Revealed"
                safe_name = hd.quote(user.get("name", "Unknown"))
            else:
                status = "🎭 Hidden"
                safe_name = "Anon…"

            list_summary += f"{start_index + idx + 1}. <b>{safe_name}</b> — {status}\n"

        elif list_type == 'admirers':
        # 👀 Hide name until user taps
            list_summary += f"{start_index + idx + 1}. 🎭 Anonymous Admirer — Tap to view/match\n"

        elif list_type == 'likes':
            WAITING_VARIANTS = [
                "⏳ Still cooking…",
                "👀 Watching from afar",
                "💌 Waiting for reply",
                "🕒 Patience pays…"
            ]
            status = random.choice(WAITING_VARIANTS)
            list_summary += f"{start_index + idx + 1}. <b>{safe_name}</b> ({status})\n"

    keyboard = _generate_list_pagination_keyboard(list_data, page, list_type, user_id)

    final_text = (
        f"<b>{title}</b> ({len(list_data)})\n\n"
        f"Page {page + 1} of {(len(list_data) + PAGE_SIZE - 1) // PAGE_SIZE}\n\n"
        "Tap a profile below to take action 👇\n\n"
        f"{list_summary}"
    )

    # --- Send or edit message ---
    if isinstance(source, CallbackQuery):
        try:
            await message.edit_text(
                final_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error editing message, sending new one: {e}")
            await message.answer(
                final_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        await source.answer()
    else:
        await message.answer(
            final_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

# --- 🔹 Main Crush Dashboard Entry (No changes) ---

@router.message(F.text == "💖 My Crushes")
async def show_crush_dashboard(message: Message):
    """
    Main entrypoint to view matches, likes, and admirers.
    """
    await message.answer(
        "💖 *Your Crush Zone*\n\n"
        "Check who you’ve matched with, who liked you, and the ones you liked. 👀🔥",
        reply_markup=get_crush_dashboard_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# --- 1. Message Handlers to Start List View (No changes, they call the corrected _render) ---

@router.message(F.text == "💘 Mutual Matches")
async def start_show_mutual_matches(message: Message, state: FSMContext):
    """Initiates the paginated view for mutual matches."""
    await _render_crush_list_view(message, state, message.from_user.id, 'matches', page=0)

@router.message(F.text == "👀 Who Liked Me")
async def start_show_who_liked_me(message: Message, state: FSMContext):
    """Initiates the paginated view for admirers."""
    await _render_crush_list_view(message, state, message.from_user.id, 'admirers', page=0)

@router.message(F.text.in_([
    "❤️ My Likes",
    "📤 Like removed — here’s your updated list",
    "🧹 Cleaned up your likes!",
    "💔 Like retracted. Back to your list:"
]))
async def start_show_my_likes(message: Message, state: FSMContext):
    await _render_crush_list_view(message, state, message.from_user.id, 'likes', page=0)



@router.callback_query(F.data.startswith("page_"))
async def handle_pagination(callback: CallbackQuery, state: FSMContext):
    """Handles pagination button presses for all crush lists."""
    _, list_type, new_page_str = callback.data.split('_')
    new_page = int(new_page_str)
    
    await _render_crush_list_view(callback, state, callback.from_user.id, list_type, page=new_page)


# --- 3. Action Handlers (Chat/Detail View) ---

@router.callback_query(F.data.startswith("chat_"), F.state == CrushState.viewing_matches)
async def handle_match_chat_selection(callback: CallbackQuery, state: FSMContext):
    """
    Handles clicking a mutual match name/button to start a chat.
    This acts as a bridge to your existing chat logic.
    """
    # Data format: chat_[match_id]_[page_number]
    match_id_str, current_page_str = callback.data.split('_')[1:3]
    
    # Preserve the current list/page info for the 'Back' button in chat
    await state.update_data(
        last_crush_page=int(current_page_str),
        last_crush_list_type='matches'
    )
    
    # Modify the callback data to match the expected format of the original start_chat handler
    callback.data = f"chat_{match_id_str}"
    
    # IMPORTANT: Call the external start_chat handler logic
    await start_chat(callback, state)


@router.callback_query(F.data.startswith("viewprofile_"), F.state == CrushState.viewing_admirers)
async def handle_admirer_selection(callback: CallbackQuery, state: FSMContext):
    """Shows a detailed profile view for an admirer with options to Like Back (Match)."""
    # Data format: viewadm_[user_id]_[page_number]
    admirer_id_str, current_page_str = callback.data.split('_')[1:3]
    admirer_id = int(admirer_id_str)
    
    await state.update_data(
        last_crush_page=int(current_page_str),
        last_crush_list_type='admirers'
    )
    
    admirer = await db.get_user(admirer_id)
    
    # Ensure this function exists in utils.py

# ✅ Await the coroutine to get the actual string
    profile_text = await format_profile_text(admirer)

    await callback.message.answer(profile_text, parse_mode="HTML")
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # This button triggers the action to create a match
        [InlineKeyboardButton(text="❤️ Like Back (Match!)", callback_data=f"likeback_{admirer_id}")],
        # Add a reveal option here if you want to use coins to see the profile text fully
        [InlineKeyboardButton(text="🔙 Back to Admirers", callback_data="back_to_last_crush_list")]
    ])
    
    # Delete the previous list message before sending the profile photo
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer_photo(
        photo=admirer.get('profile_pic_url', 'default_photo_id'), # Use .get for safety
        caption=f"👀 **Admirer Profile:** {admirer['name']}\n\n" + profile_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@router.callback_query(F.data == "crush_dashboard")
async def back_to_crush_dashboard_callback(callback: CallbackQuery, state: FSMContext):
    """Back button from a list view to the main dashboard."""
    await state.clear()
    await show_crush_dashboard(callback.message)
    await callback.answer()

@router.callback_query(F.data == "back_to_last_crush_list")
async def back_to_last_crush_list(callback: CallbackQuery, state: FSMContext):
    """Returns to the last paginated list (e.g., from the admirer profile view)."""
    data = await state.get_data()
    
    list_type = data.get('last_crush_list_type', 'matches')
    page = data.get('last_crush_page', 0)
    
    # Delete the photo/detail message and re-render the paginated list
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    # We pass the message object from the callback here to reuse the chat context
    await _render_crush_list_view(callback.message, state, callback.from_user.id, list_type, page)
    await callback.answer()


# --- Reply Keyboard Back Handlers (Kept from original) ---

@router.message(F.text == "🔙 My Crushes")
async def back_to_crush_dashboard_msg(message: Message):
    await show_crush_dashboard(message)

@router.message(F.text == "🔙 Main Menu")
async def back_to_main_menu(message: Message):
    await show_main_menu(message)