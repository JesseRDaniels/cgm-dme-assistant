"""Claude LLM service."""
from anthropic import AsyncAnthropic
from typing import Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncAnthropic] = None


def get_client() -> AsyncAnthropic:
    """Get or create Anthropic client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def generate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """
    Generate a response using Claude.

    Args:
        system_prompt: System context and instructions
        user_message: User query with any context
        max_tokens: Maximum response length
        temperature: Creativity (0.0-1.0, lower = more focused)

    Returns:
        Generated text response
    """
    settings = get_settings()
    client = get_client()

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude generation failed: {e}")
        raise


async def classify_intent(query: str) -> str:
    """
    Classify the intent of a user query.

    Returns one of: prior_auth, coding, denial, documentation, general
    """
    system = """You are an intent classifier for a CGM DME billing assistant.
Classify the user's query into ONE of these categories:
- prior_auth: Questions about prior authorization, medical necessity, coverage criteria
- coding: Questions about HCPCS codes, modifiers, billing
- denial: Questions about claim denials, appeals, rejection reasons
- documentation: Questions about DWO, SWO, orders, required documents
- general: Other questions about CGM/DME

Respond with ONLY the category name, nothing else."""

    try:
        response = await generate(
            system_prompt=system,
            user_message=query,
            max_tokens=20,
            temperature=0.0,
        )
        intent = response.strip().lower()
        valid_intents = ["prior_auth", "coding", "denial", "documentation", "general"]
        return intent if intent in valid_intents else "general"
    except Exception:
        return "general"
