import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from database import db
from bot_config import BOT_TOKEN, ADMIN_GROUP_ID
from handlers_likes import router as likes_router
from handlers_profile import router as profile_router
from handlers_main import router as main_router
from handlers_matching import router as matching_router
from handlers_chat import router as chat_router
from handlers_confession import router as confession_router
from handlers_admin import router as admin_router
from handlers_crushes import router as crushes_router
from handlers_leaderboard import router as leaderboard_router
from handlers_coin_and_shop import router as coin_and_shop_router
from handlers_invite import router as invite_router
from notifications import setup_scheduler, shutdown_scheduler
from middlewares.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

dp = Dispatcher()

dp.include_router(profile_router)
dp.include_router(main_router)
dp.include_router(matching_router)
dp.include_router(chat_router)
dp.include_router(confession_router)
dp.include_router(admin_router)
dp.include_router(leaderboard_router)
dp.message.middleware(RateLimitMiddleware(rate_limit=1))
dp.callback_query.middleware(RateLimitMiddleware(rate_limit=1))
dp.include_router(crushes_router)
dp.include_router(likes_router)  
dp.include_router(coin_and_shop_router)
dp.include_router(invite_router)

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Start the bot / Main menu"),
        BotCommand(command="profile", description="View your profile"),
        BotCommand(command="admin", description="Admin panel (admin only)")
    ]
    await bot.set_my_commands(commands)

async def on_startup(bot: Bot):
    logger.info("Bot is starting up...")
    await db.connect()
    logging.info("Bot has started and database is connected.")

    await setup_bot_commands(bot)

    setup_scheduler(bot)

    if ADMIN_GROUP_ID:
        try:
            await bot.send_message(
                ADMIN_GROUP_ID,
                "🤖 CrushConnect Bot Started! 🔥\n\n"
                "All systems operational ✅"
            )
        except Exception as e:
            logger.error(f"Could not send startup message to admin group: {e}")

    logger.info("Bot startup complete!")

async def on_shutdown(bot: Bot):
    logger.info("Bot is shutting down...")

    shutdown_scheduler()
    await db.close() 
    logger.info("Database connection closed.")

    if ADMIN_GROUP_ID:
        try:
            await bot.send_message(
                ADMIN_GROUP_ID,
                "🤖 CrushConnect Bot Stopped ⏸️"
            )
        except Exception as e:
            logger.error(f"Could not send shutdown message to admin group: {e}")

    logger.info("Bot shutdown complete!")

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
