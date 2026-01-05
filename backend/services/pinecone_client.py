"""Pinecone vector database client."""
from pinecone import Pinecone, ServerlessSpec
from typing import Optional
import logging

from config import get_settings

logger = logging.getLogger(__name__)

# Global client instance
_pc: Optional[Pinecone] = None
_index = None


async def init_pinecone():
    """Initialize Pinecone client and index."""
    global _pc, _index

    settings = get_settings()

    if not settings.pinecone_api_key:
        logger.warning("Pinecone API key not set - vector search disabled")
        return

    try:
        _pc = Pinecone(api_key=settings.pinecone_api_key)

        # Check if index exists
        existing_indexes = [idx.name for idx in _pc.list_indexes()]

        if settings.pinecone_index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
            _pc.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.embedding_dimensions,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        _index = _pc.Index(settings.pinecone_index_name)
        logger.info(f"Connected to Pinecone index: {settings.pinecone_index_name}")

    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        raise


def get_index():
    """Get the Pinecone index instance."""
    if _index is None:
        raise RuntimeError("Pinecone not initialized. Call init_pinecone() first.")
    return _index


async def upsert_vectors(
    vectors: list[dict],
    namespace: str = "default",
):
    """
    Upsert vectors to Pinecone.

    vectors: List of dicts with id, values, metadata
    """
    index = get_index()
    index.upsert(vectors=vectors, namespace=namespace)


async def query_vectors(
    query_vector: list[float],
    top_k: int = 5,
    namespace: str = "default",
    filter: Optional[dict] = None,
) -> list[dict]:
    """
    Query Pinecone for similar vectors.

    Returns list of matches with id, score, metadata.
    """
    index = get_index()

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        namespace=namespace,
        filter=filter,
        include_metadata=True,
    )

    return [
        {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata,
        }
        for match in results.matches
    ]


async def delete_namespace(namespace: str):
    """Delete all vectors in a namespace."""
    index = get_index()
    index.delete(delete_all=True, namespace=namespace)


async def delete_vectors(ids: list[str], namespace: str = "default"):
    """Delete specific vectors by ID."""
    index = get_index()
    index.delete(ids=ids, namespace=namespace)
