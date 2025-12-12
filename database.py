import os
import random
import asyncpg
import logging
import json
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, date, timedelta

from dotenv import load_dotenv

from services.match_classifier import classify_match
from utils import calculate_vibe_compatibility, recency_score

# Configure logging
logger = logging.getLogger(__name__)

# --- Helper Function ---
def _dict_from_row(row: asyncpg.Record) -> Optional[Dict[str, Any]]:
    """Converts an asyncpg.Record object to a dictionary."""
    if not row:
        return None
    return dict(row.items())
load_dotenv()
class Database:
    """
    An async-compatible PostgreSQL database class for AAUPulse.
    This class handles all database operations, replacing the original SQLite implementation.
    """
    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv("POSTGRES_DSN")
        if not self.dsn:
            raise ValueError("POSTGRES_DSN not set in environment or passed to Database.")
        self._pool: asyncpg.Pool | None = None
        
    
    @property
    def pool(self):
        if not self._pool:
            raise RuntimeError("Database not connected yet")
        return self._pool

    async def connect(self, reset: bool = False):
        """
        Initializes the database pool and creates tables.
        If reset=True, drops existing schema before re-initializing.
        """
        try:
            self._pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=10)
            async with self._pool.acquire() as conn:
                await conn.execute("SET TIME ZONE 'UTC'")
                if reset:
                    logger.warning("⚠️ Resetting database schema...")
                    await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
                await self._initialize_db(conn)
            logger.info("Database pool created and tables initialized.")
        except Exception as e:
            logger.critical(f"FATAL: Could not connect to database at {self.dsn}: {e}")
            raise

    async def close(self):
        """Closes the database pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed.")
            
    async def _initialize_db(self, conn: asyncpg.Connection):
        """Creates all necessary tables and indexes if they don't exist."""
        # --- Users Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
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
                created_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # --- Match Queue Table --- #
        await conn.execute("""

            CREATE TABLE IF NOT EXISTS match_queue (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    user1_id BIGINT NOT NULL,
                    user2_id BIGINT NOT NULL,

                    campus1 TEXT,
                    campus2 TEXT,
                    department1 TEXT,
                    department2 TEXT,
                    year1 TEXT,
                    year2 TEXT,

                    interests JSONB,
                    vibe_score FLOAT,
                    special_type TEXT,

                    created_at TIMESTAMP DEFAULT NOW(),
                    next_post_time TIMESTAMP,
                    sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP,

                    error TEXT DEFAULT NULL,
                    admin_notes TEXT DEFAULT NULL
                );

           

            """)

        # --- Likes Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                liker_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                liked_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(liker_id, liked_id)
            );
        """)

        # --- Matches Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                initiator_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                revealed BOOLEAN DEFAULT FALSE,
                chat_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- Chats Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE,
                sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                message TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- Confessions Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS confessions (
                id SERIAL PRIMARY KEY,
                sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                campus TEXT,
                department TEXT,
                text TEXT,
                status TEXT DEFAULT 'pending',
                channel_message_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- Referrals Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                referred_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                coins_awarded INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- Transactions Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                amount INTEGER CHECK(amount != 0),
                type TEXT CHECK(type IN (
                    'daily_login',
                    'referral',
                    'confession',
                    'match',
                    'purchase',
                    'system'
                )),
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- Daily Logins Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_logins (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                login_date DATE,
                UNIQUE(user_id, login_date)
            );
        """)

        # --- Leaderboard Cache ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard_cache (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                week_start DATE,
                likes_received INTEGER DEFAULT 0,
                matches_count INTEGER DEFAULT 0,
                UNIQUE(user_id, week_start)
            );
        """)

        # --- Passes Table ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS passes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                target_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, target_id)
            );
        """)

        # --- Interests Catalog ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS interest_catalog (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE
            );
        """)

        # --- User Activity ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                last_seen TIMESTAMP NOT NULL
            );
        """)

        # --- Interests ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS interests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                interest_id INTEGER REFERENCES interest_catalog(id) ON DELETE CASCADE,
                UNIQUE(user_id, interest_id)
            );
            
            ALTER TABLE users ALTER COLUMN id TYPE BIGINT;
            ALTER TABLE likes ALTER COLUMN liker_id TYPE BIGINT;
            ALTER TABLE likes ALTER COLUMN liked_id TYPE BIGINT;
            ALTER TABLE matches ALTER COLUMN user1_id TYPE BIGINT;
            ALTER TABLE matches ALTER COLUMN user2_id TYPE BIGINT;
            ALTER TABLE matches ALTER COLUMN initiator_id TYPE BIGINT;
            ALTER TABLE chats ALTER COLUMN sender_id TYPE BIGINT;
            ALTER TABLE confessions ALTER COLUMN sender_id TYPE BIGINT;
            ALTER TABLE referrals ALTER COLUMN referrer_id TYPE BIGINT;
            ALTER TABLE referrals ALTER COLUMN referred_id TYPE BIGINT;
            ALTER TABLE transactions ALTER COLUMN user_id TYPE BIGINT;
            ALTER TABLE daily_logins ALTER COLUMN user_id TYPE BIGINT;
            ALTER TABLE leaderboard_cache ALTER COLUMN user_id TYPE BIGINT;
            ALTER TABLE passes ALTER COLUMN user_id TYPE BIGINT;
            ALTER TABLE passes ALTER COLUMN target_id TYPE BIGINT;
            ALTER TABLE user_activity ALTER COLUMN user_id TYPE BIGINT;
            ALTER TABLE interests ALTER COLUMN user_id TYPE BIGINT;
        """)


        # --- Indexes ---
        await  conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_liker_id ON likes (liker_id);")
        await  conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_liked_id ON likes (liked_id);")
        await  conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_users ON matches (user1_id, user2_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_match_id ON chats (match_id);")
        await  conn.execute("CREATE INDEX IF NOT EXISTS idx_confessions_status ON confessions (status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_passes_user_id_created ON passes (user_id, created_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id_created ON transactions (user_id, created_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_interests_user_id ON interests(user_id);")
        
        
     

    async def fetch(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)

    async def execute(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *args)


    async def get_user(self, user_id: int) -> Optional[Dict]:
            try:
                row = await self.fetchrow(
                    "SELECT * FROM users WHERE id = $1", user_id
                )
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
            placeholders = ', '.join(f"${i+1}" for i in range(len(user_data)))
            sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
            
            await self.execute(sql, *user_data.values())
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    async def update_user(self, user_id: int, updates: Dict) -> bool:
        if not updates:
            return True
        try:
            if 'vibe_score' in updates and isinstance(updates['vibe_score'], dict):
                updates['vibe_score'] = json.dumps(updates['vibe_score'])

            set_clause = ", ".join([f"{key} = ${i+1}" for i, key in enumerate(updates)])
            values = list(updates.values())
            values.append(user_id)
            
            sql = f"UPDATE users SET {set_clause} WHERE id = ${len(values)}"
            
            await self.execute(sql, *values)
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False

    async def update_last_active(self, user_id: int):
        try:
            await self.execute(
                "UPDATE users SET last_active = NOW() WHERE id = $1",
                user_id
            )
        except Exception as e:
            logger.error(f"Error updating last_active for {user_id}: {e}")

    async def get_matches_for_user(self, user_id: int, filters: Dict = None) -> List[Dict]:
        try:
            user = await self.get_user(user_id)
            if not user:
                return []

            params = [user_id, user_id, user_id, user_id]

            sql = """
                    WITH pass_counts AS (
                        SELECT target_id, COUNT(*) AS pass_count
                        FROM passes
                        WHERE user_id = $1
                        AND created_at > NOW() - INTERVAL '3 days'
                        GROUP BY target_id
                    ),
                    mutual_likes AS (
                        SELECT liker_id
                        FROM likes
                        WHERE liked_id = $2
                    )
                    SELECT u.*,
                        COALESCE(pc.pass_count, 0) AS pass_count,
                        CASE WHEN u.id IN (SELECT liker_id FROM mutual_likes) THEN 1 ELSE 0 END AS liked_you
                    FROM users u
                    LEFT JOIN pass_counts pc ON u.id = pc.target_id
                    WHERE u.id != $3
                    AND u.is_active = TRUE
                    AND u.is_banned = FALSE
                    AND u.id NOT IN (SELECT liked_id FROM likes WHERE liker_id = $4)
                    AND pc.pass_count IS NULL
                    """


            # --- Dynamic filters ---
            if user.get("seeking_gender", "").lower() != "any":
                sql += f" AND LOWER(u.gender) = ${len(params)+1}"
                params.append(user["seeking_gender"].lower())

            sql += f" AND (LOWER(u.seeking_gender) = 'any' OR LOWER(u.seeking_gender) = ${len(params)+1})"
            params.append(user.get("gender", "").lower())

            if filters:
                if filters.get("campus"):
                    sql += f" AND u.campus = ${len(params)+1}"
                    params.append(filters["campus"])
                if filters.get("department"):
                    sql += f" AND u.department = ${len(params)+1}"
                    params.append(filters["department"])
                if filters.get("year"):
                    sql += f" AND u.year = ${len(params)+1}"
                    params.append(filters["year"])

            sql += " ORDER BY liked_you DESC, u.last_active DESC LIMIT 100"

            rows = await self.fetch(sql, *params)
            candidates = [_dict_from_row(row) for row in rows]

            # --- Ranking ---
            # Parse viewer vibe safely
            raw_viewer_vibe = user.get("vibe_score")
            if isinstance(raw_viewer_vibe, str):
                try:
                    viewer_vibe = json.loads(raw_viewer_vibe)
                except Exception:
                    viewer_vibe = {}
            elif isinstance(raw_viewer_vibe, dict):
                viewer_vibe = raw_viewer_vibe
            else:
                viewer_vibe = {}

            viewer_interests = await self.get_user_interests(user_id)

            # Batch fetch candidate interests
            candidate_ids = [c["id"] for c in candidates]
            all_interests = await self.get_multiple_user_interests(candidate_ids)  # implement this helper

            def rank(c):
                raw_c_vibe = c.get("vibe_score")
                if isinstance(raw_c_vibe, str):
                    try:
                        cand_vibe = json.loads(raw_c_vibe)
                    except Exception:
                        cand_vibe = {}
                elif isinstance(raw_c_vibe, dict):
                    cand_vibe = raw_c_vibe
                else:
                    cand_vibe = {}

                vibe = calculate_vibe_compatibility(viewer_vibe, cand_vibe)
                overlap = len(set(viewer_interests) & set(all_interests.get(c["id"], [])))
                recency = recency_score(c.get("last_active"))
                liked_you = c.get("liked_you", 0)
                pass_count = c.get("pass_count", 0)

                score = (0.45 * vibe +
                        0.25 * overlap +
                        0.2 * recency +
                        0.1 * liked_you)

                if pass_count == 1:
                    score *= 0.5

                return score

            candidates.sort(key=rank, reverse=True)

            # Keep top 50, but shuffle lightly for variety
            top = candidates[:50]
            random.shuffle(top[:10])  # shuffle only top 10 for freshness
            return top

        except Exception as e:
            logger.error(f"Error getting matches for user {user_id}: {e}")
            return []


    async def get_multiple_user_interests(self, user_ids: List[int]) -> Dict[int, List[str]]:
        """
        Fetch interests for multiple users in one query.
        Returns a dict mapping user_id -> list of interest names.
        """
        if not user_ids:
            return {}

        query = """
            SELECT i.user_id, ic.name
            FROM interests i
            JOIN interest_catalog ic ON i.interest_id = ic.id
            WHERE i.user_id = ANY($1)
        """
        rows = await self.fetch(query, user_ids)

        interests_map: Dict[int, List[str]] = {}
        for row in rows:
            uid = row["user_id"]
            interests_map.setdefault(uid, []).append(row["name"])

        return interests_map

    
    
    async def count_active_users(self, minutes: int = 10) -> int:
        query = """
            SELECT COUNT(DISTINCT user_id) as cnt
            FROM user_activity
            WHERE last_seen >= NOW() - ($1 * INTERVAL '1 minute')
        """
        row = await self.fetchrow(query, minutes)
        return row["cnt"] if row else 0


# Count new likes (admirers) for a given user
    async def count_new_likes(self, user_id: int) -> int:
        query = """
            SELECT COUNT(*) as cnt
            FROM likes
            WHERE liked_id = $1
        """
        row = await self.fetchrow(query, user_id)
        return row["cnt"] if row else 0

    # --- Interests Helpers ---

    async def get_user_interests(self, user_id: int) -> List[str]:
        query = """
            SELECT ic.name
            FROM interests i
            JOIN interest_catalog ic ON i.interest_id = ic.id
            WHERE i.user_id = $1
        """
        rows = await self.fetch(query, user_id)
        return [row["name"] for row in rows]

    async def get_other_user_ids(self, user_id: int) -> List[int]:
        query = "SELECT id FROM users WHERE id != $1"
        rows = await self.fetch(query, user_id)
        return [row["id"] for row in rows]

    async def set_user_interests(self, user_id: int, interests: List[str]):
        """
        Replace a user's interests with the provided list.
        Ensures each interest exists in the catalog.
        """
        try:
            # Clear old interests
            await self.execute("DELETE FROM interests WHERE user_id = $1", user_id)

            for interest in interests:
                interest = interest.strip()
                if not interest:
                    continue

                # Ensure interest exists in catalog
                row = await self.fetchrow(
                    "SELECT id FROM interest_catalog WHERE name = $1", interest
                )

                if row:
                    interest_id = row["id"]
                else:
                    row = await self.fetchrow(
                        "INSERT INTO interest_catalog (name) VALUES ($1) RETURNING id",
                        interest
                    )
                    interest_id = row["id"]

                # Insert into user interests
                await self.execute(
                    "INSERT INTO interests (user_id, interest_id) VALUES ($1, $2) "
                    "ON CONFLICT (user_id, interest_id) DO NOTHING",
                    user_id, interest_id
                )

        except Exception as e:
            logger.error(f"Error setting interests for user {user_id}: {e}")

    from services.match_classifier import classify_match

    # small helper to compute next_post_time (naive local time)
    


    async def add_like(self, liker_id: int, liked_id: int, bot=None) -> dict:
        """
        Extended add_like:
        - registers likes
        - detects mutual like
        - creates match
        - classifies match
        - QUEUES special matches via MatchQueueService
        """

        try:
            # ----------------------------------------------------
            # INSERT LIKE (idempotent)
            # ----------------------------------------------------
            await self.execute(
                "INSERT INTO likes (liker_id, liked_id) VALUES ($1, $2) "
                "ON CONFLICT (liker_id, liked_id) DO NOTHING",
                liker_id, liked_id
            )

            # ----------------------------------------------------
            # CHECK REVERSE LIKE (mutual)
            # ----------------------------------------------------
            reverse_like = await self.fetchrow(
                "SELECT id FROM likes WHERE liker_id = $1 AND liked_id = $2",
                liked_id, liker_id
            )

            if not reverse_like:
                await self.update_leaderboard_cache()
                return {"status": "liked"}  # one-sided like → done

            # ----------------------------------------------------
            # MUTUAL LIKE → CREATE MATCH
            # ----------------------------------------------------
            row = await self.fetchrow(
                """
                SELECT liker_id
                FROM likes
                WHERE (liker_id = $1 AND liked_id = $2)
                OR (liker_id = $3 AND liked_id = $4)
                ORDER BY id ASC
                LIMIT 1
                """,
                liker_id, liked_id, liked_id, liker_id
            )
            initiator_id = row["liker_id"] if row else liker_id

            user1_id = min(liker_id, liked_id)
            user2_id = max(liker_id, liked_id)

            match_row = await self.fetchrow(
                "INSERT INTO matches (user1_id, user2_id, initiator_id) "
                "VALUES ($1,$2,$3) RETURNING id",
                user1_id, user2_id, initiator_id
            )
            match_id = match_row["id"]

            # ----------------------------------------------------
            # COLLECT USER PROFILES + INTERESTS
            # ----------------------------------------------------
            user1 = await self.get_user(user1_id)
            user2 = await self.get_user(user2_id)

            interests1 = await self.get_user_interests(user1_id)
            interests2 = await self.get_user_interests(user2_id)

            # ----------------------------------------------------
            # VIBE SCORE (JSON)
            # ----------------------------------------------------
            try:
                vibe1 = json.loads(user1.get("vibe_score", "{}") or "{}")
            except:
                vibe1 = {}

            try:
                vibe2 = json.loads(user2.get("vibe_score", "{}") or "{}")
            except:
                vibe2 = {}

            try:
                from utils import calculate_vibe_compatibility
                vibe_score = calculate_vibe_compatibility(vibe1, vibe2) or 0.0
            except:
                vibe_score = 0.0

            # ----------------------------------------------------
            # CLASSIFY MATCH
            # ----------------------------------------------------
            special_type, shared_interests, vibe_score = classify_match(
                user1, user2, interests1, interests2, vibe_score
            )

            # ----------------------------------------------------
            # DECIDE IF THIS MATCH SHOULD BE QUEUED
            # ----------------------------------------------------
            should_queue = bool(special_type) or (random.random() < 0.10)
            from services.match_queue_service import MatchQueueService


            if should_queue:
                # use the official queueing service
                queue_service = MatchQueueService(self, bot)

                await queue_service.queue_match(
                    match={"id": match_id},
                    user1=user1,
                    user2=user2,
                    special_type=special_type,
                    vibe_score=vibe_score,
                    interests=shared_interests
                )

            # DO NOT reward coins here
            await self.update_leaderboard_cache()

            return {"status": "match", "match_id": match_id}

        except Exception as e:
            logger.error(f"Error adding like from {liker_id} to {liked_id}: {e}")
            return {"status": "error"}
        
    async def get_user_stats(self, user_id: int) -> Dict:
        stats = {'likes_sent': 0, 'likes_received': 0, 'matches': 0, 'referrals': 0}
        try:
            row = await self.fetchrow("SELECT COUNT(*) AS cnt FROM likes WHERE liker_id = $1", user_id)
            stats['likes_sent'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(*) AS cnt FROM likes WHERE liked_id = $1", user_id)
            stats['likes_received'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(*) AS cnt FROM matches WHERE user1_id = $1 OR user2_id = $1", user_id)
            stats['matches'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(*) AS cnt FROM referrals WHERE referrer_id = $1", user_id)
            stats['referrals'] = row["cnt"] if row else 0

            return stats
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return stats

    async def get_referrals(self, user_id: int, offset: int = 0, limit: int = 10) -> List[Dict]:
        try:
            sql = """
                SELECT referred_id, created_at
                FROM referrals
                WHERE referrer_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await self.fetch(sql, user_id, limit, offset)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching referrals for {user_id}: {e}")
            return []

    async def get_user_rank(self, user_id: int) -> int | None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start

        sql = """
            SELECT user_id, RANK() OVER (ORDER BY likes_received DESC, u.name ASC) as rnk
            FROM leaderboard_cache lc
            JOIN users u ON lc.user_id = u.id
            WHERE week_start = $1
        """
        rows = await self.fetch(sql, week_start_str)
        for row in rows:
            if row["user_id"] == user_id:
                return row["rnk"]
        return None

    async def remove_like(self, liker_id: int, liked_id: int) -> bool:
        try:
            status = await self.execute(
                "DELETE FROM likes WHERE liker_id = $1 AND liked_id = $2",
                liker_id, liked_id
            )
            await self.update_leaderboard_cache()
            # asyncpg returns e.g. "DELETE 1" or "DELETE 0"
            return status.startswith("DELETE 1")
        except Exception as e:
            logger.error(f"Error removing like {liker_id}->{liked_id}: {e}")
            return False

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
            LIMIT $1
        """
        rows = await self.fetch(query, limit)
        return [dict(row) for row in rows]

    async def get_match_by_id(self, match_id: int) -> Optional[Dict]:
        row = await self.fetchrow(
            "SELECT id as match_id, user1_id, user2_id, chat_active, revealed FROM matches WHERE id = $1",
            match_id
        )
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
        try:
            row = await self.fetchrow(
                "SELECT id as match_id, user1_id, user2_id, chat_active, revealed FROM matches WHERE id = $1",
                match_id
            )
            if not row:
                logger.error(f"No match found with id {match_id} for user {user_id}")
                return None

            user1_id, user2_id = row['user1_id'], row['user2_id']
            if user_id not in (user1_id, user2_id):
                logger.error(f"User {user_id} is not part of match {match_id}")
                return None

            other_user_id = user2_id if user1_id == user_id else user1_id

            # ✅ use self._pool instead of self.pool
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE matches SET chat_active = FALSE, revealed = FALSE WHERE id = $1",
                    match_id
                )
                await conn.execute(
                    "DELETE FROM likes WHERE (liker_id = $1 AND liked_id = $2) OR (liker_id = $2 AND liked_id = $1)",
                    user_id, other_user_id
                )

            logger.info(f"Unmatched successfully for match_id={match_id}, user_id={user_id}")

            updated_row = await self.fetchrow(
                "SELECT id as match_id, user1_id, user2_id, chat_active, revealed FROM matches WHERE id = $1",
                match_id
            )
            if updated_row:
                return {
                    "match_id": updated_row["match_id"],
                    "user1_id": updated_row["user1_id"],
                    "user2_id": updated_row["user2_id"],
                    "chat_active": bool(updated_row["chat_active"]),
                    "revealed": bool(updated_row["revealed"]),
                }
            return None

        except Exception as e:
            logger.error(f"Error unmatching {match_id} by {user_id}: {e}")
            return None

    async def get_who_liked_me(self, user_id: int) -> list[dict]:
        try:
            sql = """
                SELECT DISTINCT u.id, u.name, u.username, u.photo_file_id
                FROM likes l
                JOIN users u ON u.id = l.liker_id
                WHERE l.liked_id = $1
                AND NOT EXISTS (
                    SELECT 1 FROM matches m
                    WHERE ((m.user1_id = l.liker_id AND m.user2_id = l.liked_id)
                        OR (m.user1_id = l.liked_id AND m.user2_id = l.liker_id))
                        AND m.chat_active = TRUE
                )
            """
            rows = await self.fetch(sql, user_id)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting who liked me for {user_id}: {e}")
            return []

    async def get_my_likes(self, user_id: int) -> list[dict]:
        try:
            sql = """
                SELECT DISTINCT u.id, u.name, u.username, u.photo_file_id
                FROM likes l
                JOIN users u ON u.id = l.liked_id
                WHERE l.liker_id = $1
                AND NOT EXISTS (
                    SELECT 1 FROM matches m
                    WHERE ((m.user1_id = l.liker_id AND m.user2_id = l.liked_id)
                        OR (m.user1_id = l.liked_id AND m.user2_id = l.liker_id))
                        AND m.chat_active = TRUE
                )
            """
            rows = await self.fetch(sql, user_id)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting my likes for {user_id}: {e}")
            return []


    async def get_user_matches(self, user_id: int) -> List[Dict]:
        try:
            sql = """
                SELECT DISTINCT 
                    m.id AS match_id,
                    m.revealed,
                    m.initiator_id,
                    CASE WHEN m.user1_id = $1 THEN m.user2_id ELSE m.user1_id END AS other_user_id
                FROM matches m
                WHERE (m.user1_id = $1 OR m.user2_id = $1)
                  AND m.chat_active = TRUE
            """
            rows = await self.fetch(sql, user_id)

            result = []
            seen = set()
            for match_row in rows:
                other_id = match_row["other_user_id"]
                if other_id in seen:
                    continue
                seen.add(other_id)

                other_user = await self.get_user(other_id)
                if other_user:
                    result.append({
                        "match_id": match_row["match_id"],
                        "user": other_user,
                        "revealed": bool(match_row["revealed"]),
                        "initiator_id": match_row["initiator_id"],
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
                SELECT m.id AS match_id, m.revealed, m.user1_id, m.user2_id
                FROM matches m
                WHERE (m.user1_id = $1 AND m.user2_id = $2)
                   OR (m.user1_id = $3 AND m.user2_id = $4)
                LIMIT 1
            """
            row = await self.fetchrow(sql, user1_id, user2_id, user2_id, user1_id)
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
            SELECT id AS match_id, user1_id, user2_id, initiator_id, chat_active, revealed
            FROM matches
            WHERE chat_active = TRUE
              AND ((user1_id = $1 AND user2_id = $2) OR (user1_id = $3 AND user2_id = $4))
            LIMIT 1
        """
        row = await self.fetchrow(sql, user1_id, user2_id, user2_id, user1_id)

        if row:
            return {
                "match_id": row["match_id"],
                "user1_id": row["user1_id"],
                "user2_id": row["user2_id"],
                "initiator_id": row["initiator_id"],
                "chat_active": bool(row["chat_active"]),
                "revealed": bool(row["revealed"]),
            }
        return None

    async def save_chat_message(self, match_id: int, sender_id: int, message: str) -> bool:
        try:
            sql = "INSERT INTO chats (match_id, sender_id, message) VALUES ($1, $2, $3)"
            await self.execute(sql, match_id, sender_id, message)
            return True
        except Exception as e:
            logger.error(f"Error saving chat message for match {match_id}: {e}")
            return False

    async def get_chat_history(self, match_id: int, limit: int = 20) -> List[Dict]:
        try:
            sql = "SELECT * FROM chats WHERE match_id = $1 ORDER BY created_at DESC LIMIT $2"
            rows = await self.fetch(sql, match_id, limit)
            return list(reversed([dict(r.items()) for r in rows]))
        except Exception as e:
            logger.error(f"Error getting chat history for match {match_id}: {e}")
            return []

    async def add_pass(self, user_id: int, target_id: int) -> Dict[str, Any]:
        """
        Records a 'pass' (ignore/swipe-left) action.
        Ensures the same pass isn't duplicated.
        """
        try:
            result = await self.execute(
                """
                INSERT INTO passes (user_id, target_id, created_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id, target_id) DO NOTHING
                """,
                user_id, target_id
            )
            return {"status": "passed"}
        except Exception as e:
            logger.error(f"Error adding pass for user {user_id} -> {target_id}: {e}")
            return {"status": "error", "error": str(e)}

    
    async def delete_confession(self, confession_id: int) -> None:
        sql = "DELETE FROM confessions WHERE id = $1"
        await self.execute(sql, confession_id)
    
    async def get_user_confessions(self, sender_id: int) -> list[dict]:
        """
        Fetch all confessions submitted by a user.
        Returns a list of dicts with id, campus, department, text, status, channel_message_id, created_at.
        """
        sql = """
        SELECT id, campus, department, text, status, channel_message_id, created_at
        FROM confessions
        WHERE sender_id = $1
        ORDER BY created_at DESC
        """
        rows = await self.fetch(sql, sender_id)
        # Convert asyncpg.Record → dict
        return [dict(row) for row in rows] if rows else []

    async def create_confession(self, sender_id: int, confession_data: Dict) -> Optional[int]:
        try:
            sql = """
            INSERT INTO confessions (sender_id, campus, department, text)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """
            row = await self.fetchrow(
                sql,
                sender_id,
                confession_data['campus'],
                confession_data['department'],
                confession_data['text']
            )
            return row["id"] if row else None
        except Exception as e:
            logger.error(f"Error creating confession for user {sender_id}: {e}")
            return None

    async def get_confession(self, confession_id: int) -> Optional[Dict]:
        """Fetches a single confession by its ID."""
        try:
            row = await self.fetchrow("SELECT * FROM confessions WHERE id = $1", confession_id)
            return dict(row.items()) if row else None
        except Exception as e:
            logger.error(f"Error getting confession {confession_id}: {e}")
            return None

    async def get_pending_confessions(self) -> List[Dict]:
        try:
            sql = "SELECT * FROM confessions WHERE status = 'pending' ORDER BY created_at ASC"
            rows = await self.fetch(sql)
            return [dict(r.items()) for r in rows]
        except Exception as e:
            logger.error(f"Error getting pending confessions: {e}")
            return []

    async def update_confession_status(self, confession_id: int, status: str, message_id: Optional[int] = None) -> bool:
        try:
            sql = "UPDATE confessions SET status = $1, channel_message_id = $2 WHERE id = $3"
            await self.execute(sql, status, message_id, confession_id)
            return True
        except Exception as e:
            logger.error(f"Error updating confession {confession_id}: {e}")
            return False

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        try:
            # UNIQUE(referred_id) exists; this will error if duplicate. Keep logic same.
            sql = "INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)"
            await self.execute(sql, referrer_id, referred_id)

            await self.add_coins(referrer_id, 50, 'referral', f'Referred user {referred_id}')
            return True
        except Exception as e:
            logger.error(f"Error adding referral from {referrer_id} to {referred_id}: {e}")
            return False

    async def add_coins(self, user_id: int, amount: int, tx_type: str, description: str) -> bool:
        try:
            await self.execute("UPDATE users SET coins = coins + $1 WHERE id = $2", amount, user_id)
            await self.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
                user_id, amount, tx_type, description
            )
            return True
        except Exception as e:
            logger.error(f"Error adding {amount} coins to user {user_id}: {e}")
            return False

    async def spend_coins(self, user_id: int, amount: int, tx_type: str, description: str) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user or user['coins'] < amount:
                return False

            if tx_type not in {"daily_login", "referral", "confession", "match", "purchase", "system"}:
                tx_type = "purchase"

            await self.execute(
                "UPDATE users SET coins = coins - $1 WHERE id = $2",
                amount, user_id
            )
            await self.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
                user_id, -amount, tx_type, description
            )
            return True
        except Exception as e:
            logger.error(f"Error spending {amount} coins for user {user_id}: {e}")
            return False

    async def get_transactions(self, user_id: int, offset: int = 0, limit: int = 10) -> List[Dict]:
        try:
            sql = """
                SELECT amount, type, description, created_at
                FROM transactions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await self.fetch(sql, user_id, limit, offset)
            return [dict(row.items()) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching transactions for {user_id}: {e}")
            return []


    async def record_daily_login(self, user_id: int) -> bool:
        try:
            today = date.today()
            # Return a row only if inserted; avoids guessing rowcount/status strings
            row = await self.fetchrow(
                "INSERT INTO daily_logins (user_id, login_date) VALUES ($1, $2) "
                "ON CONFLICT (user_id, login_date) DO NOTHING "
                "RETURNING 1",
                user_id, today
            )
            if row:
                await self.add_coins(user_id, 10, 'daily_login', 'Daily login bonus')
                return True
            return False
        except Exception as e:
            logger.error(f"Error recording daily login for user {user_id}: {e}")
            return False

    async def get_daily_streak(self, user_id: int) -> int:
        try:
            rows = await self.fetch(
                "SELECT login_date FROM daily_logins WHERE user_id = $1 ORDER BY login_date DESC",
                user_id
            )
            # login_date is DATE in Postgres; ensure it's a date object
            dates = [r["login_date"] if isinstance(r["login_date"], date) else date.fromisoformat(str(r["login_date"])) for r in rows]

            today = date.today()
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
            week_start_str = week_start

            # Clear old cache for this week
            await self.execute(
                "DELETE FROM leaderboard_cache WHERE week_start = $1",
                week_start_str
            )

            # Insert all users with their like counts (0 if none), considering only likes from this week
            sql = """
                INSERT INTO leaderboard_cache (user_id, week_start, likes_received)
                SELECT u.id, $1, COALESCE(COUNT(l.id), 0) AS likes_received
                FROM users u
                LEFT JOIN likes l
                    ON l.liked_id = u.id
                    AND DATE(l.created_at) >= $1
                WHERE u.is_active = TRUE AND u.is_banned = FALSE
                GROUP BY u.id
            """
            status = await self.execute(sql, week_start_str)
            # status example: "INSERT 0 <n>"
            try:
                inserted = int(status.split()[-1])
            except Exception:
                inserted = 0
            logger.info(f"Leaderboard cache updated for {week_start_str}: {inserted} rows inserted")

            return True
        except Exception as e:
            logger.error(f"Error updating leaderboard cache: {e}")
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
                WHERE lc.week_start = $1
                ORDER BY lc.likes_received DESC, u.name ASC
                LIMIT 10
            """
            rows = await self.fetch(sql, week_start)
            return [dict(r.items()) for r in rows]
        except Exception as e:
            logger.error(f"Error getting leaderboard for week {week_start}: {e}")
            return []


    async def increment_field(self, user_id: int, field: str, amount: int = 1) -> bool:
        try:
            query = f"UPDATE users SET {field} = {field} + $1 WHERE id = $2"
            await self.execute(query, amount, user_id)
            return True
        except Exception as e:
            logger.error(f"Error incrementing {field} for user {user_id}: {e}")
            return False

    async def get_user_rank(self, user_id: int) -> int | None:
        """
        Returns the 1-based rank of the user for the current week, or None if not found.
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start

        sql = """
            SELECT rank_alias.rank
            FROM (
                SELECT
                    user_id,
                    RANK() OVER (ORDER BY likes_received DESC, u.name ASC) AS rank
                FROM leaderboard_cache lc
                JOIN users u ON lc.user_id = u.id
                WHERE week_start = $1
            ) rank_alias
            WHERE rank_alias.user_id = $2
        """
        try:
            row = await self.fetchrow(sql, week_start_str, user_id)
            return row["rank"] if row else None
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
            row = await self.fetchrow("SELECT COUNT(id) AS cnt FROM users")
            stats['total_users'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(id) AS cnt FROM users WHERE is_active = TRUE")
            stats['active_users'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(id) AS cnt FROM matches")
            stats['total_matches'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(id) AS cnt FROM confessions")
            stats['total_confessions'] = row["cnt"] if row else 0

            row = await self.fetchrow("SELECT COUNT(id) AS cnt FROM confessions WHERE status = 'pending'")
            stats['pending_confessions'] = row["cnt"] if row else 0

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
            params = []
            sql = "SELECT id FROM users WHERE is_active = TRUE AND is_banned = FALSE"
            if limit is not None:
                sql += " LIMIT $1"
                params.append(limit)

            rows = await (self.fetch(sql, *params) if params else self.fetch(sql))
            return [r["id"] for r in rows]
        except Exception as e:
            logger.error(f"Error getting active user IDs for notification: {e}")
            return []



    async def get_all_active_user_ids(self) -> List[int]:
        """Returns a list of IDs for all active, non-banned users."""
        try:
            sql = "SELECT id FROM users WHERE is_active = TRUE AND is_banned = FALSE"
            rows = await self.fetch(sql)
            return [row['id'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting active user IDs: {e}")
            return []

    async def reveal_match_identity(self, match_id: int, user_id: int) -> bool:
        """Sets the 'revealed' flag to True for a specific match, ensuring the user is one of the participants."""
        try:
            sql = "UPDATE matches SET revealed = TRUE WHERE id = $1 AND (user1_id = $2 OR user2_id = $2)"
            await self.execute(sql, match_id, user_id)
            return True
        except Exception as e:
            logger.error(f"Error revealing match identity for match {match_id}: {e}")
            return False

    async def get_weekly_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Fetches the current top users and their likes from the leaderboard_cache
        table for the current week. Returns a list of dicts with user info.
        """
        try:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_start_str = week_start

            sql = """
                SELECT u.id, u.name, u.campus, lc.likes_received
                FROM leaderboard_cache lc
                JOIN users u ON lc.user_id = u.id
                WHERE lc.week_start = $1
                ORDER BY lc.likes_received DESC, u.name ASC
                LIMIT $2
            """
            rows = await self.fetch(sql, week_start_str, limit)
            return [dict(r.items()) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching weekly leaderboard: {e}")
            return []

    # --- Admin Helpers ---

    async def get_users_page(self, offset: int = 0, limit: int = 5) -> list[dict]:
        """
        Return a paginated list of users ordered by created_at DESC.
        Used in admin panel browsing.
        """
        try:
            sql = "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            rows = await self.fetch(sql, limit, offset)
            return [dict(r.items()) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"Error fetching users page: {e}")
            return []

    async def count_users(self) -> int:
        """Return total number of users."""
        try:
            row = await self.fetchrow("SELECT COUNT(*) AS c FROM users")
            return row["c"] if row else 0
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    async def set_user_banned(self, user_id: int, banned: bool = True) -> bool:
        """Toggle a user's banned status."""
        try:
            await self.execute(
                "UPDATE users SET is_banned = $1 WHERE id = $2",
                banned, user_id
            )
            return True
        except Exception as e:
            logger.error(f"Error setting banned={banned} for user {user_id}: {e}")
            return False

    async def set_user_active(self, user_id: int, active: bool = True) -> bool:
        """Toggle a user's active status."""
        try:
            await self.execute(
                "UPDATE users SET is_active = $1 WHERE id = $2",
                active, user_id
            )
            return True
        except Exception as e:
            logger.error(f"Error setting active={active} for user {user_id}: {e}")
            return False

    async def delete_user(self, user_id: int) -> bool:
        """Hard delete a user row (use with caution)."""
        try:
            await self.execute("DELETE FROM users WHERE id = $1", user_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False


db = Database()

