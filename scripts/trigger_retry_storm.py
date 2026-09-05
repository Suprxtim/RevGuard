import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, engine
from app.models.schema import RevenueEvent, EventType, EventStatus, RecoveryAction, RecoveryActionType, RecoveryOutcome
from app.core.policy_gate import evaluate_policy
from app.core.logger import logger

async def trigger_retry_storm():
    """
    Demonstrates the graceful failure scenario where a retry storm is detected.
    """
    user_id = f"storm_usr_{uuid.uuid4().hex[:8]}"
    
    async with AsyncSessionLocal() as session:
        # Create a new event
        event = RevenueEvent(
            type=EventType.payment_failure,
            user_id=user_id,
            amount=1500.00,
            context={"decline_code": "R04"},
            detected_at=datetime.now(timezone.utc),
            status=EventStatus.open
        )
        session.add(event)
        await session.flush()
        
        # Inject 15 previous retry attempts for this user within the last hour
        now = datetime.now(timezone.utc)
        actions = []
        for i in range(15):
            actions.append(RecoveryAction(
                event_id=event.id,
                action_type=RecoveryActionType.retry,
                executed_at=now - timedelta(minutes=random.randint(1, 50)),
                outcome=RecoveryOutcome.failure,
                attempt_number=i+1
            ))
        session.add_all(actions)
        await session.commit()
        
        logger.info(f"Injected 15 failed retries for user {user_id}")
        
        # Now, evaluate policy for a new proposed retry
        decision = await evaluate_policy(session, event, "Retry immediately")
        
        logger.info("--- POLICY DECISION ---")
        logger.info(f"Action Approved: {decision['action_approved']}")
        logger.info(f"Rule Triggered: {decision['rule_triggered']}")
        logger.info(f"Rationale: {decision['rationale']}")
        
        if decision["rule_triggered"] == "retry_storm_check":
            logger.info("SUCCESS: Graceful failure scenario triggered correctly.")
        else:
            logger.error("FAILED: Did not trigger retry storm check.")

if __name__ == "__main__":
    import random
    asyncio.run(trigger_retry_storm())
