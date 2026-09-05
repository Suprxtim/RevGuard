from groq import AsyncGroq, GroqError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.logger import logger
from app.core.config import settings

# Initialize Groq client with API key from environment
client = AsyncGroq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are an expert AI Merchant Copilot for a revenue recovery dashboard.
You help merchants understand their payment failure and recovery metrics.

You will be provided with structured JSON context containing the CURRENT aggregates from the database.
You CANNOT query the database yourself. You MUST base your answers ONLY on the provided context.
Be concise, professional, and helpful. Format your response in plain text (short paragraphs or bullet points).

If the user asks something outside the scope of the provided metrics (e.g., specific user details, or actions not supported), politely explain that you only have access to the high-level aggregates provided in your current context.
"""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(GroqError),
    before_sleep=lambda retry_state: logger.warning(f"Retrying Groq API call for Copilot... (Attempt {retry_state.attempt_number})")
)
async def ask_copilot(query: str, metrics_context: dict) -> str:
    """
    Safely answers a merchant's query using pre-computed aggregates as context.
    """
    context_str = f"CURRENT METRICS CONTEXT:\n{metrics_context}\n\nMERCHANT QUESTION:\n{query}"
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": context_str,
                }
            ],
            model="qwen/qwen3.6-27b",
            temperature=0.3, # Slightly creative but grounded
        )
        content = chat_completion.choices[0].message.content
        import re
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        logger.error(f"Copilot LLM API call failed: {e}")
        return "I'm currently unable to process your request due to an AI service error."
