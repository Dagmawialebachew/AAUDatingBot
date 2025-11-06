from datetime import datetime
import io
import logging
from PIL import Image
import aiohttp
from typing import List, Optional

logger = logging.getLogger(__name__)

async def download_and_resize_image(file_url: str, max_size: tuple = (800, 800)) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status != 200:
                    return None

                image_data = await response.read()

        image = Image.open(io.BytesIO(image_data))

        if image.mode != 'RGB':
            image = image.convert('RGB')

        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        return output.getvalue()
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None


def calculate_vibe_compatibility(vibe1: dict, vibe2: dict) -> int:
    """
    Compare two vibe dicts and return a compatibility percentage.
    Defaults to 50 if no overlap or empty answers.
    """
    if not vibe1 or not vibe2:
        return 50

    score = 0
    total = 0

    for key, val in vibe1.items():
        if key in vibe2:
            total += 1
            if vibe2[key] == val:
                score += 1

    if total == 0:
        return 50

    raw = (score / total) * 100

    # Clamp extremes so you don’t get boring 0% or 100%
    if raw == 100:
        return 95
    if raw == 0:
        return 10

    return int(raw)


def vibe_label(score: int | None) -> str:
    """
    Turn a numeric vibe score into a cinematic label.
    Handles None scores safely.
    """
    if score is None:
        return "❔ No Vibe Score Yet"
    if score >= 80:
        return f"🔥 Strong Match ({score}%)"
    elif score >= 50:
        return f"⚡ Medium Vibe ({score}%)"
    else:
        return f"❄️ Low Match ({score}%)"


def recency_score(last_active: Optional[str]) -> float:
        if not last_active:
            return 0
        try:
            dt = datetime.fromisoformat(last_active)
            days = (datetime.utcnow() - dt).days
            return max(0, 1 - days/30)  # full score if today, decays over 30 days
        except Exception:
            return 0
        
        
from aiogram.utils.text_decorations import html_decoration as hd

async def format_profile_text(
    user: dict,
    vibe_score: int = None,
    show_full: bool = False,
    viewer_interests: list = None,
    candidate_interests: list = None,
    revealed: bool = False,  # 👈 supports both modes
) -> str:
    """
    Build a cinematic profile text (revealed or anonymous) with vibe score & interests.
    Can be reused for matches, likes, admirers, etc.
    """
    # Safety and cleanup
    campus = hd.quote(user.get("campus", ""))
    department = hd.quote(user.get("department", ""))
    year = hd.quote(str(user.get("year", "")))
    bio = hd.quote(user.get("bio", ""))
    

    # ---------- REVEALED ----------
    if revealed:
        name = hd.quote(user.get("name", "Unknown"))
        text = f"👤 {name}\n"
        text += f"📍 {campus} | {department}\n"
        text += f"🎓 {year}\n\n"
        text += f"💭 {bio}\n"

        if show_full and user.get("username"):
            username = hd.quote(user["username"])
            text += f"\n📱 @{username}"

        if vibe_score is not None:
            text += f"\n\n{vibe_label(vibe_score)}"

    # ---------- ANONYMOUS ----------
    else:
        tease_interests = random.sample(candidate_interests or [], min(2, len(candidate_interests or [])))
        if tease_interests:
            interests_hint = "✨ They might be into " + " & ".join(tease_interests)
        else:
            interests_hint = "✨ Their interests are waiting to be revealed..."

        text = (
            "🔒 <b>Identity Hidden</b>\n"
            f"🎓 {year}, {campus}\n"
            f"{vibe_label(vibe_score)}\n\n"
            f"{interests_hint}\n"
            "🙈 <i>Photo blurred until reveal...</i>"
        )

    # ---------- INTERESTS ----------
    if candidate_interests is None:
        candidate_interests = []

    if viewer_interests:
        shared = list(set(viewer_interests) & set(candidate_interests))
        if shared:
            text += "\n\n🤝 <b>Shared Interests</b>\n"
            text += " • " + "\n • ".join(shared[:3])
            if len(shared) > 3:
                text += f"\n • +{len(shared)-3} more..."
        elif candidate_interests:
            text += "\n\n✨ <b>Their Interests</b>\n"
            text += " • " + "\n • ".join(candidate_interests[:3])
    else:
        if candidate_interests:
            text += "\n\n✨ <b>Interests</b>\n"
            text += " • " + "\n • ".join(candidate_interests[:3])

    return text

def generate_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

ICEBREAKERS = [
    "If you could have dinner with anyone from AAU, dead or alive, who would it be? 🍽️",
    "What's the most embarrassing thing that happened to you on campus? 😅",
    "Coffee date or campus walk? ☕️🚶",
    "Best spot on campus for a first date? 📍",
    "What's your go-to karaoke song? 🎤",
    "Netflix series you're binging right now? 📺",
    "Pineapple on pizza: yes or absolutely not? 🍕",
    "Early bird or night owl? 🌅🦉",
    "What's your hidden talent? ✨",
    "Dream travel destination? ✈️",
    "Cats or dogs? 🐱🐶",
    "What would you do with 1 million birr? 💰",
    "Favorite Ethiopian dish? 🍲",
    "Most used emoji? 😄",
    "If you could swap lives with anyone for a day, who? 🔄"
]

import random

def get_random_icebreaker() -> str:
    return random.choice(ICEBREAKERS)

def format_coins_display(coins: int) -> str:
    return f"🪙 {coins} Coins"

def validate_bio(bio: str, max_length: int = 200) -> tuple[bool, str]:
    if len(bio.strip()) < 10:
        return False, "Bio too short! Make it at least 10 characters 💬"

    if len(bio) > max_length:
        return False, f"Bio too long! Keep it under {max_length} characters 📝"

    return True, ""
