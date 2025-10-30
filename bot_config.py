import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@AAUCrushConnect')
ADMIN_GROUP_ID = os.getenv('ADMIN_GROUP_ID')
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
    "🏥 Health Sciences": "Health Sciences",
    "📈 FBE": "FBE",
    "🔬 Natural Sciences": "Natural Sciences",
    "🧠 Social Sciences": "Social Sciences",
    "📚 Other": "Other",
}


YEARS = {
    "🥇 1st Year": "1st Year",
    "🥈 2nd Year": "2nd Year",
    "🥉 3rd Year": "3rd Year",
    "🏅 4th Year": "4th Year",
    "🎓 5th Year+": "5th Year+",
}

GENDERS = ["👦 Male", "👩 Female", "⚧ Other"]

COIN_REWARDS = {
    'daily_login': 10,
    'referral': 50,
    'confession': 5,
    'profile_complete': 20,
    'first_match': 30
}

COIN_COSTS = {
    'reveal_crush': 30,
    'extra_likes': 20,
    'premium_vibe': 50
}

VIBE_QUESTIONS = [
    {
        'q': '☕️ Morning bunna before class or 🥤 Soft drink with friends after lecture?',
        'options': ['☕️ Bunna', '🥤 Soft drink'],
        'trait': 'social'
    },
    {
        'q': '📚 Serious library grind or 🛋️ Group study that turns into gossip?',
        'options': ['📚 Library grind', '🛋️ Group study'],
        'trait': 'studious'
    },
    {
        'q': '🌙 All‑night exam prep or 🎬 Movie marathon with friends?',
        'options': ['🌙 Exam prep', '🎬 Movie marathon'],
        'trait': 'lifestyle'
    },
    {
        'q': '🎉 Campus event hype or 🏠 Chill at home with Netflix?',
        'options': ['🎉 Campus event', '🏠 Netflix'],
        'trait': 'extrovert'
    },
    {
        'q': '🍲 Cafeteria shiro & injera or 🍕 Shawarma/Pizza off‑campus?',
        'options': ['🍲 Shiro & injera', '🍕 Shawarma/Pizza'],
        'trait': 'foodie'
    },
    {
        'q': '⚽️ Football match at the stadium or 🎮 FIFA in the dorms?',
        'options': ['⚽️ Stadium football', '🎮 Dorm FIFA'],
        'trait': 'hobbies'
    },
    {
        'q': '🚌 Taxi line adventures or 🚶‍♂️ Walking with friends between classes?',
        'options': ['🚌 Taxi line', '🚶‍♂️ Walking crew'],
        'trait': 'lifestyle2'
    }
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
DAILY_LIKE_LIMIT = 50


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
    "https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif",  # confetti
    "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",  # hearts
    "https://media.giphy.com/media/26FLdmIp6wJr91JCM/giphy.gif",  # fireworks
]

# Surprise GIFs for admirer (receiver)
NOTIFY_GIFS = [
    "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",  # popping hearts
    "https://media.giphy.com/media/3ohhwf7h2T8n7kZ9RK/giphy.gif",  # sparkle burst
    "https://media.giphy.com/media/l0ExkZ3Q9aZ9Q7w2Y/giphy.gif",  # confetti pop
]


