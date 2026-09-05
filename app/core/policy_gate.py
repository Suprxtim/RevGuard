from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from app.models.schema import RevenueEvent, RecoveryAction, RecoveryActionType, EventType

async def evaluate_policy(session: AsyncSession, event: RevenueEvent, proposed_action: str) -> dict:
    """
    Evaluates the proposed action against the 5 strict policy rules.
    Returns a dict with 'action_approved', 'rule_triggered', and 'rationale'.
    """
    # Rule 1: Max retry cap (<= 3 attempts)
    if "Retry" in proposed_action:
        stmt = select(func.count(RecoveryAction.id)).where(
            RecoveryAction.event_id == event.id,
            RecoveryAction.action_type == RecoveryActionType.retry
        )
        retry_count = await session.scalar(stmt)
        if retry_count >= 3:
            return {
                "action_approved": False,
                "rule_triggered": "max_retry_cap",
                "rationale": f"Maximum retry cap of 3 attempts reached for event {event.id}."
            }

    # Rule 3: Retry-storm check (> 10 retries in 1 hour for the user)
    # The graceful failure scenario
    if "Retry" in proposed_action:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = select(func.count(RecoveryAction.id)).join(RevenueEvent).where(
            RevenueEvent.user_id == event.user_id,
            RecoveryAction.action_type == RecoveryActionType.retry,
            RecoveryAction.executed_at >= one_hour_ago
        )
        storm_count = await session.scalar(stmt)
        if storm_count >= 10:
            return {
                "action_approved": False,
                "rule_triggered": "retry_storm_check",
                "rationale": f"Retry storm detected: {storm_count} retries in the last hour for user {event.user_id}. Pausing all retries and escalating."
            }

    # Rule 4: Spend/exposure cap (value <= 5000)
    # If the event amount exceeds 5000, we do not auto-action, but escalate.
    if event.amount > 5000:
        if "Nudge" not in proposed_action: # Allowing nudges for high value abandoned carts
            return {
                "action_approved": False,
                "rule_triggered": "spend_exposure_cap",
                "rationale": f"Event amount ({event.amount}) exceeds the ₹5,000 auto-recovery cap. Escalating for manual review."
            }

    # Rule 2: Idempotency check
    # Handled practically by checking if the exact action was already approved and pending execution
    # This check prevents duplicate execution of the same action in quick succession.
    stmt = select(func.count(RecoveryAction.id)).where(
        RecoveryAction.event_id == event.id,
        RecoveryAction.outcome == 'pending'
    )
    pending_actions = await session.scalar(stmt)
    if pending_actions > 0:
        return {
            "action_approved": False,
            "rule_triggered": "idempotency_check",
            "rationale": "An action is already pending execution for this event."
        }

    # Rule 5: Nudge Cooldown check (no more than 1 nudge per 24 hours per user)
    if "Nudge" in proposed_action:
        one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt = select(func.count(RecoveryAction.id)).join(RevenueEvent).where(
            RevenueEvent.user_id == event.user_id,
            RecoveryAction.action_type == RecoveryActionType.nudge,
            RecoveryAction.executed_at >= one_day_ago
        )
        nudge_count = await session.scalar(stmt)
        if nudge_count >= 1:
            return {
                "action_approved": False,
                "rule_triggered": "nudge_cooldown",
                "rationale": f"Nudge cooldown active: User {event.user_id} was already nudged in the last 24 hours."
            }

    # If all rules pass
    return {
        "action_approved": True,
        "rule_triggered": "all_rules_passed",
        "rationale": "The proposed action passed all policy gates successfully."
    }
