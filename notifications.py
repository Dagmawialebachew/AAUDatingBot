import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import db
from bot_config import CHANNEL_ID
import random
from typing import List

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

DAILY_MESSAGES = [
    "Your crush might be waiting for you... 😏",
    "Time to shoot your shot! 🎯",
    "Someone cute just joined... 👀",
    "New matches are ready! 🔥",
    "Don't leave your crush hanging... 💭"
]

WEEKLY_MESSAGES = {
    'friday': "💌 Confession Friday! Drop those anonymous confessions 🔥",
    'sunday': "😍 Blind Date Sunday! Find your match today 💘"
}

async def send_daily_notifications(bot):
    """Sends a daily motivational notification to active users."""
    try:
        # Fetch up to 100 active user IDs using the local DB wrapper
        user_ids: List[int] = await db.get_active_user_ids(limit=100) 

        message = random.choice(DAILY_MESSAGES)

        for user_id in user_ids:
            try:
                await bot.send_message(
                    user_id,
                    f"🔔 Daily Reminder!\n\n{message}\n\nOpen CrushConnect now! 💯"
                )
            except Exception as e:
                # Log non-critical errors (e.g., user blocked the bot)
                logger.error(f"Failed to send daily notification to {user_id}: {e}")

        logger.info(f"Sent daily notifications to {len(user_ids)} users")

    except Exception as e:
        logger.error(f"Error sending daily notifications: {e}")

async def send_weekly_confession_reminder(bot):
    """Posts a Confession Friday reminder to the channel and sends a personal message to active users."""
    try:
        # 1. Post to Channel
        await bot.send_message(
            CHANNEL_ID,
            "💌 It's Confession Friday! 💌\n\n"
            "Drop your anonymous confessions now 🔥\n\n"
            "Who knows? Your crush might see it 👀\n\n"
            "@CrushConnectBot"
        )

        # 2. Notify Users
        # Fetch up to 200 active user IDs
        user_ids: List[int] = await db.get_active_user_ids(limit=200)

        for user_id in user_ids:
            try:
                await bot.send_message(
                    user_id,
                    "💌 Confession Friday! 💌\n\n"
                    "Post an anonymous confession and get 5 coins! 🪙"
                )
            except Exception as e:
                logger.error(f"Failed to send Friday reminder to {user_id}: {e}")

        logger.info("Sent Confession Friday reminders")

    except Exception as e:
        logger.error(f"Error sending Friday reminders: {e}")

async def send_weekly_match_reminder(bot):
    """Posts a Blind Date Sunday reminder to the channel and sends a personal message to active users."""
    try:
        # 1. Post to Channel
        await bot.send_message(
            CHANNEL_ID,
            "😍 Blind Date Sunday! 😍\n\n"
            "Find your perfect match today! 💘\n\n"
            "Swipe, match, chat! 🔥\n\n"
            "@CrushConnectBot"
        )

        # 2. Notify Users
        # Fetch up to 200 active user IDs
        user_ids: List[int] = await db.get_active_user_ids(limit=200)

        for user_id in user_ids:
            try:
                await bot.send_message(
                    user_id,
                    "😍 Blind Date Sunday! 😍\n\n"
                    "Your match is waiting... start swiping! 💯"
                )
            except Exception as e:
                logger.error(f"Failed to send Sunday reminder to {user_id}: {e}")

        logger.info("Sent Blind Date Sunday reminders")

    except Exception as e:
        logger.error(f"Error sending Sunday reminders: {e}")



async def update_weekly_leaderboard(bot):
    """Updates the leaderboard cache and posts an announcement to the channel."""
    try:
        # Refresh the cache
        await db.update_leaderboard_cache()

        # Now fetch the updated leaderboard
        leaderboard = await db.get_weekly_leaderboard(limit=10)

        if not leaderboard:
            await bot.send_message(
                CHANNEL_ID,
                "🏆 Weekly Leaderboard Update! 🏆\n\n"
                "No data yet for this week. Keep engaging to climb the ranks! 🔥"
            )
            logger.warning("Weekly leaderboard update posted with no data")
            return

        # Build a nice text block
        lines = []
        for idx, user in enumerate(leaderboard, start=1):
            lines.append(f"{idx}. {user['name']} ({user['campus']}) — ❤️ {user['likes_received']}")

        text = (
            "🏆 Weekly Leaderboard Update! 🏆\n\n"
            "Here are this week's most popular profiles:\n\n"
            + "\n".join(lines) +
            "\n\nUse /leaderboard in the bot to see the full list 👀\n\n"
            "@CrushConnectBot"
        )

        await bot.send_message(CHANNEL_ID, text)
        logger.info("Posted weekly leaderboard update with %d entries", len(leaderboard))

    except Exception as e:
        logger.error("Error posting leaderboard: %s", e)


def setup_scheduler(bot):
    """Configures and starts the APScheduler jobs."""
    scheduler.add_job(
        send_daily_notifications,
        'cron',
        hour=19,
        minute=0,
        args=[bot],
        id='daily_notifications'
    )

    scheduler.add_job(
        send_weekly_confession_reminder,
        'cron',
        day_of_week='fri',
        hour=12,
        minute=0,
        args=[bot],
        id='friday_confessions'
    )

    scheduler.add_job(
        send_weekly_match_reminder,
        'cron',
        day_of_week='sun',
        hour=14,
        minute=0,
        args=[bot],
        id='sunday_matches'
    )

    scheduler.add_job(
        update_weekly_leaderboard,
        'cron',
        # This job will run on Monday at 10:00 AM
        day_of_week='mon',
        hour=10,
        minute=0,
        args=[bot],
        id='weekly_leaderboard'
    )

    scheduler.start()
    logger.info("Scheduler started with all jobs configured")

def shutdown_scheduler():
    """Shuts down the APScheduler."""
    scheduler.shutdown()
    logger.info("Scheduler shut down")
