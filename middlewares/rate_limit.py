from asyncio.log import logger
import random
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
import json

from bot_config import RATE_LIMIT_MESSAGES
from database import Database


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self.user_last_action: Dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()

        if user_id in self.user_last_action:
            time_passed = (now - self.user_last_action[user_id]).total_seconds()
            if time_passed < self.rate_limit:
                rate_limit_msg = random.choice(RATE_LIMIT_MESSAGES)

                if isinstance(event, CallbackQuery):
                    # Show popup with OK button
                    await event.answer(rate_limit_msg, show_alert=True)
                # For Message events, just ignore (no chat clutter)
                return

        self.user_last_action[user_id] = now
        return await handler(event, data)




class GracefulFallbackMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        from handlers_main import show_main_menu
        try:
            return await handler(event, data)
        except Exception as e:
            # Log unexpected errors
            await event.answer(
                "🤔 I didn’t quite get that.\n\n"
                "Here are some things you can try:\n"
                "• /start — open the main menu\n"
                "• /help — see available commands\n"
                "Or just tap a button below 👇",
                reply_markup=show_main_menu(event)
            )
            return None
        


import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, date

logger = logging.getLogger(__name__)

# In-memory tracker for unban requests per day
unban_requests_today: dict[int, dict] = {}  # {user_id: {"date": date, "count": int}}

def get_banned_user_kb() -> ReplyKeyboardMarkup:
    """Keyboard shown to banned users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Profile")],
            [KeyboardButton(text="🙏 Request Unban")]
        ],
        resize_keyboard=True
    )

POSSIBLE_REASONS = [
    "• Spam or promotional content",
    "• Explicit or inappropriate profile photo",
    "• Harassment or offensive language",
    "• Fake or misleading identity",
    "• Solicitation or scams",
]

# Exact actions blocked for banned users
BLOCKED_ACTIONS = {
    "❤️ Find Matches",
    "💖 My Crushes",
    "💌 Confess",
    "⚙️ More",
    "🗂️ Browse Users",
    "👤 View Profile",
    "👀 View Profile",
    "💬 Open Chat",
}

# Callback prefixes blocked for banned users
BLOCKED_PREFIXES = ("chat_", "like_", "match_")

class BanCheckMiddleware(BaseMiddleware):
    def __init__(self, db):
        super().__init__()
        self.db = db

    async def __call__(self, handler, event, data):
        user_id = None
        user_text = None

        if isinstance(event, Message):
            user_id = event.from_user.id
            user_text = event.text or ""
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            user_text = event.data or ""

        if user_id:
            user = await self.db.get_user(user_id)
            if user and user.get("is_banned"):
                # Block if exact match OR prefix match
                if user_text in BLOCKED_ACTIONS or any(
                    user_text.startswith(prefix) for prefix in BLOCKED_PREFIXES
                ):
                    reasons_text = "\n".join(POSSIBLE_REASONS)
                    text = (
                        f"🚫 You are banned from using this bot.\n\n"
                        f"Possible reasons:\n{reasons_text}\n\n"
                        "You may edit your profile to request reinstatement.\n"
                        "Or request an unban (max 2 times per day)."
                    )
                    if isinstance(event, Message):
                        await event.answer(text, reply_markup=get_banned_user_kb())
                    elif isinstance(event, CallbackQuery):
                        await event.message.answer(text, reply_markup=get_banned_user_kb())
                        await event.answer("You are banned.", show_alert=True)

                    # Log without emojis to avoid Windows encoding errors
                    logger.info(
                        "Blocked banned user %s on action %s", user_id, user_text
                    )
                    return

                # Allowed self-service actions
                logger.info(
                    "Banned user %s accessed allowed action %s", user_id, user_text
                )

        # Pass event to next handler
        return await handler(event, data)
