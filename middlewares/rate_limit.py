from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta
import json


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
                lang_data = data.get('lang_data', {})
                rate_limit_msg = lang_data.get('rate_limit', 'Please slow down!')

                if isinstance(event, Message):
                    await event.answer(rate_limit_msg)
                elif isinstance(event, CallbackQuery):
                    await event.answer(rate_limit_msg, show_alert=True)
                return

        self.user_last_action[user_id] = now
        return await handler(event, data)
