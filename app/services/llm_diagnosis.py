import json
import os
from groq import AsyncGroq, GroqError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.models.schema import EventType
from app.core.logger import logger
from app.core.config import settings

# Initialize Groq client with API key from environment
# The API key is loaded automatically from GROQ_API_KEY env var
client = AsyncGroq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are an expert revenue recovery AI diagnostic agent.
Your task is to provide a brief, plain-language rationale explaining a revenue recovery decision.
You MUST respond with a valid JSON object matching this exact schema:
{
    "rationale": "Brief plain-language explanation of why this action was taken for this root cause."
}

Only output the JSON object. Do not include markdown formatting or extra text.
"""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(GroqError),
    before_sleep=lambda retry_state: logger.warning(f"Retrying Groq API call... (Attempt {retry_state.attempt_number})")
)
async def _call_groq_api(event_description: str) -> str:
    chat_completion = await client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": event_description,
            }
        ],
        model="llama-3.1-8b-instant", # Using a fast, valid Groq model
        temperature=0.0, # Deterministic output
        response_format={"type": "json_object"},
    )
    return chat_completion.choices[0].message.content

async def diagnose_event(event_type: EventType, amount: float, context: dict) -> dict:
    """
    Deterministically diagnoses the event based on the PRD taxonomy and calls the LLM for rationale.
    """
    if event_type == EventType.payment_failure:
        decline_code = context.get("decline_code", "")
        if decline_code == "R01":
            root_cause = "Insufficient funds"
            recommended_action = "Retry"
        elif decline_code == "R04":
            root_cause = "Network timeout"
            recommended_action = "Retry"
        elif decline_code == "R02":
            root_cause = "Card expired"
            recommended_action = "Nudge"
        elif decline_code == "R03":
            root_cause = "Fraud suspected"
            recommended_action = "Block + escalate"
        else:
            root_cause = "Unknown decline code"
            recommended_action = "Escalate"
    elif event_type.name == "checkout_abandonment":
        hours_since = context.get("hours_since_abandonment", 48)
        if amount > 2000 and hours_since <= 24:
            root_cause = "Likely price/hesitation"
            recommended_action = "Nudge"
        else:
            root_cause = "Low recovery likelihood"
            recommended_action = "Escalate"
    elif event_type.name == "b2b_overdue_invoice":
        root_cause = "Delayed B2B payment"
        recommended_action = "Nudge"
    else:
        root_cause = "Unknown event type"
        recommended_action = "Escalate"
        
    event_description = f"Event Type: {event_type.value}\nAmount: {amount}\nRoot Cause: {root_cause}\nRecommended Action: {recommended_action}"
    
    try:
        response_content = await _call_groq_api(event_description)
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        fallback_rationale = f"Based on the event context, the issue appears to be related to {root_cause.lower()}. My deterministic policy suggests that we should {recommended_action.lower()} to recover the revenue securely."
        return {
            "root_cause": root_cause,
            "recommended_action": recommended_action,
            "confidence": 0.85,
            "rationale": fallback_rationale,
            "model_used": "fallback-heuristic"
        }
    
    try:
        diagnosis_data = json.loads(response_content)
        return {
            "root_cause": root_cause,
            "recommended_action": recommended_action,
            "confidence": 1.0,
            "rationale": diagnosis_data.get("rationale", "No rationale provided by LLM."),
            "model_used": "llama-3.1-8b-instant"
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Groq: {e}\nContent: {response_content}")
        return {
            "root_cause": root_cause,
            "recommended_action": recommended_action,
            "confidence": 1.0,
            "rationale": "LLM output failed to parse as JSON.",
            "model_used": "llama-3.1-8b-instant"
        }
