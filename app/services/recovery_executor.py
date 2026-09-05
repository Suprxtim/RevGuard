import razorpay
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.schema import RevenueEvent, RecoveryAction, RecoveryActionType, RecoveryOutcome
from app.core.config import settings

# Initialize Razorpay Client (only if keys exist, else mock)
if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
    rzp_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
else:
    rzp_client = None

async def execute_recovery(session: AsyncSession, event: RevenueEvent, action_type_str: str) -> RecoveryAction:
    """
    Executes the approved recovery action.
    """
    # Map the string action to Enum
    if "Retry" in action_type_str:
        action_type = RecoveryActionType.retry
    elif "Nudge" in action_type_str:
        action_type = RecoveryActionType.nudge
    elif "Block" in action_type_str or "Escalate" in action_type_str or "Log only" in action_type_str:
        action_type = RecoveryActionType.escalate
    else:
        action_type = RecoveryActionType.escalate # Default fallback
        
    # Idempotency check: Is there already a pending action of this type for this event?
    stmt = select(RecoveryAction).where(
        RecoveryAction.event_id == event.id,
        RecoveryAction.action_type == action_type,
        RecoveryAction.outcome == RecoveryOutcome.pending
    )
    existing_action = await session.scalar(stmt)
    if existing_action:
        return existing_action
        
    # Calculate attempt number
    stmt = select(func.max(RecoveryAction.attempt_number)).where(
        RecoveryAction.event_id == event.id,
        RecoveryAction.action_type == action_type
    )
    max_attempt = await session.scalar(stmt)
    current_attempt = (max_attempt or 0) + 1
        
    action_record = RecoveryAction(
        event_id=event.id,
        action_type=action_type,
        executed_at=datetime.now(timezone.utc),
        outcome=RecoveryOutcome.pending,
        attempt_number=current_attempt
    )
    
    session.add(action_record)
    await session.commit()
    await session.refresh(action_record)
    
    # Execution Logic
    if action_type == RecoveryActionType.retry:
        # Call Razorpay API
        try:
            if rzp_client:
                # In a real scenario, this would be a specific retry or recurring mandate endpoint
                # Since the PRD requests test-mode payment retry, we simulate the network call 
                # using the SDK. We wrap it in a thread if it's synchronous.
                # rzp_client.payment.capture(payment_id, amount)
                pass 
            
            # Simulated async network delay
            await asyncio.sleep(0.5) 
            
            # Simulated probability modeled on PRD (e.g., R04 ~85%, R01 ~75%)
            import random
            decline_code = event.context.get("decline_code", "")
            success_prob = 0.85 if decline_code == "R04" else 0.75
            
            if random.random() <= success_prob:
                action_record.outcome = RecoveryOutcome.success
            else:
                action_record.outcome = RecoveryOutcome.failure
                
        except Exception as e:
            action_record.outcome = RecoveryOutcome.failure

    elif action_type == RecoveryActionType.nudge:
        # Generate Hinglish SMS/Email copy via LLM
        from app.services.llm_diagnosis import client
        import json
        
        try:
            # Customize prompt based on event type
            if event.type.name == "b2b_overdue_invoice":
                system_instruction = "You are a professional B2B assistant. You must respond with a valid JSON object matching this exact schema:\n{\n  \"reasoning\": \"Your step-by-step thinking process\",\n  \"message\": \"The final 2-sentence email\"\n}"
                prompt = f"Write a professional, polite 2-sentence email follow-up to a client for an overdue B2B invoice of ₹{event.amount}. Include a call to action to pay."
                channel = "Email"
            else:
                system_instruction = "You are an SMS copywriter. You must respond with a valid JSON object matching this exact schema:\n{\n  \"reasoning\": \"Your step-by-step thinking process\",\n  \"message\": \"The final 1-sentence SMS\"\n}"
                prompt = f"Write a friendly 1-sentence SMS in conversational Hinglish (Hindi + English) to recover an abandoned checkout of ₹{event.amount}. Include a call to action."
                channel = "SMS"
                
            completion = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=250,
                response_format={"type": "json_object"}
            )
            
            raw_response = completion.choices[0].message.content
            try:
                data = json.loads(raw_response)
                message = data.get("message", "")
            except json.JSONDecodeError:
                message = raw_response # Fallback if somehow not JSON
                
            action_record.context = {"generated_message": message, "channel": channel}
            action_record.outcome = RecoveryOutcome.success
        except Exception as e:
            from app.core.logger import logger
            logger.error(f"Failed to generate LLM copy: {e}")
            action_record.context = {"error": str(e), "generated_message": f"System fallback: Please complete your payment of ₹{event.amount}."}
            action_record.outcome = RecoveryOutcome.success # Fallback succeeds
        
    elif action_type == RecoveryActionType.escalate:
        # Simulated escalation via structured logs
        await asyncio.sleep(0.1)
        action_record.outcome = RecoveryOutcome.success
        
        # Save the Sale: Simulated Conversational Transcript
        decline_code = event.context.get("decline_code", "")
        if decline_code == "R01":
            action_record.context = {
                "transcript": [
                    {"role": "bot", "content": f"Hi, your payment of ₹{event.amount} failed due to insufficient funds. Would you like to split this into 3 easy EMIs using Razorpay?"},
                    {"role": "user", "content": "Yes, please send the link."},
                    {"role": "bot", "content": "Here is your Razorpay Payment Link for EMI setup: https://rzp.io/i/simulated"}
                ]
            }
        
    await session.commit()
    return action_record
