import json
import logging
import html
from typing import Dict, Optional, List
from aiogram.types import ReplyKeyboardRemove
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.text_decorations import html_decoration as hd

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import db

from utils import calculate_vibe_compatibility, format_profile_text, get_random_icebreaker, vibe_label
from handlers_main import show_main_menu
import random
logger = logging.getLogger(__name__)
router = Router()



REJECTION_MESSAGES = [
    "🚫 This chat only speaks two languages: words and vibes.\nTry typing something sweet or drop a voice note 🎙️",
    "📷 Photos? Stickers? Tempting, but this chat is strictly text and voice only 💬🎙️",
    "🙅‍♂️ Only words and whispers allowed here.\nSend a message or a voice note to keep the convo flowing!",
    "🛑 That’s a cool move, but this chat is all about real talk and real voices.",
]

back_to_crushes_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔙 Back to Crushes")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

class ChatState(StatesGroup):
    in_chat = State()


# Active chat context: user_id -> { match_id, other_user_id, revealed }
active_chats: Dict[int, Dict] = {}

# Per-user pinned profile card: user_id -> { match_id -> pinned_message_id }
pinned_cards: Dict[int, Dict[int, int]] = {}

# Map messageId (on receiver side) to a logical chat message for reaction/engaging reply
# receiver_user_id -> { message_id -> { 'match_id': int, 'sender_id': int } }
message_map: Dict[int, Dict[int, Dict]] = {}


# ---------- UI helpers ----------

def h(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text)


def bubble(sender_label: str, content: str) -> str:
    return f"<b>{sender_label}</b>\n▫️ {content}\n"


def caption_header(other_user: dict, revealed: bool) -> str:
    name = h(other_user.get("name", ""))
    return f"💌 <b>Chat with {name}</b>" if revealed else "🎭 <b>Anonymous Crush Chat</b>"



def build_header_keyboard(match_id: int, revealed: bool) -> InlineKeyboardMarkup:
    rows = []

    # Reveal button for unrevealed users
    if not revealed:
        rows.append([
            InlineKeyboardButton(
                text="🎭 Reveal Identity (30 coins)",
                callback_data=f"reveal_{match_id}"
            )
        ])

    # Row with Unmatch + View Full Profile
    rows.append([
        InlineKeyboardButton(
            text="❌ Unmatch",
            callback_data=f"unmatch_confirm_{match_id}"
        ),
        InlineKeyboardButton(
            text="👤 View Full Profile",
            callback_data=f"viewprofile_from_chat_{match_id}"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)




@router.callback_query(F.data.startswith("viewprofile_from_chat_"))
async def view_profile_from_chat(callback: CallbackQuery):
    raw = callback.data
    try:
        match_id = int(raw.split("_")[-1])
    except Exception:
        await callback.answer("Invalid profile reference 💀", show_alert=True)
        return

    viewer_id = callback.from_user.id

    # Fetch match data
    match_data = await get_match_data_for_chat(viewer_id, match_id)
    if not match_data:
        await callback.answer("Profile not found 💀", show_alert=True)
        return

    other_user = match_data["user"]
    revealed = match_data["revealed"]

    # Fetch interests
    candidate_interests = await db.get_user_interests(other_user["id"])
    viewer_interests = await db.get_user_interests(viewer_id)

    # Build profile
    profile_text = await format_profile_text(
        other_user,
        show_full=True,
        revealed=revealed,
        candidate_interests=candidate_interests,
        viewer_interests=viewer_interests
    )

    # Buttons: Unmatch + Back to Chat
    actions_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Unmatch",
                callback_data=f"unmatch_confirm_{match_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Back to Chat",
                callback_data=f"chat_{match_id}"
            )
        ]
    ])

    # Delete previous message before sending new profile
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Send profile
    try:
        if revealed and other_user.get("photo_file_id"):
            await callback.message.answer_photo(
                photo=other_user["photo_file_id"],
                caption=profile_text,
                reply_markup=actions_kb,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.answer(
                profile_text,
                reply_markup=actions_kb,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error("Error sending full profile: %s", e)
        await callback.message.answer(
            profile_text,
            reply_markup=actions_kb,
            parse_mode=ParseMode.HTML
        )

    await callback.answer()


@router.callback_query(F.data.startswith("unmatch_confirm_"))
async def confirm_unmatch(callback: CallbackQuery):
    try:
        match_id = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer("Invalid unmatch reference 💀")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, unmatch", callback_data=f"unmatch_{match_id}"),
            InlineKeyboardButton(text="🔙 Cancel", callback_data=f"chat_{match_id}")
        ]
    ])

    text = (
        "⚠️ Are you sure you want to unmatch?\n\n"
        "This will close the chat and put them back into your Likes/Admirers lists."
    )

    # ✅ Check if the message has a caption (photo/video/etc.)
    try:
        if getattr(callback.message, "caption", None) is not None:
            await callback.message.edit_caption(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )

        await callback.answer()

    except Exception as e:
        await callback.answer("Something went wrong 💀")
        print(f"⚠️ confirm_unmatch error: {e}")


@router.callback_query(F.data.startswith("unmatch_"))
async def handle_unmatch(callback: CallbackQuery, state: FSMContext):
    try:
        match_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Invalid unmatch reference 💀")
        return

    user_id = callback.from_user.id

    success = await db.unmatch(match_id, user_id)
    if not success:
        await callback.answer("Could not unmatch 💀", show_alert=True)
        return

    # Fetch the updated match row for notifications
    updated_match = await db.get_match_by_id(match_id)
    logger.info(f"Updated match after unmatch: {updated_match}")


    # Clean up active session
    active_chats.pop(user_id, None)
    pinned_cards.get(user_id, {}).pop(match_id, None)
    await state.update_data(active_chat=None, pinned_card_id=None)

    # Update UI
    # Update UI safely
    text = "💔 You’ve unmatched. This chat is now closed."
    try:
        if getattr(callback.message, "caption", None) is not None:
            await callback.message.edit_caption(
                text,
                reply_markup=None
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=None
            )
    except Exception:
        await callback.message.answer(text)


    # Notify the other user
    try:
        match_data = await get_match_data_for_chat(user_id, match_id)
        if match_data:
            other_user = match_data["user"]
            await callback.bot.send_message(
                other_user["id"],
                "💔 Your match has ended. You’ll now see them again in Likes/Admirers."
            )
    except Exception as e:
        logger.error(f"Could not notify other user about unmatch: {e}")

    # Bring user back to main menu
    await callback.message.answer("Returning you to the main menu…", reply_markup=ReplyKeyboardRemove())   
    await show_main_menu(callback.message, user_id=callback.from_user.id)
    await callback.answer("Unmatched ❌")


# Minimal back keyboard
back_to_crushes_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔙 Back to Crushes")]],
    resize_keyboard=True
)

# Back + Icebreaker keyboard
chat_actions_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎲 Try Icebreaker")],
        [KeyboardButton(text="🔙 Back to Crushes")]
    ],
    resize_keyboard=True
)


def build_message_actions(match_id: int, msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{match_id}"),
            InlineKeyboardButton(text="❤️", callback_data=f"react_{match_id}_heart_{msg_id}"),
            InlineKeyboardButton(text="😂", callback_data=f"react_{match_id}_laugh_{msg_id}"),
            InlineKeyboardButton(text="🔥", callback_data=f"react_{match_id}_fire_{msg_id}"),
        ]
    ])



def sent_confirmation_variants(to_name: str) -> List[str]:
    to_display = h(to_name)
    return [
        f"✅ Sent to {to_display}",
        f"📨 {to_display} got it",
        "✨ Delivered",
        "✅ Sent",
    ]


# ---------- Data helpers ----------

async def get_match_data_for_chat(user_id: int, match_id: int) -> Optional[dict]:
    matches = await db.get_user_matches(user_id)
    for m in matches:
        if m.get("match_id") == match_id:
            return m
    return None


async def ensure_pinned_card_for_user(
    bot,
    user_id: int,
    match_id: int,
    other_user: dict,
    revealed: bool,
    history: Optional[list] = None,
) -> Optional[int]:
    """
    Ensure the target user has a pinned profile card for this match.
    Returns pinned message_id or None on failure.
    """
    user_map = pinned_cards.setdefault(user_id, {})
    if user_map.get(match_id):
        return user_map[match_id]

    header = caption_header(other_user, revealed)

    bubbles = []
    if history:
        for msg in history[-5:]:
            sender_label = "🔵 Them" if msg["sender_id"] == other_user.get("id") else "🟢 You"
            bubbles.append(bubble(sender_label, h(msg.get("message", ""))))
        history_text = "\n".join(bubbles)
    else:
        history_text = "✨ <i>No messages yet — break the ice!</i> 💬"

    caption = (
        f"{header}\n\n"
        f"📜 <u>Last messages</u>\n"
        f"{history_text}\n\n"
        f"───────────────\n\n"
        f"💡 <i>Say hi, drop a voice note, or send a sticker — your move.</i>"
    )

    keyboard = build_header_keyboard(match_id, revealed)
    photo_file_id = other_user.get("photo_file_id")

    try:
        if photo_file_id:
            sent = await bot.send_photo(
                user_id,
                photo=photo_file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        else:
            sent = await bot.send_message(
                user_id,
                caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        try:
            await bot.pin_chat_message(user_id, sent.message_id, disable_notification=True)
        except Exception:
            pass

        user_map[match_id] = sent.message_id
        return sent.message_id
    except Exception as e:
        logger.error(f"Failed to ensure pinned card for user {user_id}: {e}")
        return None


@router.callback_query(F.data.startswith("chat_"))
async def start_chat(callback: CallbackQuery, state: FSMContext):
    from handlers_likes import _safe_json_load

    """
    Enter chat with a specific match.
    - Revealed users get full profile photo and header.
    - Unrevealed users get a cinematic teaser (partial info) and last messages.
    """
    parts = callback.data.split("_")
    print('here are parts', parts)
    try:
        match_id = int(parts[1])
        print('here is teh match id', match_id)
    except Exception:
        await callback.answer("Invalid chat reference 💀")
        return

    user_id = callback.from_user.id
    match_data = await get_match_data_for_chat(user_id, match_id)
    if not match_data:
        await callback.answer("Match not found or chat error 💀")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_main_menu(callback.message)
        return

    other_user = match_data["user"]
    revealed = match_data["revealed"]

    # Save active chat session
    active_chats[user_id] = {
        "match_id": match_id,
        "other_user_id": other_user["id"],
        "revealed": revealed,
    }
    await state.update_data(active_chat=match_id)
    await state.set_state(ChatState.in_chat)

    # --- Fetch last messages ---
    history = await db.get_chat_history(match_id, limit=10)
    bubbles = []
    for msg in history[-5:]:
        sender_label = "🟢 You" if msg["sender_id"] == user_id else "🔵 Them"
        bubbles.append(bubble(sender_label, h(msg.get("message", ""))))
    history_text = "\n".join(bubbles) if bubbles else "✨ <i>No messages yet — break the ice!</i> 💬"

    # --- Build header/caption ---
    if revealed:
        header = caption_header(other_user, revealed=True)
        caption = (
            f"{header}\n\n"
            f"📜 <u>Last messages</u>\n"
            f"{history_text}\n\n"
            f"───────────────\n\n"
            f"💡 <i>Say hi or drop a voice note — your move.</i>"
        )
    else:
        # --- Cinematic teaser for unrevealed match ---
        teaser_interests = await db.get_user_interests(other_user["id"])
        tease_sample = random.sample(teaser_interests, min(2, len(teaser_interests))) if teaser_interests else []
        interests_hint = f"💡 Hint: Into " + " & ".join(tease_sample) if tease_sample else ""

        partial_name = other_user.get("name", "Anon")[:4] + "…"
        campus = hd.quote(other_user.get("campus", ""))
        department = hd.quote(other_user.get("department", ""))
        year = hd.quote(str(other_user.get("year", "")))
        bio = hd.quote(other_user.get("bio", ""))

        # Safe vibe score
        viewer = await db.get_user(user_id)
        viewer_vibe = _safe_json_load(viewer.get("vibe_score", "{}") if viewer else "{}")
        candidate_vibe = _safe_json_load(other_user.get("vibe_score", "{}"))
        vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

        header = f"🎭 Anonymous — {partial_name}"
        caption = (
            f"{header}\n"
            "🔒 <b>Identity Hidden</b>\n"
            f"🎓 {year}, {campus}\n"
            f"{vibe_label(vibe_score)}\n\n"
            f"{interests_hint}\n\n"
            "🙈 <i>Photo blurred until reveal...</i>\n\n"
            f"📜 <u>Last messages</u>\n"
            f"{history_text}\n\n"
            f"───────────────\n\n"
            f"💡 <i>Send a message to break the ice!</i>"
        )

    # --- Build keyboard ---
    keyboard = build_header_keyboard(match_id, revealed)

    # --- Clean previous message ---
    try:
        await callback.message.delete()
    except Exception:
        pass

    # --- Send chat entry ---
    if revealed and other_user.get("photo_file_id"):
        sent = await callback.message.answer_photo(
            photo=other_user["photo_file_id"],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        sent = await callback.message.answer(
            caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

    # Pin message only if revealed
    if revealed:
        try:
            await sent.pin(disable_notification=True)
        except Exception:
            pass
        pinned_cards.setdefault(user_id, {})[match_id] = sent.message_id
        await state.update_data(pinned_card_id=sent.message_id)

    # --- Remove main menu keyboard and enter chat mode ---
    await callback.message.answer(
        "💬 You’re now in chat mode. Type or send a voice note!",
        reply_markup=chat_actions_kb
    )

    await callback.answer()


@router.message(F.text == "🎲 Try Icebreaker")
async def trigger_icebreaker_from_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    match_id = data.get("active_chat")
    if not match_id:
        await message.answer("No active chat 💀")
        return

    # Now reuse your preview_icebreaker logic
    icebreaker = get_random_icebreaker()
    await state.update_data(pending_icebreaker=icebreaker, pending_match=match_id)

    preview_text = (
        "🎲 <b>Your random icebreaker!</b>\n\n"
        f"💡 <i>{h(icebreaker)}</i>\n\n"
        "Do you want to send this to your match?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Send it", callback_data=f"confirm_icebreaker_{match_id}")],
        [InlineKeyboardButton(text="🔄 Try another", callback_data=f"icebreaker_{match_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_icebreaker")]
    ])

    await message.answer(preview_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.message(F.text == "🔙 Back to Crushes")
async def leave_chat_via_button(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Clear active chat session
    if user_id in active_chats:
        del active_chats[user_id]

    data = await state.get_data()
    list_type = data.get("last_crush_list_type", "matches")
    page = data.get("last_crush_page", 0)

    await state.clear()
    from handlers_crushes import _render_crush_list_view, get_crush_dashboard_keyboard

    # Render crush list again
    await _render_crush_list_view(message, state, user_id, list_type, page)

    # Restore the full main menu reply keyboard
    await message.answer(
        "👋 Back to your crushes list!",
        reply_markup=get_crush_dashboard_keyboard()
    )
# ---------- Message handling (text/voice/photo/sticker) ----------

@router.message(ChatState.in_chat)
async def handle_chat_message(message: Message, state: FSMContext):
    """
    Handle text and voice/media, save them, notify the other user threaded
    under THEIR pinned header, attach reply/reaction buttons, and show subtle sent confirmations.
    Also detect native Telegram replies (reply_to_message_id) to make it feel natural.
    """
    user_id = message.from_user.id
    if user_id not in active_chats:
        await message.answer("No active chat. Use /leave_chat to go back to menu.")
        await state.clear()
        return

    chat = active_chats[user_id]
    match_id = chat["match_id"]
    other_user_id = chat["other_user_id"]

    # Determine content for DB
    if message.text:
        if len(message.text) > 1000:
            await message.answer("Message too long! Keep it under 1000 characters 💀")
            return
        content_text = message.text

    elif message.voice:
        content_text = "[voice message]"

    else:
    # Reject unsupported types with playful tone
        await message.answer(random.choice(REJECTION_MESSAGES))
        return
    # Persist
    success = await db.save_chat_message(match_id, user_id, content_text)
    if not success:
        await message.answer("Failed to send message 💀")
        return

    # Build outgoing bubble
    sender_user = await db.get_user(user_id)
    sender_name = h(sender_user["name"]) if chat["revealed"] else "Anonymous 🎭"

    if message.text:
        content_view = h(message.text)
    elif message.voice:
        content_view = "🎙️ Voice message"
    elif message.photo:
        content_view = "📷 Photo"
    elif message.sticker:
        content_view = "🌟 Sticker"
    else:
        content_view = "📎 Attachment"

    notification = bubble(f"💬 {sender_name}", content_view)

    # Ensure receiver has pinned card
    match_data_receiver = await get_match_data_for_chat(other_user_id, match_id)
    if match_data_receiver:
        other_for_receiver = match_data_receiver["user"]
        revealed_for_receiver = match_data_receiver["revealed"]
    else:
        other_for_receiver = {
            "id": user_id,
            "name": sender_user.get("name", ""),
            "photo_file_id": sender_user.get("photo_file_id"),
        }
        revealed_for_receiver = True

    receiver_history = await db.get_chat_history(match_id, limit=10)
    receiver_pinned_id = await ensure_pinned_card_for_user(
        message.bot,
        other_user_id,
        match_id,
        other_for_receiver,
        revealed_for_receiver,
        receiver_history,
    )

    kwargs = {"parse_mode": ParseMode.HTML}
    if receiver_pinned_id:
        kwargs["reply_to_message_id"] = receiver_pinned_id

    # Send media or text
    try:
        if message.voice:
            sent = await message.bot.send_voice(
                other_user_id,
                voice=message.voice.file_id,
                caption=notification,
                **kwargs,
            )
        elif message.photo:
            sent = await message.bot.send_photo(
                other_user_id,
                photo=message.photo[-1].file_id,
                caption=notification,
                **kwargs,
            )
        elif message.sticker:
            await message.bot.send_sticker(other_user_id, message.sticker.file_id)
            sent = await message.bot.send_message(other_user_id, notification, **kwargs)
        else:
            sent = await message.bot.send_message(other_user_id, notification, **kwargs)

        # Build inline keyboard AFTER sending
        actions_kb = build_message_actions(match_id, sent.message_id)
        await message.bot.edit_message_reply_markup(
            chat_id=other_user_id,
            message_id=sent.message_id,
            reply_markup=actions_kb
        )

        # Track message for reactions
        msg_map = message_map.setdefault(other_user_id, {})
        msg_map[sent.message_id] = {"match_id": match_id, "sender_id": user_id}

        # 🎬 NEW: subtle confirmation back to sender
        to_user = await db.get_user(other_user_id)
        to_name = to_user.get("name", "them")
        confirmation = random.choice(sent_confirmation_variants(to_name))
        await message.answer(confirmation)

    except Exception as e:
        logger.error(f"Could not notify other user: {e}")



# ---------- Inline reply and reactions ----------
@router.callback_query(F.data.startswith("reply_"))
async def inline_reply_click(callback: CallbackQuery, state: FSMContext):
    """
    When user taps 💬 Reply under a received message,
    drop them into full chat mode with pinned header + back button.
    """
    user_id = callback.from_user.id
    try:
        match_id = int(callback.data.split("reply_")[1])
    except Exception:
        await callback.answer("Invalid reply reference 💀")
        return

    # Fetch match data from receiver’s perspective
    match_data = await get_match_data_for_chat(user_id, match_id)
    if not match_data:
        await callback.answer("Chat not found 💀")
        return

    other_user = match_data["user"]
    revealed = match_data["revealed"]

    # Save active session
    active_chats[user_id] = {
        "match_id": match_id,
        "other_user_id": other_user["id"],
        "revealed": revealed,
    }
    await state.set_state(ChatState.in_chat)
    await state.update_data(active_chat=match_id)

    # Ensure pinned card exists for this user
    history = await db.get_chat_history(match_id, limit=10)
    pinned_id = await ensure_pinned_card_for_user(
        callback.bot,
        user_id,
        match_id,
        other_user,
        revealed,
        history,
    )
    await state.update_data(pinned_card_id=pinned_id)

    # Minimal back keyboard
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    back_to_crushes_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Back to Crushes")]],
        resize_keyboard=True
    )

    # Playful entry prompt
    await callback.message.answer(
        "💬 Reply mode on — type something sweet or drop a voice note 🎙️",
        reply_markup=back_to_crushes_kb
    )

    await callback.answer()


@router.callback_query(F.data.startswith("react_"))
async def react_to_message(callback: CallbackQuery):
    try:
        _, match_id_str, emoji_key, msg_id_str = callback.data.split("_")
        match_id = int(match_id_str)
        msg_id = int(msg_id_str)
    except Exception:
        await callback.answer("Invalid reaction 💀")
        return

    emoji = {"heart": "❤️", "laugh": "😂", "fire": "🔥"}.get(emoji_key, "✨")

    # Look up original sender from your message_map or DB
    msg_map = message_map.get(callback.from_user.id, {})
    sender_id = msg_map.get(msg_id, {}).get("sender_id")

    if sender_id:
    # Get the user who reacted
        reacting_user = await db.get_user(callback.from_user.id)
        reacting_name = reacting_user.get("name", "Someone")  # fallback

        await callback.bot.send_message(
            sender_id,
            f"{emoji} {reacting_name} reacted to your message!"
        )


    await callback.answer(f"{emoji} Reacted", show_alert=False)


# ---------- Navigation ----------

@router.callback_query(F.data == "back_from_chat")
async def back_to_matches_list(callback: CallbackQuery, state: FSMContext):
    from handlers_crushes import _render_crush_list_view

    user_id = callback.from_user.id

    if user_id in active_chats:
        del active_chats[user_id]

    data = await state.get_data()
    list_type = data.get("last_crush_list_type", "matches")
    page = data.get("last_crush_page", 0)

    await state.set_state(None)
    await _render_crush_list_view(callback, state, user_id, list_type, page)
    await callback.answer("Returning to Mutual Matches list.")



# ---------- Icebreaker ----------

MAX_ICEBREAKER_ROTATIONS = 5

@router.callback_query(F.data.startswith("icebreaker_"))
async def preview_icebreaker(callback: CallbackQuery, state: FSMContext):
    """
    Show a random icebreaker to the sender for confirmation before sending.
    Allows up to 5 reshuffles, edits the same preview message instead of spamming.
    """
    try:
        match_id = int(callback.data.split("icebreaker_")[1])
    except Exception:
        await callback.answer("Invalid icebreaker reference 💀")
        return

    user_id = callback.from_user.id
    chat = active_chats.get(user_id)
    if not chat:
        await callback.answer("No active chat 💀")
        return

    # Get current rotation count
    data = await state.get_data()
    rotations = data.get("icebreaker_rotations", 0)

    if rotations >= MAX_ICEBREAKER_ROTATIONS:
        await callback.answer("🚫 Max reshuffles reached (5). Pick one!", show_alert=True)
        return

    # Generate a random icebreaker
    icebreaker = get_random_icebreaker()

    # Store it temporarily in FSM
    await state.update_data(
        pending_icebreaker=icebreaker,
        pending_match=match_id,
        icebreaker_rotations=rotations + 1
    )

    # Playful preview
    preview_text = (
        "🎲 <b>Your random icebreaker!</b>\n\n"
        f"💡 <i>{h(icebreaker)}</i>\n\n"
        "Do you want to send this to your match?"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Send it", callback_data=f"confirm_icebreaker_{match_id}")],
        [InlineKeyboardButton(text="🔄 Try another", callback_data=f"icebreaker_{match_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_icebreaker")]
    ])

    # If this is a reshuffle, edit the existing preview instead of sending new
    try:
        await callback.message.edit_text(preview_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception:
        # If edit fails (first time), send new
        await callback.message.answer(preview_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    await callback.answer()
@router.callback_query(F.data.startswith("confirm_icebreaker_"))
async def confirm_icebreaker(callback: CallbackQuery, state: FSMContext):
    try:
        match_id = int(callback.data.split("confirm_icebreaker_")[1])
    except Exception:
        await callback.answer("Invalid confirmation 💀")
        return

    user_id = callback.from_user.id
    data = await state.get_data()
    icebreaker = data.get("pending_icebreaker")
    if not icebreaker:
        await callback.answer("No icebreaker pending 💀")
        return

    chat = active_chats.get(user_id)
    if not chat:
        await callback.answer("No active chat 💀")
        return

    other_user_id = chat["other_user_id"]

    # Save to DB
    if not await db.save_chat_message(match_id, user_id, icebreaker):
        await callback.answer("Failed to send 💀")
        return

    # Ensure receiver pinned card
    sender_user = await db.get_user(user_id)
    match_data_receiver = await get_match_data_for_chat(other_user_id, match_id)
    if match_data_receiver:
        other_for_receiver = match_data_receiver["user"]
        revealed_for_receiver = match_data_receiver["revealed"]
    else:
        other_for_receiver = {
            "id": user_id,
            "name": sender_user.get("name", ""),
            "photo_file_id": sender_user.get("photo_file_id"),
        }
        revealed_for_receiver = True

    receiver_history = await db.get_chat_history(match_id, limit=10)
    receiver_pinned_id = await ensure_pinned_card_for_user(
        callback.bot,
        other_user_id,
        match_id,
        other_for_receiver,
        revealed_for_receiver,
        receiver_history,
    )

    # Build notification text
    sender_name = h(sender_user["name"]) if chat["revealed"] else "Anonymous 🎭"
    notification = bubble(f"💬 {sender_name}", h(icebreaker))

    # Send message first
    try:
        sent = await callback.bot.send_message(other_user_id, notification, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Could not notify other user: {e}")
        await callback.answer("Failed to send icebreaker 💀")
        return

    # Build inline keyboard now that we have sent.message_id
    actions_kb = build_message_actions(match_id, sent.message_id)

    # Edit message to add inline keyboard
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=other_user_id,
            message_id=sent.message_id,
            reply_markup=actions_kb
        )
    except Exception:
        pass

    # Track message for reactions/replies
    msg_map = message_map.setdefault(other_user_id, {})
    msg_map[sent.message_id] = {"match_id": match_id, "sender_id": user_id}

    # Clear FSM
    await state.update_data(pending_icebreaker=None, pending_match=None, icebreaker_rotations=0)

    # Subtle confirmation to sender
    try:
        receiver_user = await db.get_user(other_user_id)
        receiver_name = receiver_user.get("name", "your match") if receiver_user else "your match"
        variants = sent_confirmation_variants(receiver_name)
        await callback.message.answer(variants[0])
    except Exception:
        pass

    await callback.answer("✅ Icebreaker sent!", show_alert=False)

@router.callback_query(F.data == "cancel_icebreaker")
async def cancel_icebreaker(callback: CallbackQuery, state: FSMContext):
    await state.update_data(pending_icebreaker=None, pending_match=None, icebreaker_rotations=0)
    await callback.answer("❌ Cancelled", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass


# ---------- Reveal identity ----------
@router.callback_query(F.data.startswith("reveal_"))
async def reveal_identity(callback: CallbackQuery, state: FSMContext):
    """
    Spend coins to reveal match identity with a dramatic full profile card:
    - Refund safeguard if anything fails after spending
    - Photo + full details (name, campus, department, year, bio)
    - Vibe match percentage
    - Rotating breaker line for emotional impact
    """
    try:
        match_id = int(callback.data.split("reveal_")[1])
    except Exception:
        await callback.answer("Invalid reveal reference 💀")
        return

    user_id = callback.from_user.id
    COST = 30

    # 1) Balance check
    user = await db.get_user(user_id)
    if user.get("coins", 0) < COST:
        await callback.answer(f"Not enough coins! Need {COST} coins 💀", show_alert=True)
        return

    # 2) Spend coins first
    if not await db.spend_coins(user_id, COST, "reveal_identity", "Revealed identity in chat"):
        await callback.answer("Something went wrong with coin transaction 💀", show_alert=True)
        return

    try:
        # 3) Persist reveal state
        if not await db.reveal_match_identity(match_id, user_id):
            # First refund path
            await db.add_coins(user_id, COST, "purchase", "Reveal failed – coins refunded")
            return

        # Keep active chat state in sync
        if user_id in active_chats:
            active_chats[user_id]["revealed"] = True

        # 4) Fetch match data for the revealed card
        match_data = await get_match_data_for_chat(user_id, match_id)
        if not match_data:
    # Log the failure reason
            logger.warning(
                "Reveal failed for user_id=%s: match_data is missing. Refund issued.",
                user_id,
                extra={
                    "callback_data": callback.data,
                    "cost": COST
                }
            )

            # Refund coins
            await db.add_coins(user_id, COST, "purchase", "Reveal failed – coins refunded")

            # Notify the user
            await callback.answer("Reveal failed 💀 (coins refunded)", show_alert=True)
            return


        other_user = match_data["user"]
        data = await state.get_data()
        last_page = data.get("last_crush_page", 0)

        # 5) Build the dramatic breaker line
        breakers = [
            "─────────────── ✨ ───────────────",
            "⚡ The mask comes off…",
            "🌟 A hidden crush steps into the light",
            "🎭 Identity revealed — the vibe is real",
            "💘 Sparks fly as the mystery fades",
        ]
        breaker_line = random.choice(breakers)

        # 6) Compute vibe match safely
        viewer_vibe = json.loads(user.get("vibe_score", "{}") or "{}")
        candidate_vibe = json.loads(other_user.get("vibe_score", "{}") or "{}")
        vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

        profile_text = await format_profile_text(other_user, show_full=True)
        profile_text += f"\n✨ Vibe Match: {vibe_score}%"

        # Add breaker + header
        reveal_caption = (
            f"{breaker_line}\n\n"
            "🎭 <b>Identity Revealed!</b>\n\n"
            f"{profile_text}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Continue Chat", callback_data=f"chat_{match_id}_{last_page}")],
            [InlineKeyboardButton(text="🔙 Back to Matches", callback_data="back_from_chat")],
        ])

        # 8) Deliver the reveal
        try:
            if other_user.get("photo_file_id"):
                try:
                    await callback.message.delete()
                except Exception:
                    pass

                await callback.message.answer_photo(
                    photo=other_user["photo_file_id"],
                    caption=reveal_caption,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                try:
                    await callback.message.edit_text(
                        reveal_caption,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    await callback.message.answer(
                        reveal_caption,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
        except Exception as e:
            logger.error(f"Error showing reveal profile: {e}")
            await callback.message.answer(
                reveal_caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )

        # 9) Notify the other user
        try:
            sender_name = h(user.get("name", ""))
            await callback.bot.send_message(
                other_user["id"],
                f"🎭 <b>{sender_name}</b> just revealed their identity!\n\n"
                "You’re no longer anonymous — time to make the chat count 💬",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Could not notify other user: {e}")

        await callback.answer("Identity revealed! ✅")

    except Exception as e:
        # 10) Global safeguard: refund on unexpected crash
        logger.exception(f"Reveal identity crashed: {e}")
        try:
            await db.add_coins(user_id, COST, "purchase", "Reveal failed – coins refunded")
        except Exception as re:
            logger.error(f"Failed to refund coins to {user_id}: {re}")
        await callback.answer("Reveal failed 💀 (coins refunded)", show_alert=True)
