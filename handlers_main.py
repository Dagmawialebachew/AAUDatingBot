from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from database import db
from utils import generate_referral_link, get_random_icebreaker
from handlers_profile import show_edit_profile_menu_from_main # Import the new function
from aiogram.fsm.context import FSMContext
import logging
from typing import Tuple
logger = logging.getLogger(__name__)
router = Router()

# --- Keyboards ---


@router.message(F.text == "✏️ Profile")
async def edit_profile_menu_from_main(message: Message, state: FSMContext):
    """
    Handles the '✏️ Edit Profile' Reply Keyboard button press 
    and launches the profile edit flow.
    """
    await show_edit_profile_menu_from_main(message, state)

# def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="❤️ Find Matches"), KeyboardButton(text="💖 My Crushes")],
#             [KeyboardButton(text="✏️ Edit Profile"), KeyboardButton(text="💌 Crush Confession")],
#             [KeyboardButton(text="🏆 Leaderboard"),KeyboardButton(text="🪙 Coins & Shop") ],
#             [KeyboardButton(text="👥 Invite Friends"), KeyboardButton(text="🎮 Mini Games")],
#             [KeyboardButton(text="🤝 View Shared/ 📊 Trending Interests")]

            
#         ],
#         resize_keyboard=True
#     )


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❤️ Find Matches"), KeyboardButton(text="💖 My Crushes")],
            [KeyboardButton(text="✏️ Profile"), KeyboardButton(text="💌 Confess")],
            [KeyboardButton(text="⚙️ More")]
        ],
        resize_keyboard=True,
        input_field_placeholder="✨ What’s your next move..."
    )

def get_more_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Interest & Trends"), KeyboardButton(text="🏆 Leaderboard")],
            [KeyboardButton(text="🪙 Coins & Shop"), KeyboardButton(text="👥 Invite Friends")],
            # [KeyboardButton(text="🎮 Play")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
        input_field_placeholder="⚙️ Explore more options..."
    )

def get_back_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Main Menu")]],
        resize_keyboard=True
    )
    


@router.message(F.text == "⚙️ More")
async def show_more_menu(message: Message):
    await message.answer(
        "⚙️ More options unlocked:",
        reply_markup=get_more_menu_keyboard()
    )

@router.message(F.text == "🔙 Back")
async def back_to_main_menu(message: Message):
    await message.answer(
        "🔙 Back to main menu:",
        reply_markup=get_main_menu_keyboard()
    )
    
# from html import escape as h  # escape user names safely for HTML

# async def _get_leaderboard_text_and_keyboard() -> Tuple[str, InlineKeyboardMarkup]:
#     sorted_users = await db.get_weekly_leaderboard()

#     if not sorted_users:
#         text = (
#             "🏆 Weekly Leaderboard 🏆\n\n"
#             "No one on the board yet! 👀\n\n"
#             "Be the first to get likes this week 🔥"
#         )
#     else:
#         text = "🏆 Top 10 Most Liked This Week 🏆\n\n"

#         for idx, row in enumerate(sorted_users, 1):
#             uid = row["id"]
#             count = row["likes_received"]
#             name = h(row["name"]) if row["name"] else "Unknown"
#             medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
#             text += f"{medal} <b>{name}</b> — {count} ❤️\n"


#         text += "\n\nKeep swiping to make it to the top! 💯"

#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="🔄 Refresh", callback_data="leaderboard")],
#         [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
#     ])

#     return text, keyboard

# --- Handlers ---



Router()
from aiogram.enums import ParseMode
from aiogram.filters import Command
@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        text=(
            "<b>🆘 Welcome to CrushConnect Help</b>\n\n"
            "Here’s everything you can do with this bot — no fluff, just the good stuff:\n\n"

            "🔄 <b>Swiping</b>\n"
            "Swipe through curated profiles with Like, Skip, and Filter controls.\n"
            "• ❤️ Like\n"
            "• 👋 Skip\n"
            "• 🎯 Change Filter \n"
            "• 🏠 Main Menu\n\n"

            "🎯 <b>Filters</b>\n"
            "• 📍 Campus\n"
            "• 🎓 Year\n"
            "• ✨ Clear All Filters\n\n"

            "💘 <b>Matches</b>\n"
            "When you both like each other, you’ll get a cinematic match reveal:\n"
            "• 🎉 Match celebration\n"
            "• 💬 Go to Chat\n"
            "• 💰 +30 coins reward\n\n"

            "💌 <b>Confessions</b>\n"
            "Send anonymous confessions. Admins review before posting to the channel.\n"
            "• ✅ Approve / ❌ Reject\n"
            "• ❤️ React if it’s about you\n\n"

            "👤 <b>Profile</b>\n"
            "• 📝 Edit Bio\n"
            "• 📸 Change Photo\n"
            "• 💫 Retake Vibe Quiz\n"
            "• 🔄 Change Gender/Seeking\n\n"

         
            "🧠 <b>Tips</b>\n"
            "• If buttons disappear, return to the latest message.\n"
            "• If filters are too strict, loosen them or invite friends.\n"
            "• Coins are added automatically for matches and key actions.\n\n"

            "🔐 <b>Privacy</b>\n"
            "We respect your privacy. Learn more at:\n"
            "https://privacy.microsoft.com/en-us/privacystatement\n\n"

            "✨ <i>Built for connection. Designed for joy.</i>"
        ),
        parse_mode=ParseMode.HTML
    )
    
import random
from datetime import date

async def show_main_menu(message: Message, user_id: int = None):
    uid = user_id or message.from_user.id
    user = await db.get_user(uid)

    if not user:
        await message.answer(
            "Use /start to create your profile first! 🚀",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Record daily login and calculate streak
    await db.record_daily_login(uid)
    streak = await db.get_daily_streak(uid)
    print('here is your streak for today', streak)

    # Cinematic openers
    openers = [
        f"🎬 <b>Scene reset...</b>\nWelcome back, {user['name']}!",
        f"🌟 The spotlight’s on you, {user['name']}!",
        f"⚡ Energy check: {user['name']} just entered the stage!",
        f"🔥 Back in the game, {user['name']}!"
    ]

    # Dynamic teasers
    online_count = await db.count_active_users()
    admirers_count = await db.count_new_likes(uid)

    teasers = []
    if online_count and online_count > 20:
        teasers.append(f"✨ <b>{online_count}</b> people are online right now")
    if admirers_count and admirers_count > 0:
        teasers.append(f"💌 You have <b>{admirers_count}</b> new admirers waiting")

    teaser_text = "\n".join(teasers) if teasers else "👀 The stage is yours..."

    # Wide pool of rotating tips
    tips = [
        # Matches
        "💡 Tip: Swipe wisely — every like could be your next match.",
        "💡 Tip: Shared interests boost your match chances. Curate them carefully.",
        # Crushes
        "💡 Tip: Check 'My Crushes' to see who you’ve liked — don’t leave them hanging.",
        # Likes
        "💡 Tip: Peek at 'Who Liked Me' — your admirers might surprise you.",
        # Confessions
        "💡 Tip: Post a Crush Confession anonymously and see if sparks fly.",
        # Leaderboard
        "💡 Tip: Climb the leaderboard — likes and matches earn you bragging rights.",
        # Invites
        "💡 Tip: Invite friends — every referral earns you bonus 💎.",
        # Coins & Shop
        "💡 Tip: Spend coins in the shop to unlock reveals and premium perks.",
        "💡 Tip: Track your coin history to see how you’re investing your vibe.",
        # Mini‑games
        "💡 Tip: Try mini‑games to earn coins and break the ice.",
        # Icebreakers
        "💡 Tip: Use icebreakers to start chats without the awkward pause.",
        # Reveal Identity
        "💡 Tip: Reveal your identity in chat when the timing feels right — mystery builds tension."
    ]
    tip_text = random.choice(tips)

    # Daily streak message
    streak_text = f"🔥 Daily Streak: <b>{streak} days</b> in a row!" if streak > 1 else "🔥 Your streak starts today!"

    # Final cinematic text
    text = (
        f"{random.choice(openers)} 👋\n\n"
        f"💎 Balance: <b>{user['coins']}</b>\n"
        f"{streak_text}\n\n"
        f"{teaser_text}\n\n"
        f"{tip_text}\n\n"
        "What’s the next move? 😏"
    )

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    
@router.message(F.text == "🔙 Main Menu")
async def main_menu_callback(message: Message):
    await show_main_menu(message)
    
    

@router.callback_query(F.data == "main_menu")
async def main_menu_inline_callback(callback: CallbackQuery):
    await callback.message.delete()
    await show_main_menu(callback.message, user_id=callback.from_user.id)
    await callback.answer()
    
@router.message(F.text == "🎮 Mini Games")
async def mini_games(message: Message):
    icebreaker = get_random_icebreaker()
    text = (
        "🎮 Random Icebreaker Question! 🎮\n\n"
        f"{icebreaker}\n\n"
        "Think about your answer... might come in handy later 😏"
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Mini Games")],
            [KeyboardButton(text="🔙 Main Menu")]
        ],
        resize_keyboard=True
    )

    await message.answer(text, reply_markup=keyboard)

# @router.message(F.text == "💖 My Crushes")
# async def my_crushes(message: Message):
#     matches = await db.get_user_matches(message.from_user.id)

#     if not matches:
#         text = "No matches yet... 😢\n\nTime to start swiping! 🔥"
#         keyboard = ReplyKeyboardMarkup(
#             keyboard=[
#                 [KeyboardButton(text="❤️ Find Matches")],
#                 [KeyboardButton(text="🔙 Main Menu")]
#             ],
#             resize_keyboard=True
#         )
#     else:
#         text = f"💖 Your Matches ({len(matches)}):\n\n"
#         keyboard_rows = []
#         for idx, match in enumerate(matches[:10]):
#             match_user = match['user']
#             revealed_text = f"✅ {match_user['name']}" if match['revealed'] else f"🎭 Anonymous Match #{idx+1}"
#             keyboard_rows.append([KeyboardButton(text=revealed_text)])

#         keyboard_rows.append([KeyboardButton(text="🔙 Main Menu")])
#         keyboard = ReplyKeyboardMarkup(keyboard=keyboard_rows, resize_keyboard=True)

#     await message.answer(text, reply_markup=keyboard)
