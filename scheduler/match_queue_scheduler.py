# scheduler/match_queue_scheduler.py

import asyncio
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID
from services.match_queue_service import MatchQueueService
from services.content_builder import build_match_drop_text

async def run_match_queue_scheduler(db, bot):
    service = MatchQueueService(db, bot)

    while True:
        item = None  # <-- ensures item always exists
        try:
            item = await service.get_due_item()

            if item:
                text = build_match_drop_text(item)
                await bot.send_message(CHANNEL_ID, text)
                await service.mark_sent(item["id"])
                await bot.send_message(
                    ADMIN_GROUP_ID,
                    f"🟩 MATCH POSTED\nQueue ID: {item['id']}"
                )

        except Exception as e:
            if item:
                await service.record_error(item["id"], str(e))

        await asyncio.sleep(300)  # Check every 5 minutes
