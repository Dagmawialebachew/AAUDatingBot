import aiosqlite
import asyncio
import random
import json
import os
from datetime import datetime
from faker import Faker
import aiohttp

# --- Configuration ---
DB_PATH = "crushconnect.db"
NUM_USERS = 200
MAX_BIO_LENGTH = 200
PHOTO_DIR = "profile_photos"  # Folder to store downloaded photos

# Ethiopian names
ETHIOPIAN_FIRST_NAMES = [
    "Abebe", "Kebede", "Haile", "Meron", "Selam", "Mekdes", "Yonas", "Lily", "Tsegaye", "Saba",
    "Dawit", "Eleni", "Samuel", "Hirut", "Bereket", "Martha", "Fikre", "Sisay", "Selamawit", "Biruk"
]
ETHIOPIAN_LAST_NAMES = [
    "Tesfaye", "Bekele", "Gebre", "Alemu", "Tadesse", "Worku", "Girma", "Hailu", "Ewnetu", "Fikadu"
]

CAMPUSES = [
    "Main 6kilo", "5kilo", "4kilo", "Sefer Selam", "FBE", "Yared", "Lideta"
]
DEPARTMENTS = [
    "Engineering", "Law", "Business", "Health Sciences", "IT", "FBE", "Natural Sciences", "Social Sciences", "Other"
]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year+"]
GENDERS = ["Male", "Female", "Other"]

faker = Faker("en_US")
Faker.seed(42)

# Ensure photo directory exists
os.makedirs(PHOTO_DIR, exist_ok=True)

# --- Helper functions ---
def generate_username(name):
    return name.lower().replace(" ", "_") + str(random.randint(1, 999))

def generate_bio():
    bio = faker.sentence(nb_words=12)
    return bio[:MAX_BIO_LENGTH]

async def download_photo(idx: int) -> str:
    """Downloads a photo from thispersondoesnotexist.com and returns local file path."""
    url = "https://thispersondoesnotexist.com/image"
    filename = os.path.join(PHOTO_DIR, f"user_{idx}.jpg")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(filename, "wb") as f:
                    f.write(await resp.read())
    return filename  # We'll use this as the placeholder file_id

def generate_user(idx: int, photo_file_id: str):
    first_name = random.choice(ETHIOPIAN_FIRST_NAMES)
    last_name = random.choice(ETHIOPIAN_LAST_NAMES)
    name = f"{first_name} {last_name}"
    username = generate_username(name)
    bio = generate_bio()
    gender = random.choice(GENDERS)
    seeking_gender = random.choice([g for g in GENDERS if g != gender])
    campus = random.choice(CAMPUSES)
    department = random.choice(DEPARTMENTS)
    year = random.choice(YEARS)

    vibe_answers = {q['trait']: random.randint(0, 1) for q in [
        {'trait':'social'}, {'trait':'studious'}, {'trait':'lifestyle'},
        {'trait':'extrovert'}, {'trait':'foodie'}, {'trait':'hobbies'}, {'trait':'lifestyle2'}
    ]}

    return {
        'username': username,
        'name': name,
        'gender': gender,
        'seeking_gender': seeking_gender,
        'campus': campus,
        'department': department,
        'year': year,
        'bio': bio,
        'photo_file_id': photo_file_id,
        'coins': 120,
        'vibe_score': json.dumps(vibe_answers)
    }

async def insert_user(db, user_data):
    columns = ', '.join(user_data.keys())
    placeholders = ', '.join('?' for _ in user_data)
    sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
    await db.execute(sql, tuple(user_data.values()))

# --- Main Script ---
async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for i in range(1, NUM_USERS + 1):
            try:
                photo_file_id = await download_photo(i)
                user = generate_user(i, photo_file_id)
                await insert_user(db, user)
                print(f"Inserted user: {user['name']}")
            except Exception as e:
                print(f"Error inserting user {i}: {e}")
        await db.commit()
        print(f"{NUM_USERS} Ethiopian-style users inserted successfully with photos!")

if __name__ == "__main__":
    asyncio.run(main())
