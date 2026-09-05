from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.schema import RevenueEvent, EventStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/audit")
async def audit_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    
    # Calculate Metrics first via DB
    metrics_stmt = select(
        func.sum(RevenueEvent.amount).label('total_at_risk'),
        func.sum(RevenueEvent.amount).filter(RevenueEvent.status == EventStatus.recovered).label('total_recovered')
    )
    metrics_result = await db.execute(metrics_stmt)
    metrics_row = metrics_result.fetchone()
    
    total_at_risk = float(metrics_row.total_at_risk or 0)
    total_recovered = float(metrics_row.total_recovered or 0)
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0

    # Fetch recent events with their related data (limited to 100 to prevent OOM)
    stmt = select(RevenueEvent).options(
        selectinload(RevenueEvent.diagnosis),
        selectinload(RevenueEvent.policy_decisions),
        selectinload(RevenueEvent.recovery_actions)
    ).order_by(RevenueEvent.detected_at.desc()).limit(100)
    
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    # Serialize events for the JS slide-out panel
    events_json = []
    for event in events:
        events_json.append({
            "id": event.id,
            "type": event.type.name,
            "amount": float(event.amount),
            "status": event.status.name,
            "decline_code": event.context.get("decline_code", "N/A"),
            "diagnosis": {
                "root_cause": event.diagnosis.root_cause,
                "rationale": event.diagnosis.rationale
            } if event.diagnosis else None,
            "policy": {
                "action_approved": event.policy_decisions[0].action_approved,
                "rule_triggered": event.policy_decisions[0].rule_triggered,
                "rationale": event.policy_decisions[0].rationale
            } if event.policy_decisions else None,
            "actions": [{
                "type": a.action_type.name,
                "outcome": a.outcome.name,
                "generated_message": a.context.get("generated_message", ""),
                "channel": a.context.get("channel", "")
            } for a in event.recovery_actions]
        })

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "events": events,
            "events_json": events_json,
            "total_at_risk": total_at_risk,
            "total_recovered": total_recovered,
            "recovery_rate": recovery_rate,
            "is_simulated": True
        }
    )
