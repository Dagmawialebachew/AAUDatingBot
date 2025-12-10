# services/content_builder.py
import random
import json
from datetime import datetime

# Import onboarding label maps (emoji + text)
from bot_config import YEARS, AAU_DEPARTMENTS, AAU_CAMPUSES

# Reverse maps: plain value -> "emoji text" label
YEAR_LABELS = {v: k for k, v in YEARS.items()}
DEPT_LABELS = {v: k for k, v in AAU_DEPARTMENTS.items()}
CAMPUS_LABELS = {v: k for k, v in AAU_CAMPUSES.items()}

SPECIAL_EMOJIS = {
    "high-vibe": "💘",
    "freshman-senior": "🍼🎓",
    "cross-campus": "🚌",
    "same-department": "👯‍♂️",
    "opposite-department": "⚔️",
    "shared-interests": "✨",
}
TEMPLATES = {
    "high-vibe": [
        "{emoji} 🔗 MATCH DROP — HIGH VIBE {emoji}\n\n"
        "Synced at {vibe_score}% 💯\n"
        "{dept1} × {dept2}\n"
        "{year1} × {year2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Bro… this is basically a relationship 😭🔥",

        "{emoji} 🔗 MATCH DROP — CRAZY MATCH VIBES\n\n"
        "Vibe score: {vibe_score}% ✨\n"
        "{dept1} × {dept2}\n"
        "{campus1} × {campus2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "AAU is cooking couples again 😩💗",
    ],

    "freshman-senior": [
        "{emoji} 🔗 MATCH DROP — Freshman × Senior Combo!\n\n"
        "{year1} × {year2}\n"
        "{dept1} × {dept2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Mentorship finna turn into situationship 😭🔥",

        "{emoji} 🔗 MATCH DROP — The forbidden match 😳\n\n"
        "Freshman × Senior\n"
        "{campus1} × {campus2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Free notes AND free rides 😭🚗",
    ],

    "cross-campus": [
        "{emoji} 🔗 MATCH DROP — CROSS CAMPUS!\n\n"
        "{campus1} × {campus2}\n"
        "{dept1} × {dept2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Distance can’t stop a vibe 😭🚌🔥",

        "{emoji} 🔗 MATCH DROP — Two campuses, one vibe\n\n"
        "{campus1} ↔️ {campus2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Love is paying transport today 😩💸",
    ],

    "same-department": [
        "{emoji} 🔗 MATCH DROP — Same Department!\n\n"
        "{dept1} × {dept2}\n"
        "{year1} × {year2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Group mates → soulmates 😭💗",

        "{emoji} 🔗 MATCH DROP — Major × Major combo!\n\n"
        "Both from {dept1}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Already saw each other in class 💀🔥",
    ],

    "opposite-department": [
        "{emoji} 🔗 MATCH DROP — Opposites attract!\n\n"
        "{dept1} × {dept2}\n"
        "{year1} × {year2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Balance restored ⚖️🔥",

        "{emoji} 🔗 MATCH DROP — Wild combo spotted!\n\n"
        "{dept1} × {dept2}\n\n"
        "Shared loves:\n{interests}\n\n"
        "Pure chaos energy 😭💥",
    ],

    "shared-interests": [
        "{emoji} 🔗 MATCH DROP — Shared Interests!\n\n"
        "Mutual loves:\n{interests}\n\n"
        "{dept1} × {dept2}\n"
        "{campus1} × {campus2}\n\n"
        "Same vibe, different souls ✨💗",

        "{emoji} 🔗 MATCH DROP — Connection over interests 🪩\n\n"
        "Both love:\n{interests}\n\n"
        "{year1} × {year2}\n\n"
        "Friendship → love pipeline 😭🔥",
    ],
}


def format_interests(interests):
    if not interests:
        return "No shared interests."
    return "\n".join([f"• {i}" for i in interests])


def vibe_line(vibe_score):
    # vibe_score is already 0–100
    if vibe_score >= 90:
        return "Soulmate alert 💍😭🔥"
    elif vibe_score >= 70:
        return "Strong vibe, might just work ✨💗"
    else:
        return "Chaotic energy but fun 😳💥"


def _label_with_emoji(kind: str, value: str) -> str:
    """
    Map raw values to emoji+text labels from onboarding dictionaries.
    kind: 'dept' | 'year' | 'campus'
    """
    if not value:
        return ""
    if kind == "dept":
        return DEPT_LABELS.get(value, value)
    if kind == "year":
        return YEAR_LABELS.get(value, value)
    if kind == "campus":
        return CAMPUS_LABELS.get(value, value)
    return value


def build_match_drop_text(item):
    # parse interests JSON
    try:
        interests_list = json.loads(item.get("interests") or "[]")
    except Exception:
        interests_list = []

    interests = format_interests(interests_list)

    # vibe_score is stored as 0–100 in your system; keep as int
    try:
        vibe_score = int(float(item.get("vibe_score", 0)))
    except Exception:
        vibe_score = 0

    special_type = item.get("special_type")

    # Pre-map labels to emoji+text
    dept1 = _label_with_emoji("dept", item.get("department1", ""))
    dept2 = _label_with_emoji("dept", item.get("department2", ""))

    year1 = _label_with_emoji("year", item.get("year1", ""))
    year2 = _label_with_emoji("year", item.get("year2", ""))

    campus1 = _label_with_emoji("campus", item.get("campus1", ""))
    campus2 = _label_with_emoji("campus", item.get("campus2", ""))

    # pick template
    if special_type and special_type in TEMPLATES:
        template = random.choice(TEMPLATES[special_type])
        emoji = SPECIAL_EMOJIS.get(special_type, "✨")
        text = template.format(
            emoji=emoji,
            dept1=dept1,
            dept2=dept2,
            year1=year1,
            year2=year2,
            campus1=campus1,
            campus2=campus2,
            vibe_score=vibe_score,
            interests=interests,
        )
    else:
        # fallback: pick any template from any category
        template = random.choice(random.choice(list(TEMPLATES.values())))
        text = template.format(
            emoji="✨",
            dept1=dept1,
            dept2=dept2,
            year1=year1,
            year2=year2,
            campus1=campus1,
            campus2=campus2,
            vibe_score=vibe_score,
            interests=interests,
        )

    # add contextual hype
    return f"{text}\n\n{vibe_line(vibe_score)}\n\n— @AAUPulseBot 💫"
