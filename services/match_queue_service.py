# services/match_queue_service.py

import json
from datetime import datetime, timedelta

from bot_config import CHANNEL_ID, ADMIN_GROUP_ID
from database import Database
from services.content_builder import build_match_drop_text


PRIME_POST_TIMES = [
    (12, 15),
    (15, 0),
    (18, 0),
    (20, 0),
    (22, 30),
]


class MatchQueueService:

    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot

    # ----------------------------------------------------
    # PICK NEXT PRIME TIME SLOT
    # ----------------------------------------------------
    def compute_next_post_time(self):
        now = datetime.now()

        for hour, minute in PRIME_POST_TIMES:
            scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled > now:
                return scheduled

        # If all today's times passed → tommorrow at 12:15
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=12, minute=15, second=0, microsecond=0)

    # ----------------------------------------------------
    # INSERT MATCH INTO QUEUE
    # ----------------------------------------------------
    async def queue_match(self, match, user1, user2, special_type, vibe_score, interests):
        """
        Push match into queue for channel posting.
        `interests` MUST be a list -> stored as JSON string.
        """

        next_time = self.compute_next_post_time()
        interests_json = json.dumps(interests or [])

        query = """
            INSERT INTO match_queue (
                match_id, user1_id, user2_id,
                campus1, campus2, department1, department2,
                year1, year2,
                interests, vibe_score, special_type,
                next_post_time
            )
            VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13
            )
            RETURNING id;
        """

        row = await self.db.pool.fetchrow(
            query,
            match["id"], user1["id"], user2["id"],
            user1.get("campus"), user2.get("campus"),
            user1.get("department"), user2.get("department"),
            user1.get("year"), user2.get("year"),
            interests_json,                   # JSON string
            float(vibe_score or 0.0),
            special_type,
            next_time
        )

        queue_id = row["id"]

        # Log to admin ONLY here (not for every like)
        await self.bot.send_message(
            ADMIN_GROUP_ID,
            (
                "🎉 <b>NEW MATCH QUEUED!</b>\n\n"
                f"🆔 <b>Queue ID:</b> <code>{queue_id}</code>\n"
                f"🎯 <b>Match ID:</b> <code>{match['id']}</code>\n"
                f"✨ <b>Type:</b> {special_type or '—'}\n"
                f"📊 <b>Vibe Score:</b> {vibe_score:.2f}\n"
                f"🕒 <b>Scheduled:</b> {next_time}\n\n"
                "👥 <b>Participants</b>\n"
                f"• 👤 <b>User1:</b> {user1['campus']} • {user1['department']} • {user1['year']}\n"
                f"• 👤 <b>User2:</b> {user2['campus']} • {user2['department']} • {user2['year']}\n\n"
                f"💡 <b>Shared Interests:</b> {', '.join(interests) if interests else 'None'}\n\n"
                "🚀 <i>Ready to drop into the channel!</i>"
            ),
            parse_mode="HTML"
        )



        return queue_id

    # ----------------------------------------------------
    # FETCH NEXT ITEM READY TO POST
    # ----------------------------------------------------
    async def get_due_item(self):
        query = """
            SELECT *
            FROM match_queue
            WHERE sent = FALSE
            AND next_post_time >= NOW()
            ORDER BY next_post_time ASC
            LIMIT 1;
        """
        return await self.db.pool.fetchrow(query)

    # ----------------------------------------------------
    # MARK QUEUE ITEM AS SENT
    # ----------------------------------------------------
    async def mark_sent(self, queue_id):
        await self.db.pool.execute(
            "UPDATE match_queue SET sent = TRUE, sent_at = NOW() WHERE id = $1",
            queue_id
        )

    # ----------------------------------------------------
    # SAVE SEND ERROR
    # ----------------------------------------------------
    async def record_error(self, queue_id, error_msg):
        await self.db.pool.execute(
            "UPDATE match_queue SET error = $1 WHERE id = $2",
            error_msg, queue_id
        )

        await self.bot.send_message(
            ADMIN_GROUP_ID,
            f"🟥 MATCH ERROR\n"
            f"Queue ID: {queue_id}\n"
            f"Error: {error_msg}"
        )
