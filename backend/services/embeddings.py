"""Embedding service using Voyage AI (Anthropic's embedding model)."""
import httpx
from typing import Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"


async def get_embedding(text: str) -> list[float]:
    """
    Get embedding for a single text using Voyage AI.

    Uses voyage-3-lite model (1024 dimensions).
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                VOYAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": text,
                    "input_type": "document",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Get embeddings for multiple texts.

    Voyage supports batch embedding up to 128 texts.
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                VOYAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": texts,
                    "input_type": "document",
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise


async def get_query_embedding(text: str) -> list[float]:
    """
    Get embedding for a query (uses input_type='query' for better retrieval).
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                VOYAGE_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": text,
                    "input_type": "query",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            raise
