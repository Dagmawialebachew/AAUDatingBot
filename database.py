import random
import aiosqlite
import logging
import json
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, date, timedelta

from utils import calculate_vibe_compatibility, recency_score

# Configure logging
logger = logging.getLogger(__name__)

# --- Helper Function ---
def _dict_from_row(row: aiosqlite.Row) -> Optional[Dict[str, Any]]:
    """Converts an aiosqlite.Row object to a dictionary."""
    if not row:
        return None
    return dict(row)

class Database:
    """
    An async-compatible SQLite database class for CrushConnect.
    This class handles all database operations, replacing the original Supabase implementation.
    """
    def __init__(self, db_path: str = "crushconnect.db"):
        self.db_path = db_path
        self._db = None

    async def connect(self):
        """Initializes the database connection and creates tables if they don't exist."""
        try:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row  # Access columns by name
            await self._initialize_db()
            logger.info("Database connection successful and tables initialized.")
        except Exception as e:
            logger.critical(f"FATAL: Could not connect to database at {self.db_path}: {e}")
            raise

    async def close(self):
        """Closes the database connection."""
        if self._db:
            await self._db.close()
            logger.info("Database connection closed.")



    async def _initialize_db(self):
        """Creates all necessary tables and indexes if they don't exist."""
        async with self._db.cursor() as cursor:
            # --- Users Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    name TEXT,
                    gender TEXT,
                    seeking_gender TEXT,
                    campus TEXT,
                    department TEXT,
                    year TEXT,
                    bio TEXT,
                    photo_file_id TEXT,
                    coins INTEGER DEFAULT 120,
                    vibe_score TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # --- Likes Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    liker_id INTEGER,
                    liked_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(liker_id, liked_id),
                    FOREIGN KEY(liker_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(liked_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Matches Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id INTEGER,
                    user2_id INTEGER,
                    revealed BOOLEAN DEFAULT FALSE,
                    chat_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user1_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(user2_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Chats Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    sender_id INTEGER,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Confessions Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS confessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    campus TEXT,
                    department TEXT,
                    text TEXT,
                    status TEXT DEFAULT 'pending', -- pending, approved, rejected
                    channel_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Referrals Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    coins_awarded INTEGER DEFAULT 50,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(referrer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(referred_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Transactions Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER CHECK(amount != 0),
                    type TEXT CHECK(type IN  (
            'daily_login',
            'referral',
            'confession',
            'match',
            'purchase',
            'system'
        )
        ),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Daily Logins Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    login_date DATE,
                    UNIQUE(user_id, login_date),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # --- Leaderboard Cache ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    week_start DATE,
                    likes_received INTEGER DEFAULT 0,
                    matches_count INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, week_start)
                )
            """)

            # --- Passes Table ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS passes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    target_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, target_id)
                )
            """)

            # --- Interests Catalog (normalized) ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )
            """)
            
            await cursor.execute("""
                                 CREATE TABLE IF NOT EXISTS user_activity (
    user_id     INTEGER PRIMARY KEY,
    last_seen   TIMESTAMP NOT NULL
);
             """)

            # --- User Interests (many-to-many) ---
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    interest_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(interest_id) REFERENCES interest_catalog(id) ON DELETE CASCADE,
                    UNIQUE(user_id, interest_id)
                )
            """)

            # --- Safe add last_active column ---
            await cursor.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in await cursor.fetchall()]
            if "last_active" not in cols:
                await cursor.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            # --- Indexes ---
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_likes_liker_id ON likes (liker_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_likes_liked_id ON likes (liked_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_users ON matches (user1_id, user2_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_match_id ON chats (match_id)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_confessions_status ON confessions (status)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_passes_user_id_created ON passes (user_id, created_at)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id_created ON transactions (user_id, created_at)")
            await cursor.execute("CREATE INDEX IF NOT EXISTS idx_interests_user_id ON interests(user_id)")

        await self._db.commit()


    async def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            async with self._db.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = await cursor.fetchone()
                return _dict_from_row(row)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_user(self, user_data: Dict) -> bool:
        try:
            # Serialize vibe_score dict to a JSON string
            if 'vibe_score' in user_data and isinstance(user_data['vibe_score'], dict):
                user_data['vibe_score'] = json.dumps(user_data['vibe_score'])
                
            columns = ', '.join(user_data.keys())
            placeholders = ', '.join('?' for _ in user_data)
            sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
            
            async with self._db.execute(sql, tuple(user_data.values())):
                await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await self._db.rollback()
            return False

    async def update_user(self, user_id: int, updates: Dict) -> bool:
        if not updates:
            return True
        try:
            if 'vibe_score' in updates and isinstance(updates['vibe_score'], dict):
                updates['vibe_score'] = json.dumps(updates['vibe_score'])

            set_clause = ", ".join([f"{key} = ?" for key in updates])
            values = list(updates.values())
            values.append(user_id)
            
            sql = f"UPDATE users SET {set_clause} WHERE id = ?"
            
            async with self._db.execute(sql, tuple(values)):
                await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            await self._db.rollback()
            return False

    async def update_last_active(self, user_id: int):
        try:
            await self._db.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            await self._db.commit()
        except Exception as e:
            logger.error(f"Error updating last_active for {user_id}: {e}")

    async def get_matches_for_user(self, user_id: int, filters: Dict = None) -> List[Dict]:
        """
        Fetch and rank potential matches for a user with:
        - Exclusion of self, inactive, banned
        - Exclusion of already liked
        - Exclusion of candidates passed twice in the last 3 days
        - Soft penalty for candidates passed once (ranked lower, not hidden)
        - Optional filters (gender, campus, department, year)
        - Ranking by vibe compatibility, shared interests, recency, mutual likes
        - Shuffle top results for freshness
        """
        try:
            user = await self.get_user(user_id)
            if not user:
                return []

            params = [user_id, user_id, user_id, user_id]

            sql = """
            WITH pass_counts AS (
                SELECT target_id, COUNT(*) AS pass_count
                FROM passes
                WHERE user_id = ?
                AND created_at > DATE('now', '-3 days')
                GROUP BY target_id
            ),
            mutual_likes AS (
                SELECT liker_id
                FROM likes
                WHERE liked_id = ?
            )
            SELECT u.*,
                COALESCE(pc.pass_count, 0) AS pass_count,
                CASE WHEN u.id IN (SELECT liker_id FROM mutual_likes) THEN 1 ELSE 0 END AS liked_you
            FROM users u
            LEFT JOIN pass_counts pc ON u.id = pc.target_id
            WHERE u.id != ?
            AND u.is_active = TRUE
            AND u.is_banned = FALSE
            AND u.id NOT IN (SELECT liked_id FROM likes WHERE liker_id = ?)
            AND (pc.pass_count IS NULL OR pc.pass_count < 2)
            """

            # --- Dynamic filters ---
            if user['seeking_gender'].lower() != 'any':
                sql += " AND LOWER(u.gender) = ?"
                params.append(user['seeking_gender'].lower())

            # Candidate must be seeking viewer's gender (case-insensitive)
            sql += " AND (LOWER(u.seeking_gender) = 'any' OR LOWER(u.seeking_gender) = ?)"
            params.append(user['gender'].lower())



            if filters:
                if filters.get('campus'):
                    sql += " AND u.campus = ?"
                    params.append(filters['campus'])
                if filters.get('department'):
                    sql += " AND u.department = ?"
                    params.append(filters['department'])
                if filters.get('year'):
                    sql += " AND u.year = ?"
                    params.append(filters['year'])

            sql += " ORDER BY liked_you DESC, u.last_active DESC LIMIT 100"

            async with self._db.execute(sql, tuple(params)) as cursor:
                rows = await cursor.fetchall()
                candidates = [_dict_from_row(row) for row in rows]

            # --- Ranking ---
            viewer_vibe = json.loads(user.get('vibe_score', '{}') or '{}')
            viewer_interests = await self.get_user_interests(user_id)

            # Preload candidate interests
            candidate_interests_map = {
                c['id']: await self.get_user_interests(c['id'])
                for c in candidates
            }

            def rank(c):
                vibe = calculate_vibe_compatibility(
                    viewer_vibe, json.loads(c.get('vibe_score', '{}') or '{}')
                )
                overlap = len(set(viewer_interests) & set(candidate_interests_map[c['id']]))
                recency = recency_score(c.get('last_active'))
                liked_you = c.get('liked_you', 0)
                pass_count = c.get('pass_count', 0)

                # Weighted score
                score = (0.45 * vibe +
                        0.25 * overlap +
                        0.2 * recency +
                        0.1 * liked_you)

                # Soft penalty if passed once
                if pass_count == 1:
                    score *= 0.5

                return score

            candidates.sort(key=rank, reverse=True)

            # Take top 50, shuffle lightly for freshness
            top = candidates[:50]
            random.shuffle(top)
            return top

        except Exception as e:
            logger.error(f"Error getting matches for user {user_id}: {e}")
            return []

    
    async def count_active_users(self, minutes: int = 10) -> int:
        query = """
            SELECT COUNT(DISTINCT user_id) as cnt
            FROM user_activity
            WHERE last_seen >= datetime('now', ?)
        """
        async with self._db.execute(query, (f'-{minutes} minutes',)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


# Count new likes (admirers) for a given user
    async def count_new_likes(self, user_id: int) -> int:
        query = """
            SELECT COUNT(*) as cnt
            FROM likes
            WHERE liked_id = ?
        """
        async with self._db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    
# --- Interests Helpers ---

    async def get_user_interests(self, user_id: int) -> List[str]:
        query = """
            SELECT ic.name
            FROM interests i
            JOIN interest_catalog ic ON i.interest_id = ic.id
            WHERE i.user_id = ?
        """
        async with self._db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
        
    async def get_other_user_ids(self, user_id: int) -> List[int]:
        query = "SELECT id FROM users WHERE id != ?"
        async with self._db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def set_user_interests(self, user_id: int, interests: List[str]):
        """
        Replace a user's interests with the provided list.
        Ensures each interest exists in the catalog.
        """
        try:
            # Clear old interests
            await self._db.execute("DELETE FROM interests WHERE user_id = ?", (user_id,))

            for interest in interests:
                interest = interest.strip()
                if not interest:
                    continue

                # Ensure interest exists in catalog
                async with self._db.execute(
                    "SELECT id FROM interest_catalog WHERE name = ?", (interest,)
                ) as cursor:
                    row = await cursor.fetchone()

                if row:
                    interest_id = row["id"]
                else:
                    async with self._db.execute(
                        "INSERT INTO interest_catalog (name) VALUES (?)", (interest,)
                    ) as cur2:
                        interest_id = cur2.lastrowid

                # Insert into user interests
                await self._db.execute(
                    "INSERT OR IGNORE INTO interests (user_id, interest_id) VALUES (?, ?)",
                    (user_id, interest_id)
                )

            await self._db.commit()
        except Exception as e:
            logger.error(f"Error setting interests for user {user_id}: {e}")
            await self._db.rollback()


    

    async def add_like(self, liker_id: int, liked_id: int) -> dict:
        try:
            # Insert like (ignore if already exists)
            await self._db.execute(
                "INSERT OR IGNORE INTO likes (liker_id, liked_id) VALUES (?, ?)",
                (liker_id, liked_id)
            )
            await self._db.commit()

            # Check reverse like (did the other person already like you?)
            async with self._db.execute(
                "SELECT id FROM likes WHERE liker_id = ? AND liked_id = ?",
                (liked_id, liker_id)
            ) as cursor:
                reverse_like = await cursor.fetchone()

            if reverse_like:
                # Create a match
                user1_id = min(liker_id, liked_id)
                user2_id = max(liker_id, liked_id)
                async with self._db.execute(
                    "INSERT INTO matches (user1_id, user2_id) VALUES (?, ?)",
                    (user1_id, user2_id)
                ) as cursor:
                    match_id = cursor.lastrowid

                # Reward both users
                await self.add_coins(liker_id, 10, 'match', 'You got a new match!')
                await self.add_coins(liked_id, 10, 'match', 'You got a new match!')

                await self._db.commit()
                await self.update_leaderboard_cache()
                return {"status": "match", "match_id": match_id}

            # If no reverse like, just a one‑sided like
            await self.update_leaderboard_cache()
            
            return {"status": "liked"}

        except Exception as e:
            logger.error(f"Error adding like from {liker_id} to {liked_id}: {e}")
            await self._db.rollback()
            return {"status": "error"}

    
   
        
    async def get_user_stats(self, user_id: int) -> Dict:
        stats = {'likes_sent': 0, 'likes_received': 0, 'matches': 0, 'referrals': 0}
        try:
            async with self._db.cursor() as cursor:
                await cursor.execute("SELECT COUNT(*) FROM likes WHERE liker_id = ?", (user_id,))
                stats['likes_sent'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(*) FROM likes WHERE liked_id = ?", (user_id,))
                stats['likes_received'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(*) FROM matches WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
                stats['matches'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
                stats['referrals'] = (await cursor.fetchone())[0]

            return stats
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return stats
        
        
    
    async def get_referrals(self, user_id: int, offset: int = 0, limit: int = 10) -> List[Dict]:
        try:
            sql = """
                SELECT referred_id, created_at
                FROM referrals
                WHERE referrer_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            async with self._db.execute(sql, (user_id, limit, offset)) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching referrals for {user_id}: {e}")
            return []




    async def get_user_rank(self, user_id: int) -> int | None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start.isoformat()

        sql = """
            SELECT user_id, RANK() OVER (ORDER BY likes_received DESC, u.name ASC) as rnk
            FROM leaderboard_cache lc
            JOIN users u ON lc.user_id = u.id
            WHERE week_start = ?
        """
        async with self._db.execute(sql, (week_start_str,)) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            if row["user_id"] == user_id:
                return row["rnk"]
        return None


    async def remove_like(self, liker_id: int, liked_id: int) -> bool:
        try:
            async with self._db.execute(
                "DELETE FROM likes WHERE liker_id = ? AND liked_id = ?",
                (liker_id, liked_id)
            ) as cursor:
                await self._db.commit()
                await self.update_leaderboard_cache()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing like {liker_id}->{liked_id}: {e}")
            await self._db.rollback()
            return False

            
            
    # inside database.py

    async def get_trending_interests(self, limit: int = 10):
        """
        Return the top trending interests by number of users.
        """
        query = """
            SELECT ic.name, COUNT(i.user_id) as count
            FROM interests i
            JOIN interest_catalog ic ON i.interest_id = ic.id
            GROUP BY ic.name
            ORDER BY count DESC
            LIMIT ?
        """
        async with self._db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return rows



    async def get_match_by_id(self, match_id: int) -> Optional[Dict]:
        async with self._db.execute(
            "SELECT id as match_id, user1_id, user2_id, chat_active, revealed FROM matches WHERE id = ?",
            (match_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "match_id": row["match_id"],
                "user1_id": row["user1_id"],
                "user2_id": row["user2_id"],
                "chat_active": bool(row["chat_active"]),
                "revealed": bool(row["revealed"]),
            }
        return None


    async def unmatch(self, match_id: int, user_id: int) -> Optional[Dict]:
        """
        Soft unmatch:
        - Sets chat_active = FALSE
        - Resets revealed = FALSE
        - Deletes likes between users so they can like again
        - Returns updated match row for verification
        """
        try:
            # Fetch the match first
            async with self._db.execute(
                "SELECT id as match_id, user1_id, user2_id, chat_active, revealed "
                "FROM matches WHERE id = ?",
                (match_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                logger.error(f"No match found with id {match_id} for user {user_id}")
                return None

            logger.info(f"Before unmatch - match row: {row}")

            user1_id, user2_id = row['user1_id'], row['user2_id']
            if user_id not in (user1_id, user2_id):
                logger.error(f"User {user_id} is not part of match {match_id}")
                return None

            other_user_id = user2_id if user1_id == user_id else user1_id

            # Soft unmatch + reset reveal
            await self._db.execute(
                "UPDATE matches SET chat_active = FALSE, revealed = FALSE WHERE id = ?",
                (match_id,)
            )

            # Delete likes in both directions
            await self._db.execute(
                "DELETE FROM likes WHERE (liker_id = ? AND liked_id = ?) OR (liker_id = ? AND liked_id = ?)",
                (user_id, other_user_id, other_user_id, user_id)
            )

            await self._db.commit()
            logger.info(f"Unmatched successfully for match_id={match_id}, user_id={user_id}")

            # Fetch updated match row
            async with self._db.execute(
                "SELECT id as match_id, user1_id, user2_id, chat_active, revealed "
                "FROM matches WHERE id = ?",
                (match_id,)
            ) as cursor:
                updated_row = await cursor.fetchone()

            logger.info(f"After unmatch - updated match row: {updated_row}")

            return {
                "match_id": updated_row["match_id"],
                "user1_id": updated_row["user1_id"],
                "user2_id": updated_row["user2_id"],
                "chat_active": bool(updated_row["chat_active"]),
                "revealed": bool(updated_row["revealed"]),
            }

        except Exception as e:
            logger.error(f"Error unmatching {match_id} by {user_id}: {e}")
            await self._db.rollback()
            return None


    async def get_who_liked_me(self, user_id: int) -> list[dict]:
        """
        Returns unique users who liked `user_id` but haven't got an active match.
        """
        try:
            sql = """
                SELECT DISTINCT u.id, u.name, u.username, u.photo_file_id
                FROM likes l
                JOIN users u ON u.id = l.liker_id
                WHERE l.liked_id = ?
                AND NOT EXISTS (
                    SELECT 1 FROM matches m
                    WHERE ((m.user1_id = l.liker_id AND m.user2_id = l.liked_id)
                        OR (m.user1_id = l.liked_id AND m.user2_id = l.liker_id))
                        AND m.chat_active = TRUE
                )
            """
            async with self._db.execute(sql, (user_id,)) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting who liked me for {user_id}: {e}")
            return []


    async def get_my_likes(self, user_id: int) -> list[dict]:
        """
        Returns unique users that `user_id` liked but who haven't got an active match.
        """
        try:
            sql = """
                SELECT DISTINCT u.id, u.name, u.username, u.photo_file_id
                FROM likes l
                JOIN users u ON u.id = l.liked_id
                WHERE l.liker_id = ?
                AND NOT EXISTS (
                    SELECT 1 FROM matches m
                    WHERE ((m.user1_id = l.liker_id AND m.user2_id = l.liked_id)
                        OR (m.user1_id = l.liked_id AND m.user2_id = l.liker_id))
                        AND m.chat_active = TRUE
                )
            """
            async with self._db.execute(sql, (user_id,)) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting my likes for {user_id}: {e}")
            return []

    async def get_user_matches(self, user_id: int) -> List[Dict]:
        try:
            sql = """
                SELECT DISTINCT m.id as match_id, m.revealed,
                    CASE WHEN m.user1_id = ? THEN m.user2_id ELSE m.user1_id END as other_user_id
                FROM matches m
                WHERE (m.user1_id = ? OR m.user2_id = ?)
                AND m.chat_active = TRUE
            """
            async with self._db.execute(sql, (user_id, user_id, user_id)) as cursor:
                matches_data = await cursor.fetchall()

            result = []
            seen = set()
            for match_row in matches_data:
                other_id = match_row['other_user_id']
                if other_id in seen:
                    continue
                seen.add(other_id)
                other_user = await self.get_user(other_id)
                if other_user:
                    result.append({
                        'match_id': match_row['match_id'],
                        'user': other_user,
                        'revealed': bool(match_row['revealed'])
                    })
            return result
        except Exception as e:
            logger.error(f"Error getting user matches for {user_id}: {e}")
            return []


    async def get_match_between(self, user1_id: int, user2_id: int) -> Optional[Dict]:
        """
        Fetch a single match row between two users, including reveal state.
        """
        try:
            sql = """
                SELECT m.id as match_id, m.revealed, m.user1_id, m.user2_id
                FROM matches m
                WHERE (m.user1_id = ? AND m.user2_id = ?)
                OR (m.user1_id = ? AND m.user2_id = ?)
                LIMIT 1
            """
            async with self._db.execute(sql, (user1_id, user2_id, user2_id, user1_id)) as cursor:
                row = await cursor.fetchone()
            if row:
                return {
                    "match_id": row["match_id"],
                    "revealed": bool(row["revealed"]),
                    "user1_id": row["user1_id"],
                    "user2_id": row["user2_id"],
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching match between {user1_id} and {user2_id}: {e}")
            return None


    async def get_active_match_between(self, user1_id: int, user2_id: int) -> Optional[Dict]:
        sql = """
            SELECT id as match_id, user1_id, user2_id, chat_active, revealed
            FROM matches
            WHERE chat_active = 1
            AND ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
            LIMIT 1
        """
        async with self._db.execute(sql, (user1_id, user2_id, user2_id, user1_id)) as cursor:
            row = await cursor.fetchone()
        if row:
            return {
                "match_id": row["match_id"],
                "user1_id": row["user1_id"],
                "user2_id": row["user2_id"],
                "chat_active": bool(row["chat_active"]),
                "revealed": bool(row["revealed"]),
            }
        return None


    async def save_chat_message(self, match_id: int, sender_id: int, message: str) -> bool:
        try:
            sql = "INSERT INTO chats (match_id, sender_id, message) VALUES (?, ?, ?)"
            async with self._db.execute(sql, (match_id, sender_id, message)):
                await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving chat message for match {match_id}: {e}")
            await self._db.rollback()
            return False

    async def get_chat_history(self, match_id: int, limit: int = 20) -> List[Dict]:
        try:
            sql = "SELECT * FROM chats WHERE match_id = ? ORDER BY created_at DESC LIMIT ?"
            async with self._db.execute(sql, (match_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return list(reversed([_dict_from_row(r) for r in rows]))
        except Exception as e:
            logger.error(f"Error getting chat history for match {match_id}: {e}")
            return []
        
        

    async def add_pass(self, user_id: int, target_id: int) -> Dict[str, Any]:
        """
        Records a 'pass' (ignore/swipe-left) action.
        Ensures the same pass isn't duplicated.
        """
        try:
            await self._db.execute(
                "INSERT OR IGNORE INTO passes (user_id, target_id) VALUES (?, ?)",
                (user_id, target_id)
            )
            await self._db.commit()
            return {"status": "passed"}
        except Exception as e:
            logger.error(f"Error adding pass for user {user_id} -> {target_id}: {e}")
            return {"status": "error", "error": str(e)}


    async def create_confession(self, sender_id: int, confession_data: Dict) -> Optional[int]:
        try:
            sql = "INSERT INTO confessions (sender_id, campus, department, text) VALUES (?, ?, ?, ?)"
            params = (sender_id, confession_data['campus'], confession_data['department'], confession_data['text'])
            
            async with self._db.execute(sql, params) as cursor:
                confession_id = cursor.lastrowid
            
            await self.add_coins(sender_id, 5, 'confession', 'Posted a confession')
            await self._db.commit()
            return confession_id
        except Exception as e:
            logger.error(f"Error creating confession for user {sender_id}: {e}")
            await self._db.rollback()
            return None

    async def get_confession(self, confession_id: int) -> Optional[Dict]:
        """Fetches a single confession by its ID."""
        try:
            async with self._db.cursor() as cursor:
                await cursor.execute("SELECT * FROM confessions WHERE id = ?", (confession_id,))
                row = await cursor.fetchone()
                return _dict_from_row(row)
        except Exception as e:
            logger.error(f"Error getting confession {confession_id}: {e}")
            return None
            
    async def get_pending_confessions(self) -> List[Dict]:
        try:
            sql = "SELECT * FROM confessions WHERE status = 'pending' ORDER BY created_at ASC"
            async with self._db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                return [_dict_from_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting pending confessions: {e}")
            return []

    async def update_confession_status(self, confession_id: int, status: str, message_id: Optional[int] = None) -> bool:
        try:
            sql = "UPDATE confessions SET status = ?, channel_message_id = ? WHERE id = ?"
            async with self._db.execute(sql, (status, message_id, confession_id)):
                await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating confession {confession_id}: {e}")
            await self._db.rollback()
            return False

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        try:
            sql = "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)"
            async with self._db.execute(sql, (referrer_id, referred_id)):
                pass
            await self.add_coins(referrer_id, 50, 'referral', f'Referred user {referred_id}')
            await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding referral from {referrer_id} to {referred_id}: {e}")
            await self._db.rollback()
            return False

    async def add_coins(self, user_id: int, amount: int, tx_type: str, description: str) -> bool:
        try:
            await self._db.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, user_id))
            await self._db.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, amount, tx_type, description)
            )
            await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding {amount} coins to user {user_id}: {e}")
            await self._db.rollback()
            return False



    async def spend_coins(self, user_id: int, amount: int, tx_type: str, description: str) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user or user['coins'] < amount:
                return False

            # Normalize tx_type to allowed values
            if tx_type not in {"daily_login","referral","confession","match","purchase","system"}:
                tx_type = "purchase"

            await self._db.execute(
                "UPDATE users SET coins = coins - ? WHERE id = ?",
                (amount, user_id)
            )
            await self._db.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
                (user_id, -amount, tx_type, description)
            )
            await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error spending {amount} coins for user {user_id}: {e}")
            await self._db.rollback()
            return False

    
    async def get_transactions(self, user_id: int, offset: int = 0, limit: int = 10) -> List[Dict]:
        try:
            sql = """
                SELECT amount, type, description, created_at
                FROM transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            async with self._db.execute(sql, (user_id, limit, offset)) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching transactions for {user_id}: {e}")
            return []


    async def record_daily_login(self, user_id: int) -> bool:
        try:
            today = date.today().isoformat()
            # INSERT OR IGNORE will do nothing if the unique constraint (user_id, login_date) is violated
            async with self._db.execute("INSERT OR IGNORE INTO daily_logins (user_id, login_date) VALUES (?, ?)", (user_id, today)) as cursor:
                if cursor.rowcount > 0: # If a row was inserted
                    await self.add_coins(user_id, 10, 'daily_login', 'Daily login bonus')
                    await self._db.commit()
                    return True
            return False # No new row was inserted, user already logged in today
        except Exception as e:
            logger.error(f"Error recording daily login for user {user_id}: {e}")
            await self._db.rollback()
            return False
        
    
    from datetime import date, timedelta

    async def get_daily_streak(self, user_id: int) -> int:
        try:
            today = date.today()
            async with self._db.execute(
                "SELECT login_date FROM daily_logins WHERE user_id = ? ORDER BY login_date DESC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                dates = [date.fromisoformat(row[0]) for row in rows]

                streak = 0
                for i, login_date in enumerate(dates):
                    expected = today - timedelta(days=i)
                    if login_date == expected:
                        streak += 1
                    else:
                        break

                return streak
        except Exception as e:
            logger.error(f"Error calculating streak for user {user_id}: {e}")
            return 0



    

    async def update_leaderboard_cache(self) -> bool:
        """
        Rebuilds the leaderboard cache for the current week.
        Ensures all active users are included, even if they have 0 likes.
        """
        try:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_start_str = week_start.isoformat()

            async with self._db.cursor() as cursor:
                # Clear old cache for this week
                await cursor.execute(
                    "DELETE FROM leaderboard_cache WHERE week_start = ?",
                    (week_start_str,)
                )

                # Insert all users with their like counts (0 if none)
                sql = """
                    INSERT INTO leaderboard_cache (user_id, week_start, likes_received)
                    SELECT u.id, ?, COALESCE(COUNT(l.id), 0) as likes_received
                    FROM users u
                    LEFT JOIN likes l
                        ON l.liked_id = u.id
                        AND date(l.created_at) >= ?
                    WHERE u.is_active = TRUE AND u.is_banned = FALSE
                    GROUP BY u.id
                """
                await cursor.execute(sql, (week_start_str, week_start_str))
                inserted = cursor.rowcount if cursor.rowcount is not None else 0
                logger.info(f"Leaderboard cache updated for {week_start_str}: {inserted} rows inserted")

            await self._db.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating leaderboard cache: {e}")
            await self._db.rollback()
            return False


    async def get_leaderboard(self, week_start: date = None) -> List[Dict]:
        """
        Returns top 10 users for the given week (including those with 0 likes).
        """
        try:
            if not week_start:
                today = date.today()
                week_start = today - timedelta(days=today.weekday())

            sql = """
                SELECT u.id, u.name, u.campus, lc.likes_received
                FROM leaderboard_cache lc
                JOIN users u ON lc.user_id = u.id
                WHERE lc.week_start = ?
                ORDER BY lc.likes_received DESC, u.name ASC
                LIMIT 10
            """
            async with self._db.execute(sql, (week_start.isoformat(),)) as cursor:
                rows = await cursor.fetchall()
                return [_dict_from_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting leaderboard for week {week_start}: {e}")
            return []


    async def get_user_rank(self, user_id: int) -> int | None:
        """
        Returns the 1-based rank of the user for the current week, or None if not found.
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start.isoformat()

        sql = """
            SELECT rank_alias.rank
            FROM (
                SELECT
                    user_id,
                    RANK() OVER (ORDER BY likes_received DESC, u.name ASC) as rank
                FROM leaderboard_cache lc
                JOIN users u ON lc.user_id = u.id
                WHERE week_start = ?
            ) rank_alias
            WHERE rank_alias.user_id = ?
        """
        try:
            async with self._db.execute(sql, (week_start_str, user_id)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error calculating rank for user {user_id}: {e}")
            return None

        
        
    async def get_global_stats(self) -> Dict:
        """Calculates and returns global statistics for the admin panel."""
        stats = {
            'total_users': 0,
            'active_users': 0,
            'total_matches': 0,
            'total_confessions': 0,
            'pending_confessions': 0
        }
        try:
            async with self._db.cursor() as cursor:
                await cursor.execute("SELECT COUNT(id) FROM users")
                stats['total_users'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(id) FROM users WHERE is_active = TRUE")
                stats['active_users'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(id) FROM matches")
                stats['total_matches'] = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(id) FROM confessions")
                stats['total_confessions'] = (await cursor.fetchone())[0]
                
                await cursor.execute("SELECT COUNT(id) FROM confessions WHERE status = 'pending'")
                stats['pending_confessions'] = (await cursor.fetchone())[0]
            
            return stats
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return stats
        
    
    async def get_active_user_ids(self, limit: Optional[int] = None) -> List[int]:
        """
        Retrieves IDs of all active, non-banned users, optionally limiting the count.
        Used for scheduled broadcast notifications.
        """
        try:
            async with self._db.cursor() as cursor:
                query = "SELECT id FROM users WHERE is_active = 1 AND is_banned = 0"
                if limit is not None:
                    query += f" LIMIT {limit}"
                
                await cursor.execute(query)
                rows = await cursor.fetchall()
                # Extract IDs from the Row objects
                return [row['id'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting active user IDs for notification: {e}")
            return []

    async def get_all_active_user_ids(self) -> List[int]:
        """Returns a list of IDs for all active, non-banned users."""
        try:
            sql = "SELECT id FROM users WHERE is_active = TRUE AND is_banned = FALSE"
            async with self._db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                return [row['id'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting active user IDs: {e}")
            return []
        
    
    async def reveal_match_identity(self, match_id: int, user_id: int) -> bool:
        """Sets the 'revealed' flag to True for a specific match, ensuring the user is one of the participants."""
        try:
            # We assume the 'matches' table has a composite key or a unique 'match_id'
            # and contains columns 'user1_id', 'user2_id', and 'revealed'.
            sql = "UPDATE matches SET revealed = TRUE WHERE id = ? AND (user1_id = ? OR user2_id = ?)"
            
            async with self._db.execute(sql, (match_id, user_id, user_id)):
                # We don't need to commit here if spend_coins already committed, 
                # but we commit for safety if the operations are separate.
                await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Error revealing match identity for match {match_id}: {e}")
            await self._db.rollback()
            return False
        
    
    async def get_weekly_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Fetches the current top users and their likes from the leaderboard_cache
        table for the current week. Returns a list of dicts with user info.
        """
        try:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_start_str = week_start.isoformat()

            sql = """
                SELECT u.id, u.name, u.campus, lc.likes_received
                FROM leaderboard_cache lc
                JOIN users u ON lc.user_id = u.id
                WHERE lc.week_start = ?
                ORDER BY lc.likes_received DESC, u.name ASC
                LIMIT ?
            """
            async with self._db.execute(sql, (week_start_str, limit)) as cursor:
                rows = await cursor.fetchall()
                return [_dict_from_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching weekly leaderboard: {e}")
            return []


db = Database()
