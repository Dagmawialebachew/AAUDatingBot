from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.exceptions import TelegramBadRequest
from database import db
import logging
from html import escape as h  # escape user names safely for HTML

logger = logging.getLogger(__name__)
router = Router()


async def safe_edit_text(message: Message, new_text: str, reply_markup=None, parse_mode=None):
    """
    Safely edit a Telegram message.
    Ignores TelegramBadRequest if the message is not modified.
    """
    try:
        await message.edit_text(new_text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug("Edit skipped: message not modified")
        else:
            raise

async def build_leaderboard_text_and_keyboard(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """
    Build the leaderboard text and keyboard for the current week.
    Adds flair emojis and highlights the user's own entry if in the Top 10,
    or shows their rank and distance if outside the Top 10.
    """
    sorted_users = await db.get_leaderboard()
    logger.debug("Leaderboard data: %s", sorted_users)

    text = "🏆 <b>Top 10 Most Liked This Week</b> 🏆\n\n"

    if not sorted_users:
        text += "No one on the board yet! 👀\n\nBe the first to get likes this week 🔥"
    else:
        # Extra flair for ranks
        rank_flair = {1: "🔥", 2: "⚡", 3: "✨"}

        for idx, row in enumerate(sorted_users, 1):
            count = row["likes_received"]
            name = h(row["name"]) if row["name"] else "Unknown"
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            flair = rank_flair.get(idx, "🎶")

            # Highlight the current user if they are in the Top 10
            if row["id"] == user_id:
                text += f"{medal} <b>{name}</b> — {count} ❤️ {flair} <i>(You)</i>\n"
            else:
                text += f"{medal} <b>{name}</b> — {count} ❤️ {flair}\n"

        # Show personal rank if not in top 10
        my_rank = await db.get_user_rank(user_id)
        if my_rank and my_rank > 10:
            text += f"\n… and you’re currently <b>#{my_rank}</b> 👀"
            # Optional: show how close they are to breaking into top 10
            lowest_top = sorted_users[-1]["likes_received"]
            my_user = await db.get_user(user_id)
            if my_user:
                my_likes = await db.get_user_likes_count(user_id)
                if my_likes is not None and my_likes < lowest_top:
                    diff = lowest_top - my_likes + 1
                    text += f"\nOnly {diff} ❤️ away from the Top 10! 🚀"

        text += "\n\nKeep swiping to make it to the top! 💯"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="leaderboard")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
    ])

    return text, keyboard


@router.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: CallbackQuery):
    """
    Callback handler: edits the existing message with the leaderboard.
    """
    text, keyboard = await build_leaderboard_text_and_keyboard(callback.from_user.id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(F.text == "🏆 Leaderboard")
async def show_leaderboard_message_handler(message: Message):
    """
    Message handler: sends a new leaderboard message when user types "🏆 Leaderboard".
    """
    text, keyboard = await build_leaderboard_text_and_keyboard(message.from_user.id)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
