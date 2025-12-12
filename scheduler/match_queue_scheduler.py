# scheduler/match_queue_scheduler.py

import asyncio
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID
from services.match_queue_service import MatchQueueService
from services.content_builder import build_match_drop_text

async def run_match_queue_scheduler(db, bot):
    service = MatchQueueService(db, bot)

    while True:
        try:
            # Fetch all due matches
            items = await service.get_due_items()

            if items:
                # Rank by score
                ranked = sorted(items, key=lambda i: service.compute_score(i), reverse=True)

                # Cap how many to post per slot
                to_post = ranked[:service.MAX_POSTS_PER_SLOT]
                to_reschedule = ranked[service.MAX_POSTS_PER_SLOT:]

                # Post top matches
                for item in to_post:
                    try:
                        text = build_match_drop_text(item)
                        await bot.send_message(CHANNEL_ID, text)
                        await service.mark_sent(item["id"])
                        await bot.send_message(
                            ADMIN_GROUP_ID,
                            f"🟩 MATCH POSTED\nQueue ID: {item['id']}"
                        )
                    except Exception as e:
                        await service.record_error(item["id"], str(e))

                # Reschedule leftovers
                for item in to_reschedule:
                    await service.reschedule(item["id"])
                    await bot.send_message(
                        ADMIN_GROUP_ID,
                        f"⏭️ MATCH RESCHEDULED\nQueue ID: {item['id']}"
                    )

        except Exception as e:
            await bot.send_message(
                ADMIN_GROUP_ID,
                f"🟥 SCHEDULER ERROR\n{str(e)}"
            )

        # Check every 5 minutes
        await asyncio.sleep(300)
