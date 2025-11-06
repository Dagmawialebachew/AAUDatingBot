import json
import logging
import random
from typing import Any, Optional
from bot_config import MATCHBACK_GIFS
from aiogram import Router, F
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from bot_config import MATCH_CELEBRATIONS, MATCHBACK_GIFS, MATCH_BREAKERS, NOTIFY_GIFS
from database import db
from handlers_chat import get_match_data_for_chat
from handlers_crushes import _render_crush_list_view
from handlers_main import get_main_menu_keyboard
from handlers_matching import get_swiping_reply_keyboard, show_candidate, start_matching_flow
from utils import calculate_vibe_compatibility, format_profile_text, vibe_label

router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 8  # keep consistent with your list rendering


# -----------------------
# Utilities
# -----------------------
def _safe_json_load(value: Any) -> dict:
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


# -----------------------
# Notification keyboard
# -----------------------
def liked_notification_keyboard(liker_id: int) -> InlineKeyboardMarkup:
    """
    Inline keyboard shown to the liked user when someone likes them.
    Uses a unified callback prefix "backlike_viewprofile_" so it goes through the
    same view profile handler and preserves list_type semantics.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 View Profile", callback_data=f"backlike_viewprofile_{liker_id}_admirers_0")],
        [InlineKeyboardButton(text="❌ Ignore", callback_data="ignore_like")]
    ])


async def notify_like(bot, liker_id: int, liked_id: int):
    """Notify the liked user that someone liked them with an inline keyboard."""
    try:
        await bot.send_message(
            liked_id,
            "👀 Someone just liked you!\n\nWant to find out who?",
            reply_markup=liked_notification_keyboard(liker_id)
        )
    except Exception as e:
        logger.warning("Could not notify %s of new like: %s", liked_id, e)


# -----------------------
# Ignore notification (from notify_like)
# -----------------------
@router.callback_query(F.data == "ignore_like")
async def ignore_like_callback(callback: CallbackQuery):
    try:
        await callback.answer("Ignored 👌", show_alert=False)
        await callback.message.delete()
    except Exception as e:
        logger.error("Error handling ignore_like: %s", e)
        await callback.answer("Error ignoring like", show_alert=True)




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

    # --- Fetch match row safely ---
    match_row = await db.get_active_match_between(viewer_id, other_user["id"])
    if match_row:
        initiator_id = match_row.get("initiator_id")
        if initiator_id and initiator_id == viewer_id:
            is_revealed = True
        else:
            is_revealed = match_row.get("revealed", False)
    else:
        is_revealed = False
        logger.info("No active match found between viewer and target.")

    # --- Interests & vibe ---
    candidate_interests = await db.get_user_interests(other_user["id"])
    viewer_interests = await db.get_user_interests(viewer_id)
    viewer = await db.get_user(viewer_id)

    viewer_vibe = _safe_json_load(viewer.get("vibe_score") if viewer else "{}")
    candidate_vibe = _safe_json_load(other_user.get("vibe_score", "{}"))
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

    # --- Build profile text ---
    profile_text = await format_profile_text(
        other_user,
        vibe_score=vibe_score,
        show_full=True,
        revealed=is_revealed,
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
        if other_user.get("photo_file_id") and is_revealed:
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
        logger.error("Error sending profile: %s", e)
        await callback.message.answer(
            profile_text,
            reply_markup=actions_kb,
            parse_mode=ParseMode.HTML
        )

    await callback.answer()

# -----------------------
# Like back handler (creates like and handles match)
# -----------------------



async def get_profile_text_and_kb(
    viewer_id: int,
    target_id: int,
    match_id: int,
    list_type: str,
    page: int = 0,
    revealed: Optional[bool] = None
):
    """
    Returns (profile_text, actions_kb) for a viewer-target pair, respecting
    reveal state. If `revealed` is provided, it overrides the DB state.
    """
    viewer = await db.get_user(viewer_id)
    candidate = await db.get_user(target_id)
    if not candidate:
        return None, None

    # Vibe & interests
    viewer_vibe = _safe_json_load(viewer.get("vibe_score") if viewer else "{}")
    candidate_vibe = _safe_json_load(candidate.get("vibe_score"))
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)
    viewer_interests = await db.get_user_interests(viewer_id)
    candidate_interests = await db.get_user_interests(target_id)

    # Reveal state from DB if not explicitly passed
    if revealed is None:
        match_row = await db.get_active_match_between(viewer_id, target_id)
        is_revealed = match_row and match_row.get("revealed")
    else:
        is_revealed = revealed

    # Profile text
    profile_text = await format_profile_text(
        candidate,
        vibe_score=vibe_score,
        show_full=False,
        revealed=True
    )

    # Action buttons
    if not is_revealed and match_row:
        actions_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎭 Reveal Identity (30 coins)",
                callback_data=f"reveal_{match_row['match_id']}"
            )],
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"chat_{match_id}")],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"backtolist_{list_type}_{page}")]
        ])
    else:
        actions_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"chat_{match_id}")],
            [InlineKeyboardButton(text="🔙 Back to Crushes", callback_data=f"backtolist_{list_type}_{page}")]
        ])

    return profile_text, actions_kb


async def celebrate_match(bot, user_id: int, other_id: int, match_id: int, context: str = "swipe"):
    """
    Cinematic match celebration:
    - Reward coins
    - First liker (initiator) gets short cinematic teaser only
    - Second liker (like-back) gets identity-hidden profile text (revealed=False)
    """

    # Reward coins
    try:
        await db.add_coins(user_id, 10, "match", "Match reward bonus")
        await db.add_coins(other_id, 10, "match", "Match reward bonus")
        logger.info(f"[celebrate_match] Added 10 coins to {user_id} and {other_id}")
    except Exception as e:
        logger.error(f"[celebrate_match] Failed to add match reward coins: {e}")

    # Fetch match row
    match_row = await db.get_active_match_between(user_id, other_id)
    initiator_id = match_row.get("initiator_id") if match_row else None
    logger.info(f"[celebrate_match] match_row={match_row}, initiator_id={initiator_id}")

    async def send_profile(to_user: int, profile_owner: int, is_initiator: bool):
        viewer = await db.get_user(to_user)
        candidate = await db.get_user(profile_owner)

        breakers = [
            "─────────────── ✨ ───────────────",
            "🎉 Sparks ignite...",
            "💘 Two vibes collide!",
            "⚡ A match made on campus",
            "🌟 Connection unlocked!"
        ]
        breaker_line = random.choice(breakers)

        actions_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"chat_{match_id}")],
            [InlineKeyboardButton(text="👀 View Profile", callback_data=f"backlike_viewprofile_{profile_owner}_matches_0")]
        ])

        viewer_vibe = _safe_json_load(viewer.get("vibe_score") if viewer else "{}")
        candidate_vibe = _safe_json_load(candidate.get("vibe_score") if candidate else "{}")
        vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

        if is_initiator:
            # First liker → cinematic teaser only
            logger.info(f"[send_profile] {to_user} is INITIATOR -> sending teaser only")

            caption = (
                f"{breaker_line}\n\n"
                f"🎉 <b>It’s a Match!</b>\n\n"
                f"💰 +10 coins added!\n"
                f"Use the buttons below to start chatting or view profile."
            )

            await bot.send_message(to_user, caption, reply_markup=actions_kb, parse_mode=ParseMode.HTML)

        else:
            # Second liker → identity-hidden profile text
            logger.info(f"[send_profile] {to_user} is SECOND LIKER -> sending identity-hidden profile")

            profile_text = await format_profile_text(
                candidate,
                vibe_score=vibe_score,
                show_full=False,
                viewer_interests=viewer.get("interests"),
                candidate_interests=candidate.get("interests"),
                revealed=False   # 👈 identity hidden
            )

            caption = (
                f"{breaker_line}\n\n"
                f"🎉 <b>It’s a Match!</b>\n\n"
                f"{profile_text}\n\n"
                f"💰 +10 coins added!"
            )

            await bot.send_message(to_user, caption, reply_markup=actions_kb, parse_mode=ParseMode.HTML)

    # Deliver to both users
    await send_profile(user_id, other_id, is_initiator=(initiator_id == user_id))
    await send_profile(other_id, user_id, is_initiator=(initiator_id == other_id))


@router.callback_query(F.data.startswith("likeback_"))
async def handle_like_back_to_match(callback: CallbackQuery, state: FSMContext):
    """
    Performs 'like back' → creates match → calls celebrate_match to handle
    GIF, profile card, vibe score, CTAs, notifications, and coin reward.
    """
    admirer_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    # Create match
    result = await db.add_like(user_id, admirer_id)
    if not result or result.get("status") != "match":
        await callback.answer("Error: Match could not be created 💀", show_alert=True)
        return

    match_id = result["match_id"]

    # Clean the old admirer card
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Use the unified celebration flow
    await celebrate_match(
        bot=callback.bot,
        user_id=user_id,
        other_id=admirer_id,
        match_id=match_id,
        context="likeback"
    )

    await callback.answer()


@router.callback_query(F.data == "find_matches")
async def trigger_find_matches(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.clear()

    # Fresh message with correct user context
    await callback.bot.send_message(
        chat_id=user_id,
        text="Loading profiles... get ready to swipe! 🔥",
        reply_markup=get_swiping_reply_keyboard()
    )

    has_candidate = await show_candidate(
        callback.message,  # you can still pass this for context
        state,
        user_id,
        initial_call=True
    )

    if not has_candidate:
        await callback.bot.send_message(
            chat_id=user_id,
            text="Yo... you ran out of unique people to swipe! 😭\n\n"
                 "Try changing your filters or come back later 👀",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

# -----------------------
# Ignore specific profile (from profile card)
# -----------------------
@router.callback_query(F.data.startswith("ignore_"))
async def handle_ignore(callback: CallbackQuery, state: FSMContext):
    try:
        target_id = int(callback.data.split("_", 1)[1])
        # Optional persist ignore: await db.ignore_user(callback.from_user.id, target_id)

        # Remove the profile message (if present) and acknowledge
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.answer("Ignored 👌", show_alert=False)
    except Exception as e:
        logger.exception("Error ignoring profile: %s", e)
        await callback.answer("Error ignoring profile 💀", show_alert=True)


# -----------------------
# Back to list handler (lightweight text response)
# -----------------------

@router.callback_query(F.data.startswith("backtolist_"))
async def handle_back_to_list(callback: CallbackQuery, state: FSMContext):
    try:
        _, list_type, page_str = callback.data.split("_")
        page = int(page_str)
        user_id = callback.from_user.id

        # Directly render the list instead of sending a text
        await _render_crush_list_view(callback, state, user_id, list_type, page)
    except Exception as e:
        logger.exception("Error handling backtolist: %s", e)
        await callback.answer("Could not go back 💀", show_alert=True)
    finally:
        await callback.answer()

# -----------------------
# Unlike handler (remove a like)
# -----------------------
@router.callback_query(F.data.startswith("unlike_"))
async def handle_unlike(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    """
    Removes a like from the DB and updates the profile card message.
    Then immediately re-renders the 'My Likes' list with a playful header.
    """
    try:
        target_id = int(callback.data.split("_", 1)[1])
        user_id = callback.from_user.id

        success = await db.remove_like(user_id, target_id)
        if success:
            # Confirmation message on the profile card
            try:
                await callback.message.edit_caption(
                    "💔 You’ve taken back your like.\n\nThey won’t appear in your 'My Likes' list anymore."
                )
            except Exception:
                await callback.message.answer(
                    "💔 You’ve taken back your like.\n\nThey won’t appear in your 'My Likes' list anymore."
                )

            await callback.answer("Like removed ❌")

            # Playful rotating header
            followups = [
                "📤 Like removed — here’s your updated list",
                "🧹 Cleaned up your likes!",
                "💔 Like retracted. Back to your list:",
                "❤️ My Likes (refreshed)"
            ]
            header = random.choice(followups)

            # Now actually render the updated list
            await callback.message.answer(header)
            await _render_crush_list_view(
                callback.message,
                state,
                user_id,
                "likes",
                page=0
            )

        else:
            await callback.answer("Could not remove like 💀", show_alert=True)

    except Exception as e:
        logger.exception("Error handling unlike: %s", e)
        await callback.answer("Error removing like 💀", show_alert=True)
