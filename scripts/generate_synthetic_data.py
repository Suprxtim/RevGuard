import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.schema import Base, RevenueEvent, EventType, EventStatus
from app.core.config import settings
from app.core.logger import logger
from app.core.database import engine, AsyncSessionLocal

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema created.")

async def generate_synthetic_data():
    await init_db()
    
    events = []
    now = datetime.now(timezone.utc)
    
    # 60 Payment Failures
    decline_codes = [
        ("R01", 30), # Insufficient funds (most common)
        ("R04", 20), # Network timeout (most common)
        ("R02", 8),  # Card expired
        ("R03", 2)   # Fraud suspected (rare)
    ]
    
    for code, count in decline_codes:
        for _ in range(count):
            user_id = f"usr_{uuid.uuid4().hex[:8]}"
            amount = round(random.uniform(500.0, 5000.0), 2)
            detected_at = now - timedelta(hours=random.randint(1, 48))
            
            event = RevenueEvent(
                type=EventType.payment_failure,
                user_id=user_id,
                amount=amount,
                context={"decline_code": code},
                detected_at=detected_at,
                status=EventStatus.open
            )
            events.append(event)
            
    # 15 Checkout Abandonments
    # Mix of high/low cart values, old/recent abandonments
    abandonment_profiles = [
        (True, True, 5),   # High value, recent
        (True, False, 5),  # High value, old
        (False, True, 2),  # Low value, recent
        (False, False, 3)  # Low value, old
    ]
    
    for high_value, recent, count in abandonment_profiles:
        for _ in range(count):
            user_id = f"usr_{uuid.uuid4().hex[:8]}"
            amount = round(random.uniform(10000.0, 50000.0), 2) if high_value else round(random.uniform(100.0, 400.0), 2)
            hours_ago = random.randint(1, 12) if recent else random.randint(48, 168)
            detected_at = now - timedelta(hours=hours_ago)
            
            event = RevenueEvent(
                type=EventType.checkout_abandonment,
                user_id=user_id,
                amount=amount,
                context={
                    "cart_items": random.randint(1, 5),
                    "time_since_abandonment_hours": hours_ago
                },
                detected_at=detected_at,
                status=EventStatus.open
            )
            events.append(event)
            
    # Shuffle events
    random.shuffle(events)
    
    async with AsyncSessionLocal() as session:
        session.add_all(events)
        await session.commit()
        
    logger.info(f"Generated and inserted {len(events)} synthetic events.")

if __name__ == "__main__":
    asyncio.run(generate_synthetic_data())
