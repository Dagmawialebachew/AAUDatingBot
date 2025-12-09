# test.py
import asyncio
import logging
from dotenv import load_dotenv
import os

from database import Database  # assuming your class is in database.py

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    # Load environment variables
    load_dotenv()
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise ValueError("POSTGRES_DSN not set in .env file")

    # Initialize database
    db = Database(dsn=dsn)
    await db.connect()

    # Run a simple test query
    try:
        row = await db._db.fetchrow("SELECT NOW() as current_time")
        print("Connection successful!")
        print("Current time from DB:", row["current_time"])
    except Exception as e:
        print("Query failed:", e)

    # Close connection
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
