import asyncio
from database import Database
from datetime import date, timedelta

async def main():
    db = Database("crushconnect.db")
    await db.connect()

    # Force rebuild of the cache
    await db.update_leaderboard_cache()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.isoformat()

    # Show cache contents
    async with db._db.execute("SELECT * FROM leaderboard_cache") as cursor:
        rows = await cursor.fetchall()
        print("\nAll rows in leaderboard_cache after update:")
        for r in rows:
            print(dict(r))

    # Show joined leaderboard query
    sql = """
        SELECT u.id, u.name, u.campus, lc.likes_received
        FROM leaderboard_cache lc
        JOIN users u ON lc.user_id = u.id
        WHERE lc.week_start = ?
        ORDER BY lc.likes_received DESC, u.name ASC
        LIMIT 10
    """
    async with db._db.execute(sql, (week_start_str,)) as cursor:
        rows = await cursor.fetchall()
        print("\nJoined leaderboard query:")
        for r in rows:
            print(dict(r))

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
