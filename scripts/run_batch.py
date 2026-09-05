import asyncio
from datetime import datetime, timezone
import random
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.schema import RevenueEvent, EventStatus, RecoveryOutcome, Diagnosis, PolicyDecision, EventType
from app.services.llm_diagnosis import diagnose_event
from app.core.policy_gate import evaluate_policy
from app.services.recovery_executor import execute_recovery
from app.core.logger import logger

async def run_batch():
    async with AsyncSessionLocal() as session:
        # Fetch all open events
        stmt = select(RevenueEvent).where(RevenueEvent.status == EventStatus.open)
        result = await session.execute(stmt)
        open_events = result.scalars().all()
        
        logger.info(f"Starting batch run for {len(open_events)} events...")
        
        for event in open_events:
            logger.info(f"Processing Event ID: {event.id}, Type: {event.type.name}")
            event.status = EventStatus.in_progress
            await session.commit()
            
            # 1. Diagnose
            diagnosis_data = await diagnose_event(event.type, event.amount, event.context)
            diagnosis = Diagnosis(
                event_id=event.id,
                root_cause=diagnosis_data.get("root_cause", "Unknown"),
                recommended_action=diagnosis_data.get("recommended_action", "Escalate"),
                confidence=diagnosis_data.get("confidence", 0.0),
                rationale=diagnosis_data.get("rationale", ""),
                model_used=diagnosis_data.get("model_used", "unknown")
            )
            session.add(diagnosis)
            await session.commit()
            
            # 2. Decide
            decision_data = await evaluate_policy(session, event, diagnosis.recommended_action)
            decision = PolicyDecision(
                event_id=event.id,
                action_proposed=diagnosis.recommended_action,
                action_approved=decision_data["action_approved"],
                rule_triggered=decision_data["rule_triggered"],
                rationale=decision_data["rationale"]
            )
            session.add(decision)
            await session.commit()
            
            # 3. Execute
            if decision.action_approved:
                action = await execute_recovery(session, event, decision.action_proposed)
                if action.outcome == RecoveryOutcome.success:
                    event.status = EventStatus.recovered
                else:
                    event.status = EventStatus.unrecovered
            else:
                # If rejected by policy gate (e.g. spend cap, retry storm), we escalate
                action = await execute_recovery(session, event, "Escalate")
                event.status = EventStatus.escalated
                
            await session.commit()
            
        # Reporting / Metrics
        logger.info("--- BATCH METRICS ---")
        stmt = select(RevenueEvent).options(selectinload(RevenueEvent.recovery_actions))
        result = await session.execute(stmt)
        all_events = result.scalars().all()
        
        total_at_risk = sum(e.amount for e in all_events)
        total_recovered = sum(e.amount for e in all_events if e.status == EventStatus.recovered)
        
        logger.info(f"Total ₹ at risk: {total_at_risk:,.2f}")
        logger.info(f"Total ₹ recovered: {total_recovered:,.2f}")
        logger.info(f"Overall Recovery Rate: {(total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0:.2f}%")
        logger.info("*Note: Recovery-rate figures are simulated using probabilities modeled on cited industry ranges.*")
        
if __name__ == "__main__":
    asyncio.run(run_batch())
