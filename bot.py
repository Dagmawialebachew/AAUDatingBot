import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from database import db
from handlers_likes import router as likes_router
from handlers_profile import router as profile_router
from handlers_main import router as main_router
from handlers_matching import router as matching_router
from handlers_chat import router as chat_router
from handlers_confession import router as confession_router
from handlers_admin import ADMIN_IDS, router as admin_router
from handlers_crushes import router as crushes_router
from handlers_leaderboard import router as leaderboard_router
from handlers_coin_and_shop import router as coin_and_shop_router
from handlers_invite import router as invite_router
from notifications import setup_scheduler, shutdown_scheduler
from middlewares.rate_limit import RateLimitMiddleware, GracefulFallbackMiddleware, BanCheckMiddleware

# -------------------- Env --------------------
load_dotenv()  # optional locally; Render sets env vars from render.yaml

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")  # keep as string if it's a chat/channel id
# If you need int: ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0")) or None
BASE_URL = os.getenv("BASE_URL", "")          # e.g., https://aaudatingbot.onrender.com
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", "8080"))

# -------------------- Logging --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# -------------------- Dispatcher --------------------
dp = Dispatcher()

def setup_handlers(dp: Dispatcher):
    dp.include_router(profile_router)
    dp.include_router(main_router)
    dp.include_router(matching_router)
    dp.include_router(chat_router)
    dp.include_router(confession_router)
    dp.include_router(admin_router)
    dp.include_router(leaderboard_router)
    dp.include_router(crushes_router)
    dp.include_router(likes_router)
    dp.include_router(coin_and_shop_router)
    dp.include_router(invite_router)

    dp.message.middleware(RateLimitMiddleware(rate_limit=1))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limit=1))
    
    dp.message.middleware(BanCheckMiddleware(db))
    dp.callback_query.middleware(BanCheckMiddleware(db))
    
    dp.message.middleware(GracefulFallbackMiddleware())
    dp.callback_query.middleware(GracefulFallbackMiddleware())

# -------------------- Bot Commands --------------------
from aiogram.types import BotCommandScopeDefault, BotCommandScopeChat

user_commands = [
    BotCommand(command="start", description="🚀 Start • Main Menu"),
    BotCommand(command="profile", description="👤 My Profile"),
    BotCommand(command="help", description="❓ Help & Support"),
]


admin_commands = [
    BotCommand(command="admin", description="🛠️ Admin Panel"),
    BotCommand(command="broadcast", description="📢 Broadcast Message"),
]


async def setup_bot_commands(bot: Bot):
    # Default commands for all users
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Admin‑only commands (scoped to each admin’s chat)
    for admin_id in ADMIN_IDS:
        await bot.set_my_commands(admin_commands + user_commands, scope=BotCommandScopeChat(chat_id=admin_id))
async def on_startup(bot: Bot):
    logger.info("Bot is starting up...")
    await db.connect()
    await setup_bot_commands(bot)
    setup_scheduler(bot)
    # if ADMIN_GROUP_ID:
    #     try:
    #         await bot.send_message(
    #             ADMIN_GROUP_ID,
    #             "🤖 CrushConnect Bot Started! 🔥\n\nAll systems operational ✅",
    #         )
    #     except Exception as e:
    #         logger.error(f"Could not send startup message to admin group: {e}")
    logger.info("Bot startup complete!")

async def on_shutdown(bot: Bot):
    logger.info("Bot is shutting down...")
    shutdown_scheduler()
    await db.close()
    # if ADMIN_GROUP_ID:
    #     try:
    #         await bot.send_message(ADMIN_GROUP_ID, "🤖 CrushConnect Bot Stopped ⏸️")
    #     except Exception as e:
    #         logger.error(f"Could not send shutdown message to admin group: {e}")
    logger.info("Bot shutdown complete!")

# -------------------- Health Check --------------------
async def health_check(request):
    return web.Response(text="OK")

# -------------------- Webhook App Factory --------------------
async def create_app() -> web.Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    setup_handlers(dp)

    app = web.Application()
    app.router.add_get("/health", health_check)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    async def on_startup_app(app: web.Application):
        await on_startup(bot)
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        if not BASE_URL:
            logger.warning("BASE_URL is empty — webhook may not work. Set BASE_URL to your Render URL.")
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook set to: {webhook_url}")

    async def on_shutdown_app(app: web.Application):
        await on_shutdown(bot)
        await bot.session.close()

    app.on_startup.append(on_startup_app)
    app.on_cleanup.append(on_shutdown_app)

    return app

# -------------------- Polling Mode --------------------
async def start_polling():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    setup_handlers(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

# -------------------- Entrypoint --------------------
if __name__ == "__main__":
    if "--polling" in sys.argv:
        asyncio.run(start_polling())
    else:
        logger.info(f"Starting webhook server on http://0.0.0.0:{PORT}")
        web.run_app(create_app(), host="0.0.0.0", port=PORT)
