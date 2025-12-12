import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@AAUPulse')
ADMIN_GROUP_ID = os.getenv('ADMIN_GROUP_ID')
ADMIN_NEW_USER_GROUP_ID = os.getenv('ADMIN_NEW_USER_GROUP_ID')
SUPABASE_URL = os.getenv('VITE_SUPABASE_URL')
SUPABASE_KEY = os.getenv('VITE_SUPABASE_ANON_KEY')

AAU_CAMPUSES = {
    "🎓 Main 6kilo": "Main 6kilo",
    "🧠 5kilo": "5kilo",
    "🧪 4kilo": "4kilo",
    "🌆 Sefer Selam": "Sefer Selam",
    "💼 FBE": "FBE",
    "🎵 Yared": "Yared",
    "🏙️ Lideta": "Lideta",
}

AAU_DEPARTMENTS = {
    "🧑‍💻 IT": "IT",
    "🏗️ Engineering": "Engineering",
    "⚖️ Law": "Law",
    "💼 Business": "Business",
    "📈 Health Sciences": "Health Sciences",
    "🔬 Natural Sciences": "Natural Sciences",
    "🧠 Social Sciences": "Social Sciences",
    "📚 Other": "Other",
}

RATE_LIMIT_MESSAGES = [
    "⏳ Chill a sec!",
    "🐢 Slow‑mo mode!",
    "🚦 Red light!",
    "🔥 Too spicy, cool down!"
]


LIKE_CONFIRMATIONS = [
    "❤️ Locked in!",
    "🔥 Sent your vibe!",
    "💘 Shooting your shot...",
    "✨ They’ll feel this one!"
]


PASS_CONFIRMATIONS = [
    "💔 Skipped — on to the next!",
    "👋 Let’s keep moving...",
    "🚪 Passing this one by...",
    "😌 Not your vibe, next!"
]


MATCH_CELEBRATIONS = [
    "💖 <b>It’s a Match!</b>",
    "🎉 <b>You both swiped right!</b>",
    "🔥 <b>Sparks are flying!</b>",
]



YEARS = {
    "🥇 1st Year": "1st Year",
    "🥈 2nd Year": "2nd Year",
    "🥉 3rd Year": "3rd Year",
    "🏅 4th Year": "4th Year",
    "🎓 5th Year+": "5th Year+",
}

GENDERS = ["👦 Male", "👩 Female"]

COIN_REWARDS = {
    'daily_login': 10,
    'referral': 50,
    'confession': 5,
    'profile_complete': 20,
    'first_match': 10
}

COIN_COSTS = {
    'reveal_crush': 30,
    'extra_likes': 20,
    'premium_vibe': 50
}

VIBE_QUESTIONS = [
    {
    'q': '🎉 Friday night: AAU event with friends or 😌 staying home recharging?',
    'options': ['🎉 Event', '😌 Stay home'],
    'trait': 'social_energy'
},
    {
    'q': '📚 Study mode: Silent library grind or 🤝 group study with jokes?',
    'options': ['📚 Silent library', '🤝 Group study'],
    'trait': 'study_style'
},

    {
    'q': '⏰ Are you: Always on time or 🕐 “5 minutes is not late” type?',
    'options': ['⏰ On time', '🕐 Ethiopian time'],
    'trait': 'punctuality'
},

   {
    'q': '🍲 Lunch: Shiro/Injera at the cafe or 🍔 fast food outside campus?',
    'options': ['🍲 Shiro injera', '🍔 Fast food'],
    'trait': 'food_preference'
},

    {
    'q': '🧍 Between classes: Sitting alone with headphones or 👥 chatting around campus?',
    'options': ['🎧 Headphones solo', '👥 Chatting'],
    'trait': 'campus_behavior'
},

   {
    'q': '💘 Dating style: “Let’s take it slow” or ❤️ “Let’s vibe fast”?',
    'options': ['🐌 Slow & careful', '⏩ Fast & direct'],
    'trait': 'romantic_speed'
},


    {
    'q': '🌙 Are you more of a night owl or 🌅 early morning person?',
    'options': ['🌙 Night owl', '🌅 Morning person'],
    'trait': 'day_rhythm'
},
    
    {
    'q': '💸 Money vibe: Saver or 🤑 spender on treats?',
    'options': ['💸 Saver', '🤑 Spender'],
    'trait': 'money_habit'
},
    

]


TYPE_LABELS = {
    "daily_login": "Daily Login Bonus",
    "referral": "Referral Reward",
    "confession": "Confession Sent",
    "match": "New Match Reward",
    "purchase": "Shop Purchase / Reveal",
    "system": "System Adjustment"
}



# bot_config.py


# --- Interests (curated for maximum connection) ---
INTEREST_CATEGORIES = [
    {
        "category": "🎶 Music & Arts",
        "options": [
            "🎧 Afrobeat",
            "🎸 Rock/Indie",
            "🎤 Hip‑Hop/Rap",
            "🎻 Classical",
            "🎨 Painting/Drawing",
            "📸 Photography"
        ]
    },
    {
        "category": "⚽ Sports & Fitness",
        "options": [
            "⚽ Football",
            "🏀 Basketball",
            "🏋️ Gym/Fitness",
            "🏃 Running",
            "🧘 Yoga/Meditation",
            "🚴 Cycling"
        ]
    },
    {
        "category": "📚 Learning & Growth",
        "options": [
            "📖 Reading",
            "💻 Coding/Tech",
            "🌍 Languages",
            "🧪 Science",
            "🎓 Study Groups",
            "✍️ Writing/Poetry"
        ]
    },
    {
        "category": "🎬 Entertainment",
        "options": [
            "🎬 Movies",
            "📺 Series/Netflix",
            "🎮 Gaming",
            "🎤 Karaoke",
            "🎭 Theatre/Drama",
            "🎵 Concerts"
        ]
    },
    {
        "category": "🌍 Lifestyle & Social",
        "options": [
            "☕ Café Hopping",
            "🍕 Foodie Adventures",
            "✈️ Travel",
            "🎉 Campus Events",
            "🏠 Chill Nights",
            "🚌 Road Trips"
        ]
    },
    {
        "category": "💡 Passions & Causes",
        "options": [
            "🌱 Sustainability",
            "🤝 Volunteering",
            "📢 Activism",
            "🐶 Animal Care",
            "💼 Entrepreneurship",
            "📊 Startups/Innovation"
        ]
    }
]

# Flattened list if you need quick access
ALL_INTERESTS = [opt for cat in INTEREST_CATEGORIES for opt in cat["options"]]

MAX_BIO_LENGTH = 200
MAX_CONFESSION_LENGTH = 500
DAILY_LIKE_LIMIT = 30


# Breaker lines for match moments
MATCH_BREAKERS = [
    "─────────────── ✨ ───────────────",
    "🎆 Fireworks light up the chat!",
    "⚡ Sparks just flew!",
    "💘 Two vibes, one match.",
    "🌟 A new connection ignites.",
]

# Celebration GIFs for matchback (sender)
MATCHBACK_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExa2l6M3hpYXYyNm85OTkwajg2dXRxbmo0ejU4b3phdjhwMnNmaTlvdCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/epbQ7l3UQor7y/giphy.gif",  # confetti
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExaTBqZTZzd2ZkZTJ3NmFsbXZpejF1Y2JqM2UzNGtmNjhmOXBqN29tYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/c1R3XcUXVWAFy/giphy.gif",  # fireworks
]

# Surprise GIFs for admirer (receiver)
NOTIFY_GIFS = [
    "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",  # popping hearts
    "https://media.giphy.com/media/3ohhwf7h2T8n7kZ9RK/giphy.gif",  # sparkle burst
    "https://media.giphy.com/media/l0ExkZ3Q9aZ9Q7w2Y/giphy.gif",  # confetti pop
]


