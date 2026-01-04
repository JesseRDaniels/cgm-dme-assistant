"""Embedding service using OpenAI."""
from openai import AsyncOpenAI
from typing import Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def get_embedding(text: str) -> list[float]:
    """
    Get embedding for a single text.

    Uses OpenAI text-embedding-3-small model.
    """
    settings = get_settings()
    client = get_client()

    try:
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Get embeddings for multiple texts.

    Batches requests for efficiency.
    """
    settings = get_settings()
    client = get_client()

    try:
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        raise
