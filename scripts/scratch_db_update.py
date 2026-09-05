import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://") if settings.DATABASE_URL.startswith("postgresql://") else settings.DATABASE_URL

async def main():
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TYPE eventtype ADD VALUE 'checkout_abandonment'"))
            print("Successfully added checkout_abandonment to eventtype enum.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

asyncio.run(main())
