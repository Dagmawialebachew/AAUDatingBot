

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import Database
from services.match_queue_service import MatchQueueService
from services.content_builder import build_match_drop_text
from services.match_classifier import classify_match

router = Router()



def setup_test_handlers(db: Database):
    @router.message(Command("test_fake_match"))
    async def test_fake_match(message: Message):
        """
        Manually push a fake match into match_queue and preview its text.
        """
        bot = message.bot
        service = MatchQueueService(db, bot)

        # Fake users — mimic your DB row structure EXACTLY
        user1 = {
            "id": 50001,
            "campus": "6kilo",
            "department": "Software",
            "year": "2nd Year",
            "vibe_score": "{}",
        }

        user2 = {
            "id": 50002,
            "campus": "5kilo",
            "department": "Engineering",
            "year": "3rd Year",
            "vibe_score": "{}",
        }

        # Fake interests
        interests1 = ["Music", "Movies", "Tech"]
        interests2 = ["Tech", "Gym"]

        # Classify match
        special_type, shared_interests, vibe_score = classify_match(
            user1, user2, interests1, interests2, 0.88
        )

        # Fake match row
        match_row = {"id": 999999}

        queue_id = await service.queue_match(
            match=match_row,
            user1=user1,
            user2=user2,
            special_type=special_type,
            vibe_score=vibe_score,
            interests=shared_interests,
        )

        return await message.answer(
            f"🧪 Fake match queued successfully!\nQueue ID: {queue_id}"
        )

    # -----------------------------------------------------

    @router.message(Command("test_run_scheduler"))
    async def test_run_scheduler(message: Message):
        """
        Run ONE cycle of match queue scheduler manually.
        If an item is due → build final text and send it.
        """
        bot = message.bot
        service = MatchQueueService(db, bot)

        item = await service.get_due_item()
        if not item:
            return await message.answer("No due match_queue items.")

        # Build final channel post text
        text = build_match_drop_text(item)

        # For safety: send ONLY to the chat you are testing in
        await message.answer("🔮 Generated content preview:\n\n" + text)

        # Mark as sent so scheduler will not resend
        await service.mark_sent(item["id"])

        return

    # -----------------------------------------------------

    @router.message(Command("test_like"))
    async def test_like_handler(message: Message):
        """
        Full pipeline test:
        /test_like <liker_id> <liked_id>

        Creates like → detects mutual → inserts match → queues → logs.
        """
        try:
            parts = message.text.split()
            liker_id = int(parts[1])
            liked_id = int(parts[2])
        except:
            return await message.answer("Usage: /test_like <liker> <liked>")

        result = await db.add_like(liker_id, liked_id)

        return await message.answer(
            f"💡 add_like result:\n<code>{result}</code>",
            parse_mode="HTML"
        )

    return router