from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
import random
import uuid
import asyncio

from app.core.database import get_db, engine, Base
from app.models.schema import RevenueEvent, EventType, EventStatus, RecoveryAction, RecoveryActionType, RecoveryOutcome, Diagnosis, PolicyDecision
from app.services.llm_diagnosis import diagnose_event
from app.core.policy_gate import evaluate_policy
from app.services.recovery_executor import execute_recovery
from app.services.llm_copilot import ask_copilot
from app.core.logger import logger
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from app.core.events import broadcaster

router = APIRouter(prefix="/admin", tags=["Admin"])

from sqlalchemy import text

@router.post("/reset-demo")
async def reset_demo():
    """Clears all data to reset the demo instantly, avoiding slow table drops over network."""
    try:
        async with engine.begin() as conn:
            # Truncate in the same order as locks are acquired to minimize deadlock risk
            await conn.execute(text("TRUNCATE TABLE revenue_event, diagnosis, policy_decision, recovery_action CASCADE;"))
        logger.info("Database records cleared.")
        await broadcaster.broadcast("reload")
        return {"message": "Demo data reset successfully."}
    except Exception as e:
        logger.error(f"Failed to reset demo: {e}")
        return {"message": "Error: Could not reset demo. A background process is likely locking the tables. Please wait for processing to finish and try again."}

@router.post("/simulate/batch")
async def simulate_batch(db: AsyncSession = Depends(get_db)):
    """Generates a deterministic batch of synthetic payment failures."""
    events = []
    now = datetime.now(timezone.utc)
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    
    decline_codes = [
        ("R01", 30), # Insufficient funds
        ("R04", 20), # Network timeout
        ("R02", 8),  # Card expired
        ("R03", 2)   # Fraud suspected
    ]
    
    for code, count in decline_codes:
        for _ in range(count):
            user_id = f"usr_{uuid.uuid4().hex[:8]}"
            amount = round(random.uniform(500.0, 5000.0), 2)
            detected_at = now - timedelta(hours=random.randint(1, 48))
            
            event = RevenueEvent(
                batch_id=batch_id,
                type=EventType.payment_failure,
                user_id=user_id,
                amount=amount,
                context={"decline_code": code},
                detected_at=detected_at,
                status=EventStatus.open
            )
            events.append(event)
            
    # Generate Checkout Abandonment Events (~15 total)
    abandonment_scenarios = [
        {"count": 8, "high_value": True, "recent": True},
        {"count": 4, "high_value": False, "recent": True},
        {"count": 2, "high_value": True, "recent": False},
        {"count": 1, "high_value": False, "recent": False}
    ]
    
    for scenario in abandonment_scenarios:
        for _ in range(scenario["count"]):
            user_id = f"usr_{uuid.uuid4().hex[:8]}"
            
            if scenario["high_value"]:
                amount = round(random.uniform(2500.0, 8000.0), 2)
            else:
                amount = round(random.uniform(100.0, 1500.0), 2)
                
            if scenario["recent"]:
                hours_ago = random.randint(1, 12)
            else:
                hours_ago = random.randint(30, 48)
                
            detected_at = now - timedelta(hours=hours_ago)
            
            event = RevenueEvent(
                batch_id=batch_id,
                type=EventType.checkout_abandonment,
                user_id=user_id,
                amount=amount,
                context={"hours_since_abandonment": hours_ago, "cart_items": ["synthetic_item"]},
                detected_at=detected_at,
                status=EventStatus.open
            )
            events.append(event)
            
    random.shuffle(events)
    db.add_all(events)
    await db.commit()
    logger.info(f"Generated batch {batch_id} with {len(events)} events.")
    await broadcaster.broadcast("reload")
    return {"message": f"Generated batch {batch_id} with {len(events)} events."}

@router.post("/simulate/retry-storm")
async def simulate_retry_storm(db: AsyncSession = Depends(get_db)):
    """Injects an open event with 15 previous failed retries to simulate a retry storm."""
    user_id = f"storm_usr_{uuid.uuid4().hex[:8]}"
    from datetime import timedelta
    
    event = RevenueEvent(
        type=EventType.payment_failure,
        user_id=user_id,
        amount=1500.00,
        context={"decline_code": "R04"},
        detected_at=datetime.now(timezone.utc),
        status=EventStatus.open,
        batch_id="storm_batch"
    )
    db.add(event)
    await db.flush()
    
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
    db.add_all(actions)
    await db.commit()
    
    await broadcaster.broadcast("reload")
    return {"message": "Retry Storm simulated. Click Process Pending!"}

@router.post("/simulate/b2b-invoice")
async def simulate_b2b_invoice(db: AsyncSession = Depends(get_db)):
    """Injects an open B2B overdue invoice event for the B2B stretch goal."""
    user_id = f"acme_corp_{uuid.uuid4().hex[:4]}"
    
    event = RevenueEvent(
        type=EventType.b2b_overdue_invoice,
        user_id=user_id,
        amount=5500.00,
        context={"decline_code": "NET30_OVERDUE", "client": "Acme Corp"},
        detected_at=datetime.now(timezone.utc),
        status=EventStatus.open,
        batch_id="b2b_batch"
    )
    db.add(event)
    await db.commit()
    
    await broadcaster.broadcast("reload")
    return {"message": "B2B Overdue Invoice simulated. Click Process Pending!"}

async def process_single_event(event_id: int):
    from app.core.database import AsyncSessionLocal
    import hashlib
    from sqlalchemy import text
    
    # 1. Fetch and Lock Event
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(RevenueEvent).where(
                RevenueEvent.id == event_id,
                RevenueEvent.status == EventStatus.open
            ).with_for_update(skip_locked=True)
            result = await session.execute(stmt)
            event = result.scalars().first()
            
            if not event:
                return # Already processed or locked
                
            event.status = EventStatus.in_progress
            await session.commit()
            
            # 2. Diagnose (Network I/O - Concurrent and unblocked)
            diagnosis_data = await diagnose_event(event.type, event.amount, event.context)
            diagnosis = Diagnosis(
                event_id=event.id,
                root_cause=diagnosis_data.get("root_cause", "Unknown"),
                recommended_action=diagnosis_data.get("recommended_action", "Escalate"),
                confidence=diagnosis_data.get("confidence", 0.0),
                rationale=diagnosis_data.get("rationale", ""),
                model_used=diagnosis_data.get("model_used", "unknown")
            )
            
            # We must hold onto user_id for the next block
            user_id = event.user_id
            
        except Exception as e:
            logger.error(f"Error locking/diagnosing event {event_id}: {e}")
            await session.rollback()
            return
            
    # 3. Policy Gate + Execute (Strictly serialized per user)
    async with AsyncSessionLocal() as session:
        try:
            # Acquire Postgres Advisory Lock per user FIRST to establish the Repeatable Read snapshot AFTER acquiring the lock!
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % (2**63 - 1)
            await session.execute(text(f"SELECT pg_advisory_xact_lock({user_hash})"))
            
            # Re-fetch event to attach to this session
            event = await session.get(RevenueEvent, event_id)
            if not event:
                return
            
            session.add(diagnosis)
            
            decision_data = await evaluate_policy(session, event, diagnosis.recommended_action)
            decision = PolicyDecision(
                event_id=event.id,
                action_proposed=diagnosis.recommended_action,
                action_approved=decision_data["action_approved"],
                rule_triggered=decision_data["rule_triggered"],
                rationale=decision_data["rationale"]
            )
            session.add(decision)
            
            if decision.action_approved:
                action = await execute_recovery(session, event, decision.action_proposed)
                if action.outcome == RecoveryOutcome.success:
                    event.status = EventStatus.recovered
                else:
                    event.status = EventStatus.unrecovered
            else:
                action = await execute_recovery(session, event, "Escalate")
                event.status = EventStatus.escalated
                
            await session.commit()
            await broadcaster.broadcast(f"processed:{event_id}")
        except Exception as e:
            logger.error(f"Error in policy/execute for event {event_id}: {e}")
            await session.rollback()
            # Attempt to revert status
            try:
                event = await session.get(RevenueEvent, event_id)
                if event:
                    event.status = EventStatus.open
                    await session.commit()
            except Exception as inner_e:
                logger.error(f"Failed to revert event {event_id} status: {inner_e}")

async def process_batch_background(batch_id: str = None):
    """Background task to process events deterministically and concurrently."""
    from app.core.database import AsyncSessionLocal
    import asyncio
    
    # First, get the list of event IDs to process
    async with AsyncSessionLocal() as session:
        stmt = select(RevenueEvent.id).where(RevenueEvent.status == EventStatus.open)
        if batch_id:
            stmt = stmt.where(RevenueEvent.batch_id == batch_id)
        result = await session.execute(stmt)
        event_ids = result.scalars().all()
        
    logger.info(f"Starting concurrent batch process for {len(event_ids)} events...")
    
    # Concurrency limit to prevent overwhelming API or DB connection pool
    sem = asyncio.Semaphore(10)
    
    async def sem_process(e_id):
        async with sem:
            await process_single_event(e_id)
            
    tasks = [sem_process(e_id) for e_id in event_ids]
    await asyncio.gather(*tasks)

@router.post("/process")
async def process_events(background_tasks: BackgroundTasks):
    """Triggers the processing of all open events in the background."""
    background_tasks.add_task(process_batch_background)
    await broadcaster.broadcast("reload")
    return {"message": "Batch processing started in the background."}

@router.post("/trigger-retry-storm")
async def trigger_retry_storm(db: AsyncSession = Depends(get_db)):
    """Deterministically simulates a retry storm scenario."""
    user_id = "usr_retry_storm_test"
    now = datetime.now(timezone.utc)
    batch_id = "batch_storm"
    
    # Create the event
    event = RevenueEvent(
        batch_id=batch_id,
        type=EventType.payment_failure,
        user_id=user_id,
        amount=1500.00,
        context={"decline_code": "R04"}, # Network timeout (allows retries)
        detected_at=now,
        status=EventStatus.open
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Inject 10 historical failed retry attempts within the last hour for this user
    for i in range(10):
        old_event = RevenueEvent(
            batch_id=batch_id,
            type=EventType.payment_failure,
            user_id=user_id,
            amount=1500.00,
            context={"decline_code": "R04"},
            detected_at=now - timedelta(minutes=50),
            status=EventStatus.unrecovered
        )
        db.add(old_event)
        await db.commit()
        await db.refresh(old_event)
        
        action = RecoveryAction(
            event_id=old_event.id,
            action_type=RecoveryActionType.retry,
            executed_at=now - timedelta(minutes=45) + timedelta(seconds=i),
            outcome=RecoveryOutcome.failure,
            attempt_number=1
        )
        db.add(action)
    
    await db.commit()
    await broadcaster.broadcast("reload")
    return {"message": "Retry storm scenario seeded. Run /admin/process to see the policy gate reject the 11th retry."}

class CopilotRequest(BaseModel):
    query: str

@router.post("/copilot")
async def copilot_query(req: CopilotRequest, db: AsyncSession = Depends(get_db)):
    """Handles merchant queries using pre-computed aggregates safely."""
    from sqlalchemy import func
    # Compute aggregates
    stmt = select(
        func.count(RevenueEvent.id).label('total_events'),
        func.sum(RevenueEvent.amount).label('total_at_risk'),
        func.sum(RevenueEvent.amount).filter(RevenueEvent.status == EventStatus.recovered).label('total_recovered'),
        func.sum(RevenueEvent.amount).filter(RevenueEvent.status == EventStatus.unrecovered).label('total_lost'),
        func.count(RevenueEvent.id).filter(RevenueEvent.status == EventStatus.open).label('open_events')
    )
    result = await db.execute(stmt)
    row = result.fetchone()
    
    total_events = row.total_events or 0
    total_at_risk = float(row.total_at_risk or 0)
    total_recovered = float(row.total_recovered or 0)
    total_lost = float(row.total_lost or 0)
    open_events = row.open_events or 0
    
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0
    
    metrics = {
        "total_events": total_events,
        "total_at_risk_rupees": total_at_risk,
        "total_recovered_rupees": total_recovered,
        "total_lost_rupees": total_lost,
        "recovery_rate_percentage": round(recovery_rate, 2),
        "open_events": open_events
    }
    
    answer = await ask_copilot(req.query, metrics)
    return {"answer": answer}

@router.get("/stream")
async def sse_stream(request: Request):
    """Server-Sent Events endpoint for real-time dashboard updates."""
    async def event_generator():
        q = asyncio.Queue()
        broadcaster.add_queue(q)
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Wait for the next message with a timeout to check disconnection
                try:
                    message = await asyncio.wait_for(q.get(), timeout=2.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.remove_queue(q)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
