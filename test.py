# # test.py
# import asyncio
# import logging
# import aiosqlite

# logging.basicConfig(level=logging.INFO)

# DB_PATH = "crushconnect.db"              # 👈 replace with the actual path to your SQLite file
# MY_USER_ID = 1131741322             # 👈 replace with your own user_id

# async def seed_likes(user_id: int, count: int = 999):
#     async with aiosqlite.connect(DB_PATH) as db:
#         likes = [(10_000_000 + i, user_id) for i in range(count)]  # fake liker IDs
#         await db.executemany(
    
#             "INSERT OR IGNORE INTO likes (liker_id, liked_id) VALUES (?, ?)",
#             likes
#         )
#         await db.commit()
#         logging.info(f"Inserted {count} fake likes for user {user_id}")

# async def main():
#     logging.info(f"Seeding 999 likes for user {MY_USER_ID}...")
#     await seed_likes(MY_USER_ID, 999)
#     logging.info("Done seeding likes!")

# if __name__ == "__main__":
#     asyncio.run(main())



#the above is for getting likes


# import aiosqlite
# import asyncio

# DB_PATH = "crushconnect.db"  # <-- change this to your DB file

# async def upgrade_transactions_table():
#     async with aiosqlite.connect(DB_PATH) as db:
#         async with db.execute("PRAGMA foreign_keys = ON;"):
#             pass  # ensure foreign keys are enforced

#         # 1️⃣ Rename old table
#         await db.execute("ALTER TABLE transactions RENAME TO transactions_old;")

#         # 2️⃣ Create new table with updated CHECK constraint
#         await db.execute("""
#             CREATE TABLE transactions (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER,
#                 amount INTEGER CHECK(amount != 0),
#                 type TEXT CHECK(type IN (
#                     'daily_login',
#                     'referral',
#                     'confession',
#                     'match',
#                     'purchase',
#                     'system',
#                     'bonus',
#                     'reward',
#                     'refund'
#                 )),
#                 description TEXT,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
#             );
#         """)

#         # 3️⃣ Copy data from old table
#         await db.execute("""
#             INSERT INTO transactions (id, user_id, amount, type, description, created_at)
#             SELECT id, user_id, amount, type, description, created_at
#             FROM transactions_old;
#         """)

#         # 4️⃣ Drop old table
#         await db.execute("DROP TABLE transactions_old;")

#         await db.commit()
#         print("Transactions table upgraded successfully!")

# asyncio.run(upgrade_transactions_table())



#the above is to check ulter the table
# -*- coding: utf-8 -*-
import asyncio

async def debug_matches(db, user_id: int):
    user = await db.get_user(user_id)
    if not user:
        print(f"No user found for ID {user_id}")
        return

    print(f"Debugging matches for {user['name']} | Gender: {user['gender']} | Seeking: {user['seeking_gender']}\n")

    # Fetch all potential candidates
    async with db._db.execute("SELECT id, name, gender, seeking_gender, is_active, is_banned FROM users WHERE id != ?", (user_id,)) as cur:
        rows = await cur.fetchall()
    
    viewer_gender = user['gender']
    viewer_seeking = user['seeking_gender']

    for r in rows:
        candidate_id = r['id']
        candidate_name = r['name']
        candidate_gender = r['gender']
        candidate_seeking = r['seeking_gender']
        candidate_active = r['is_active']
        candidate_banned = r['is_banned']

        # Step checks
        excluded = []

        if not candidate_active or candidate_banned:
            excluded.append("inactive/banned")

        if candidate_id == user_id:
            excluded.append("self")

        if user['seeking_gender'] != 'Any' and candidate_gender != user['seeking_gender']:
            excluded.append("gender mismatch")

        if not (candidate_seeking == 'Any' or candidate_seeking == viewer_gender):
            excluded.append("candidate not seeking viewer")

        if excluded:
            print(f"{candidate_name} excluded: {', '.join(excluded)}")
        else:
            print(f"{candidate_name} passes all filters")

async def main():
    from database import Database  # replace with actual db import
    db = Database()
    await db.connect()  # make sure your db connection is open
    await debug_matches(db, user_id=1131741322)  # replace 1 with the viewer's ID

asyncio.run(main())
