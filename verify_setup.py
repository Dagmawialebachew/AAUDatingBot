import os
import sys
from dotenv import load_dotenv

def verify_setup():
    print("🔍 CrushConnect Setup Verification\n")

    load_dotenv()

    errors = []
    warnings = []

    print("1. Checking environment variables...")

    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token or bot_token == 'your_telegram_bot_token_here':
        errors.append("❌ BOT_TOKEN not set or invalid")
    else:
        print(f"   ✅ BOT_TOKEN found (length: {len(bot_token)})")

    channel_id = os.getenv('CHANNEL_ID')
    if not channel_id:
        errors.append("❌ CHANNEL_ID not set")
    elif not channel_id.startswith('@'):
        warnings.append("⚠️  CHANNEL_ID should start with @")
    else:
        print(f"   ✅ CHANNEL_ID: {channel_id}")

    admin_group = os.getenv('ADMIN_GROUP_ID')
    if not admin_group or admin_group == 'your_admin_group_id_here':
        warnings.append("⚠️  ADMIN_GROUP_ID not set (optional but recommended)")
    else:
        print(f"   ✅ ADMIN_GROUP_ID: {admin_group}")

    supabase_url = os.getenv('VITE_SUPABASE_URL')
    if not supabase_url:
        errors.append("❌ VITE_SUPABASE_URL not set")
    else:
        print(f"   ✅ VITE_SUPABASE_URL configured")

    supabase_key = os.getenv('VITE_SUPABASE_ANON_KEY')
    if not supabase_key:
        errors.append("❌ VITE_SUPABASE_ANON_KEY not set")
    else:
        print(f"   ✅ VITE_SUPABASE_ANON_KEY configured")

    print("\n2. Checking required files...")

    required_files = [
        'bot.py',
        'bot_config.py',
        'database.py',
        'utils.py',
        'notifications.py',
        'handlers_profile.py',
        'handlers_main.py',
        'handlers_matching.py',
        'handlers_chat.py',
        'handlers_confession.py',
        'handlers_admin.py',
        'handlers_leaderboard.py',
        'requirements.txt',
        'Dockerfile',
        '.env'
    ]

    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            errors.append(f"❌ Missing file: {file}")

    print("\n3. Checking Python packages...")

    try:
        import aiogram
        print(f"   ✅ aiogram installed (version {aiogram.__version__})")
    except ImportError:
        errors.append("❌ aiogram not installed (run: pip install -r requirements.txt)")

    try:
        import supabase
        print(f"   ✅ supabase installed")
    except ImportError:
        errors.append("❌ supabase not installed (run: pip install -r requirements.txt)")

    try:
        from PIL import Image
        print(f"   ✅ Pillow installed")
    except ImportError:
        errors.append("❌ Pillow not installed (run: pip install -r requirements.txt)")

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        print(f"   ✅ APScheduler installed")
    except ImportError:
        errors.append("❌ APScheduler not installed (run: pip install -r requirements.txt)")

    print("\n" + "="*50)
    print("VERIFICATION RESULTS")
    print("="*50 + "\n")

    if errors:
        print("🚨 ERRORS (must fix):")
        for error in errors:
            print(f"  {error}")
        print()

    if warnings:
        print("⚠️  WARNINGS (optional):")
        for warning in warnings:
            print(f"  {warning}")
        print()

    if not errors:
        print("✅ Setup looks good! You can run: python bot.py")
        print("\n📋 Next steps:")
        print("  1. Make sure your bot is added as admin to your channel")
        print("  2. Run: python bot.py")
        print("  3. Open your bot in Telegram and send /start")
        print("  4. Complete profile setup")
        print("  5. Send /set_admin YOUR_USER_ID to become admin")
        return 0
    else:
        print("❌ Please fix the errors above before running the bot")
        return 1

if __name__ == "__main__":
    sys.exit(verify_setup())
