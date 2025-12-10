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

    # Row with Unmatch + Refresh
    rows.append([
        InlineKeyboardButton(
            text="❌ Unmatch",
            callback_data=f"unmatch_confirm_{match_id}"
        ),
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data=f"refresh_{match_id}"
        )
    ])

    # Row with View Full Profile
    rows.append([
        InlineKeyboardButton(
            text="👤 View Full Profile",
            callback_data=f"viewprofile_from_chat_{match_id}"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("refresh_"))
async def refresh_pinned_card(callback: CallbackQuery, state: FSMContext):
    try:
        match_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Invalid refresh reference 💀")
        return

    user_id = callback.from_user.id
    match_data = await get_match_data_for_chat(user_id, match_id)
    if not match_data:
        await callback.answer("Match not found 💀")
        return

    other_user = match_data["user"]
    revealed = match_data["revealed"]

    # Fetch latest history
    history = await db.get_chat_history(match_id, limit=10)

    # Build bubbles (consistent sender labels)
    bubbles = []
    for msg in history[-5:]:
        sender_label = "🟢 You" if msg["sender_id"] == user_id else "🔵 Them"
        bubbles.append(bubble(sender_label, h(msg.get("message", ""))))
    history_text = "\n".join(bubbles) if bubbles else "✨ <i>No messages yet — break the ice!</i> 💬"

    # Interests + vibe context for anonymous consistency
    viewer = await db.get_user(user_id)
    viewer_interests = await db.get_user_interests(user_id) or []
    candidate_interests = await db.get_user_interests(other_user["id"]) or []

    # Header/caption using same templates as start_chat
    if revealed:
        header = caption_header(other_user, revealed=True)
        caption = (
            f"{header}\n\n"
            f"📜 <u>Last messages</u>\n{history_text}\n\n"
            "───────────────\n\n"
            "💡 <i>Say hi or drop a voice note — your move.</i>"
        )
    else:
        # Anonymous: shared/tease interests hint
        shared = list(set(candidate_interests) & set(viewer_interests))
        if shared:
            chosen = random.sample(shared, min(2, len(shared)))
            interests_hint = "✨ You both vibe with " + " & ".join(chosen)
        else:
            tease = random.sample(candidate_interests, min(2, len(candidate_interests)))
            interests_hint = "✨ They might be into " + " & ".join(tease) if tease else "✨ Their interests are waiting to be revealed..."

        partial_name = other_user.get("name", "Anon")[:4] + "…"
        header = f"💌 Chat with 🎭 Anonymous — {partial_name}"
        caption = (
            f"{header}\n\n"
            "🔒 <b>Identity Hidden</b>\n\n"
            f"{interests_hint}\n"
            "🙈 <i>Photo blurred until reveal...</i>\n\n\n"
            f"📜 <u>Last messages</u>\n{history_text}\n\n"
            "───────────────\n\n"
            "💡 <i>Send a message to break the ice!</i>"
        )

    # Keyboard and target message id
    keyboard = build_header_keyboard(match_id, revealed)
    pinned_card_id = (await state.get_data()).get("pinned_card_id")
    if not pinned_card_id:
        await callback.answer("No chat card to refresh 💀")
        return

    # Edit in place
    try:
        if revealed and other_user.get("photo_file_id"):
            await callback.bot.edit_message_caption(
                chat_id=user_id,
                message_id=pinned_card_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.bot.edit_message_text(
                chat_id=user_id,
                message_id=pinned_card_id,
                text=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        await callback.answer("🔄 Card refreshed!")
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Already up to date!")
        else:
            logger.error(f"Error refreshing card: {e}")
            await callback.answer("⚠️ Could not refresh 💀")

    else:
        await callback.answer("No pinned card found 💀")




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

    # Clean up active session and pinned state
    active_chats.pop(user_id, None)
    user_pinned = pinned_cards.get(user_id, {})
    card_msg_id = user_pinned.pop(match_id, None)
    if not user_pinned:
        pinned_cards.pop(user_id, None)
    await state.update_data(active_chat=None, pinned_card_id=None)

    # Update UI: show closed text then delete the message(s)
    text = "💔 You’ve unmatched. This chat is now closed."
    try:
        # Edit the callback message first (if possible)
        if getattr(callback.message, "caption", None) is not None:
            await callback.message.edit_caption(text, reply_markup=None)
        else:
            await callback.message.edit_text(text, reply_markup=None)
    except Exception:
        # If edit fails, try to send a fallback message (non-blocking)
        try:
            await callback.message.answer(text)
        except Exception:
            pass

    # Delete the visible chat card(s) to fully close the UI
    try:
        # Delete the message that triggered the callback (if still present)
        try:
            await callback.message.delete()
        except Exception:
            pass

        # Also delete the stored chat card (if different)
        if card_msg_id:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=card_msg_id)
            except Exception:
                # ignore if already deleted or not accessible
                pass
    except Exception as e:
        logger.warning(f"Could not fully remove chat card(s) for user {user_id}, match {match_id}: {e}")

    # Notify the other user
    try:
        match_data = await get_match_data_for_chat(user_id, match_id)
        if match_data:
            other_user = match_data["user"]
            await callback.bot.send_message(
                other_user["id"],
                "💔 Your match has ended. You will not see them again in Mutual Matches."
            )
    except Exception as e:
        logger.error(f"Could not notify other user about unmatch: {e}")

    # Bring user back to main menu
    try:
        await callback.message.answer("Returning you to the main menu…", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass

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
            InlineKeyboardButton(text="💬 Reply", callback_data=f"reply_{match_id}_{msg_id}"),
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
        if photo_file_id and revealed:
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
    """
    Enter chat with a specific match.
    - Initiator (first liker) gets cinematic teaser only.
    - Second liker (like-back) gets identity-hidden profile text until reveal.
    - Revealed users get full profile photo and header.
    """

    parts = callback.data.split("_")
    try:
        match_id = int(parts[1])
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
    initiator_id = match_data.get("initiator_id")

    # Save active chat session
    active_chats[user_id] = {
        "match_id": match_id,
        "other_user_id": other_user["id"],
        "revealed": revealed,
    }
    previous_state = await state.get_state()
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
    viewer = await db.get_user(user_id)
    viewer_interests = await db.get_user_interests(user_id)
    candidate_interests = await db.get_user_interests(other_user["id"])
    from handlers_likes import _safe_json_load

    viewer_vibe = _safe_json_load(viewer.get("vibe_score", "{}") if viewer else "{}")
    candidate_vibe = _safe_json_load(other_user.get("vibe_score", "{}"))
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

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
        if initiator_id == user_id:
            # Initiator → cinematic teaser only
            header = caption_header(other_user, revealed=True)
            revealed = True
            caption = (
                f"{header}\n\n"
                f"📜 <u>Last messages</u>\n"
                f"{history_text}\n\n"
                f"───────────────\n\n"
                f"💡 <i>Say hi or drop a voice note — your move.</i>"
            )
        else:
            # Second liker → identity-hidden profile text
            viewer_interests = viewer_interests or []
            candidate_interests = candidate_interests or []
            shared = list(set(candidate_interests) & set(viewer_interests))

            if shared:
                # show overlap
                chosen = random.sample(shared, min(2, len(shared)))
                interests_hint = "✨ You both vibe with " + " & ".join(chosen)
            else:
                # fallback to candidate’s own interests
                tease_interests = random.sample(candidate_interests or [], min(2, len(candidate_interests or [])))
                if tease_interests:
                    interests_hint = "✨ They might be into " + " & ".join(tease_interests)
                else:
                    interests_hint = "✨ Their interests are waiting to be revealed..."

            partial_name = other_user.get("name", "Anon")[:4] + "…"
            header = f"💌 Chat with 🎭 Anonymous — {partial_name}"
            caption = (
                f"{header}\n\n"
                "🔒 <b>Identity Hidden</b>\n\n"
                f"{interests_hint}\n"
                "🙈 <i>Photo blurred until reveal...</i>\n\n\n"
                f"📜 <u>Last messages</u>\n{history_text}\n\n"
                "───────────────\n\n"
                "💡 <i>Send a message to break the ice!</i>"
            )

    # --- Build keyboard ---
    keyboard = build_header_keyboard(match_id, revealed)

    # --- Prefer graceful edit of existing pinned card; fallback to delete+send if none ---
    data = await state.get_data()
    pinned_card_id = data.get("pinned_card_id")

    if pinned_card_id:
        try:
            # If the pinned card has a photo (revealed with photo), edit caption; otherwise edit text
            if revealed and other_user.get("photo_file_id"):
                await callback.bot.edit_message_caption(
                    chat_id=user_id,
                    message_id=pinned_card_id,
                    caption=caption + "\n\n🔙 Back to chat view…",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=pinned_card_id,
                    text=caption + "\n\n🔙 Back to chat view…",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error editing chat card: {e}")
            # Fallback to previous behavior if edit fails
            try:
                await callback.message.delete()
            except Exception:
                pass
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
            pinned_cards.setdefault(user_id, {})[match_id] = sent.message_id
            await state.update_data(pinned_card_id=sent.message_id)
            if revealed:
                try:
                    await sent.pin(disable_notification=True)
                except Exception:
                    pass
    else:
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
        pinned_cards.setdefault(user_id, {})[match_id] = sent.message_id
        await state.update_data(pinned_card_id=sent.message_id)
        if revealed:
            try:
                await sent.pin(disable_notification=True)
            except Exception:
                pass

    # --- Enter chat mode ---
    if previous_state != ChatState.in_chat.state:
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

@router.message(ChatState.in_chat)
async def handle_chat_message(message: Message, state: FSMContext):
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
    content_view = (
        h(message.text) if message.text else
        "🎙️ Voice message" if message.voice else
        "📷 Photo" if message.photo else
        "🌟 Sticker" if message.sticker else
        "📎 Attachment"
    )
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

    # --- check if this message is a reply ---
    data = await state.get_data()
    logger.info(f"FSM data before send: {data}")
    reply_to_msg_id = data.get("reply_to_msg_id")
    reply_to_chat_id = data.get("reply_to_chat_id")

    kwargs = {"parse_mode": ParseMode.HTML}
    quoted_text = ""

    if reply_to_msg_id:
        original = message_map.get(match_id, {}).get(reply_to_msg_id)
        if original and original.get("text"):
            quoted_text = f"🔁 Replying to: {h(original['text'])}\n\n"

    # only set reply_to_message_id if sending into the same chat
    if message.chat.id == other_user_id and reply_to_msg_id:
        kwargs["reply_to_message_id"] = reply_to_msg_id
    elif receiver_pinned_id:
        kwargs["reply_to_message_id"] = receiver_pinned_id

    notification = quoted_text + notification

    # Send media or text
    try:
        if message.voice:
            sent = await message.bot.send_voice(other_user_id, voice=message.voice.file_id, caption=notification, **kwargs)
        elif message.photo:
            sent = await message.bot.send_photo(other_user_id, photo=message.photo[-1].file_id, caption=notification, **kwargs)
        elif message.sticker:
            await message.bot.send_sticker(other_user_id, message.sticker.file_id)
            sent = await message.bot.send_message(other_user_id, notification, **kwargs)
        else:
            sent = await message.bot.send_message(other_user_id, notification, **kwargs)

        # Build inline keyboard AFTER sending
        actions_kb = build_message_actions(match_id, sent.message_id)
        await message.bot.edit_message_reply_markup(chat_id=other_user_id, message_id=sent.message_id, reply_markup=actions_kb)

        # ✅ Track message for reactions and replies keyed by match_id
        msg_map = message_map.setdefault(match_id, {})
        msg_map[sent.message_id] = {"sender_id": user_id, "text": content_text}
        logger.info(f"Built actions for match {match_id}, receiver_msg_id={sent.message_id}")
        logger.info(f"Replying with reply_to_message_id={reply_to_msg_id} in chat {other_user_id}")

        # clear reply_to only after successful send
        if reply_to_msg_id:
            await state.update_data(reply_to_msg_id=None, reply_to_chat_id=None)

        # 🎬 subtle confirmation back to sender
        to_user = await db.get_user(other_user_id)
        to_name = to_user.get("name", "them")
        confirmation = random.choice(sent_confirmation_variants(to_name))
        await message.answer(confirmation)

    except Exception as e:
        logger.error(f"Could not notify other user: {e}")


@router.callback_query(F.data.startswith("reply_"))
async def inline_reply_click(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        _, match_id_str, replied_msg_id_str = callback.data.split("_", 2)
        match_id = int(match_id_str)
        replied_msg_id = int(replied_msg_id_str)
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

    # ✅ store both message_id and chat_id for reply
    await state.update_data(
        active_chat=match_id,
        reply_to_msg_id=replied_msg_id,
        reply_to_chat_id=user_id  # the chat where this message exists
    )

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

    await callback.message.answer(
        "💬 Reply mode on — type something sweet or drop a voice note 🎙️",
        reply_markup=back_to_crushes_kb
    )
    logger.info(f"Reply click: match_id={match_id}, replied_msg_id={replied_msg_id}")

    await callback.answer()


# ---------- Reactions ----------
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

    # Look up original sender + text from message_map keyed by match_id
    msg_map = message_map.get(match_id, {})
    original = msg_map.get(msg_id)

    if original:
        sender_id = original.get("sender_id")
        original_text = original.get("text", "")

        if sender_id:
            # Get the user who reacted
            reacting_user = await db.get_user(callback.from_user.id)
            reacting_name = reacting_user.get("name", "Someone")  # fallback

            # Build cinematic reaction notification
            if original_text:
                reaction_msg = (
                    f"{emoji} {reacting_name} reacted to your message\n"
                    f"───────────────\n"
                    f"💬 {h(original_text)}"
                )
            else:
                reaction_msg = (
                    f"{emoji} {reacting_name} reacted to your message\n"
                    f"───────────────\n"
                    f"✨ (no text content)"
                )

            await callback.bot.send_message(sender_id, reaction_msg, parse_mode="HTML")


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
    try:
        match_id = int(callback.data.split("reveal_")[1])
    except Exception:
        await callback.answer("Invalid reveal reference 💀")
        return

    user_id = callback.from_user.id
    COST = 30
    refund_needed = False  # <--- control flag

    try:
        # --- 1) Balance check ---
        user = await db.get_user(user_id)
        if user.get("coins", 0) < COST:
            await callback.answer(f"Not enough coins! Need {COST} coins 💀", show_alert=True)
            return

        # --- 2) Spend coins ---
        if not await db.spend_coins(user_id, COST, "reveal_identity", "Revealed identity in chat"):
            await callback.answer("Coin transaction failed 💀", show_alert=True)
            return

        # --- 3) Mark reveal in DB ---
        if not await db.reveal_match_identity(match_id, user_id):
            refund_needed = True
            raise ValueError("Reveal DB update failed")

        # --- 4) Fetch match data ---
        match_data = await get_match_data_for_chat(user_id, match_id)
        if not match_data:
            refund_needed = True
            raise ValueError("Match data missing after reveal")

        other_user = match_data["user"]

        # --- 5) Build UI (unchanged) ---
        breakers = [
            "─────────────── ✨ ───────────────",
            "⚡ The mask comes off…",
            "🌟 A hidden crush steps into the light",
            "🎭 Identity revealed — the vibe is real",
            "💘 Sparks fly as the mystery fades",
        ]
        breaker_line = random.choice(breakers)

        viewer_vibe = json.loads(user.get("vibe_score", "{}") or "{}")
        candidate_vibe = json.loads(other_user.get("vibe_score", "{}") or "{}")
        vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)
        viewer_id = callback.from_user.id
        profile_text = await format_profile_text(
        other_user,
        vibe_score=vibe_score,
        show_full=False,
        candidate_interests = await db.get_user_interests(other_user["id"]),
        viewer_interests = await db.get_user_interests(viewer_id),
        revealed=True
    )

        reveal_caption = (
            f"{breaker_line}\n\n"
            "🎭 <b>Identity Revealed!</b>\n\n"
            f"{profile_text}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Continue Chat", callback_data=f"chat_{match_id}_0")],
            [InlineKeyboardButton(text="🔙 Back to Matches", callback_data="back_from_chat")],
        ])

        # --- 6) Send message ---
        try:
            await callback.message.delete()
        except Exception:
            pass

        if other_user.get("photo_file_id"):
            await callback.message.answer_photo(
                photo=other_user["photo_file_id"],
                caption=reveal_caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.answer(
                reveal_caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )

        # --- 7) Notify the other user ---
        try:
            sender_name = h(user.get("name", "Someone"))
            await callback.bot.send_message(
                other_user["id"],
                f"🎭 <b>{sender_name}</b> just revealed their identity!\n\n"
                "You’re no longer anonymous — time to make the chat count 💬\n\n"
                f"Go to 💖 My Crushes -> 💘Mutual Matches to see more of {sender_name}",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.warning(f"Failed to notify the other user: {e}")

        await callback.answer("Identity revealed! ✅")

    except Exception as e:
        logger.exception(f"Reveal identity crashed: {e}")
        refund_needed = True

    # --- 8) Final guaranteed refund path ---
    if refund_needed:
        try:
            await db.add_coins(user_id, COST, "purchase", "Reveal failed – coins refunded")
            await callback.answer("Reveal failed 💀 (coins refunded)", show_alert=True)
        except Exception as re:
            logger.error(f"Failed to refund coins to {user_id}: {re}")
