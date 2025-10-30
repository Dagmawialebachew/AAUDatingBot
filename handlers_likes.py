import json
import logging
import random
from typing import Any

from aiogram import Router, F
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from bot_config import MATCHBACK_GIFS, MATCH_BREAKERS, NOTIFY_GIFS
from database import db
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



@router.callback_query(F.data.startswith("viewprofile_") | F.data.startswith("backlike_viewprofile_"))
async def view_profile_from_list(callback: CallbackQuery, state: FSMContext):
    """
    Unified handler for viewing a profile from lists.
    Expected callback_data formats:
      - viewprofile_{user_id}_{list_type}_{page}
      - backlike_viewprofile_{user_id}_{list_type}_{page}
    list_type is one of: likes, admirers, matches
    """
    raw = callback.data
    try:
        parts = raw.split("_")
        if parts[0] == "backlike":
            _, _, user_id_str, list_type, page_str = parts
        else:
            _, user_id_str, list_type, page_str = parts
        target_id = int(user_id_str)
        page = int(page_str)
    except Exception:
        await callback.answer("Invalid profile reference 💀", show_alert=True)
        return

    candidate = await db.get_user(target_id)
    if not candidate:
        await callback.answer("Profile not found 💀", show_alert=True)
        return

    viewer_id = callback.from_user.id
    viewer = await db.get_user(viewer_id)

    # --- Vibe score ---
    viewer_vibe = _safe_json_load(viewer.get("vibe_score") if viewer else "{}")
    candidate_vibe = _safe_json_load(candidate.get("vibe_score"))
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

    # --- Interests ---
    viewer_interests = await db.get_user_interests(viewer_id)
    candidate_interests = await db.get_user_interests(target_id)

    # --- Check reveal state ---
    match_row = await db.get_match_between(viewer_id, target_id)
    is_revealed = match_row and match_row.get("revealed")

    # --- Build profile text ---
    if is_revealed:
        profile_text = await format_profile_text(candidate, vibe_score=vibe_score, show_full=False)
        await callback.message.answer(profile_text, parse_mode="HTML")

    else:
        # Pick up to 2 random interests to tease
        tease_interests = random.sample(candidate_interests, min(2, len(candidate_interests))) if candidate_interests else []
        if tease_interests:
            interests_hint = "✨ They’re into " + " & ".join(tease_interests)
        else:
            interests_hint = "✨ Their interests are waiting to be revealed..."

        profile_text = (
            "🔒 <b>Identity Hidden</b>\n"
            f"🎓 {candidate.get('year', 'Year ?')}, {candidate.get('campus', 'Campus')}\n"
            f"{vibe_label(vibe_score)}\n"
            f"{interests_hint}\n"
            "🙈 Photo blurred until reveal"
        )

    # --- Rotating breaker ---
    breakers = [
        "─────────────── ✨ ───────────────",
        "💘 Another crush appears...",
        "🎭 A new face steps into the spotlight",
        "⚡ Fresh profile unlocked!",
        "🌟 Who’s this? Let’s find out..."
    ]
    breaker_line = random.choice(breakers)
    try:
        await callback.message.answer(breaker_line)
    except Exception:
        pass

    # --- Inline actions ---
    if not is_revealed and match_row:
        actions_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎭 Reveal Identity (30 coins)",
                callback_data=f"reveal_{match_row['match_id']}"
            )],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"backtolist_{list_type}_{page}")]
        ])
    else:
        if list_type == "admirers":
            actions_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❤️ Like Back", callback_data=f"likeback_{target_id}")],
                [InlineKeyboardButton(text="❌ Ignore", callback_data=f"ignore_{target_id}")],
                [InlineKeyboardButton(text="🔙 Back to Admirers", callback_data=f"backtolist_admirers_{page}")]
            ])
        elif list_type == "likes":
            actions_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Remove Like", callback_data=f"unlike_{target_id}")],
                [InlineKeyboardButton(text="🔙 Back to My Likes", callback_data=f"backtolist_likes_{page}")]
            ])
        else:
            actions_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"chat_with_{target_id}_0")],
                [InlineKeyboardButton(text="🔙 Back to Crushes", callback_data=f"backtolist_{list_type}_{page}")]
            ])

    # --- Clean UX: remove old message ---
    try:
        await callback.message.delete()
    except Exception:
        pass

    # --- Send profile ---
    try:
        if candidate.get("photo_file_id") and is_revealed:
            await callback.message.answer_photo(
                photo=candidate["photo_file_id"],
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
        logger.error("Error showing profile: %s", e)
        await callback.message.answer(profile_text, reply_markup=actions_kb, parse_mode=ParseMode.HTML)

    await callback.answer()


# -----------------------
# Like back handler (creates like and handles match)
# -----------------------


async def celebrate_match(bot, user_id: int, other_id: int, match_id: int, context: str = "swipe"):
    """
    Unified match celebration: sends GIF (optional), profile card, vibe score, CTAs,
    notifies the other user, and rewards coins.
    context = "swipe" | "likeback"
    """
    user = await db.get_user(user_id)
    other = await db.get_user(other_id)

    # Reward coins
    try:
        await db.update_user(user_id, {"$inc": {"coins": 30}})
    except Exception as e:
        logger.error(f"Failed to add match reward coins: {e}")

    # Optional: only show GIF in likeback context
    if context == "likeback":
        try:
            await bot.send_animation(
                user_id,
                animation=random.choice(MATCHBACK_GIFS),
                caption="🎉 <b>IT'S A MATCH!</b> 🎉\n\n✨ +30 coins added!",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    # Vibe score
    viewer_vibe = json.loads(user.get("vibe_score", "{}") or "{}")
    candidate_vibe = json.loads(other.get("vibe_score", "{}") or "{}")
    vibe_score = calculate_vibe_compatibility(viewer_vibe, candidate_vibe)

    # Profile card caption
    profile_text = format_profile_text(other, show_full=True)
    caption = (
        f"{random.choice(MATCH_BREAKERS)}\n\n"
        "💖 <b>New Mutual Match</b>\n\n"
        f"{profile_text}\n"
        f"✨ Vibe Match: {vibe_score}%"
    )

    # Inline CTAs
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Go to Chat", callback_data=f"chat_{match_id}")],
    ])

    # Send profile card
    try:
        if other.get("photo_file_id"):
            await bot.send_photo(user_id, other["photo_file_id"], caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(user_id, caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error sending match profile card: {e}")

    # Notify the other user
    keyboard_notify = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"chat_{match_id}")],
        [InlineKeyboardButton(
    text="👀 View Profile",
    callback_data=f"backlike_viewprofile_{other_id}_matches_0"
)],
        [InlineKeyboardButton(text="❤️ Find Matches", callback_data="find_matches")]
    ])

    try:
        await bot.send_message(
            other_id,
            f"💘 <b>You’ve unlocked a new crush!</b>\n\n{user['name']} liked you back — you’re now a match. 💖",
            reply_markup=keyboard_notify,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Could not notify matched user: {e}")



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
    """
    Lightweight back action: sends a short text referencing the relevant section.
    Formats:
      backtolist_likes_{page} -> respond with '💘 Mutual Matches'
      backtolist_admirers_{page} -> respond with '❤️ My Likes'
      backtolist_matches_{page} -> respond with '💘 Mutual Matches'
    """
    try:
        _, list_type, page_str = callback.data.split("_")
        page = int(page_str)  # parsed for future use
        if list_type == "likes":
            await callback.message.answer("💘 Mutual Matches")
        elif list_type == "admirers":
            await callback.message.answer("❤️ My Likes")
        else:
            await callback.message.answer("💖 Back to Crushes")
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
