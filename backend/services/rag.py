"""RAG pipeline for CGM DME queries."""
from typing import Optional
import logging

from services.embeddings import get_embedding
from services.pinecone_client import query_vectors
from services.llm import generate, classify_intent
from services.models import ChatResponse, Citation, RetrievedChunk
from prompts.system import get_system_prompt
from config import get_settings

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    query: str,
    intent: str,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Retrieve relevant chunks from Pinecone based on query.

    Filters by namespace based on intent for better results.
    """
    settings = get_settings()

    # Get query embedding
    query_embedding = await get_embedding(query)

    # Map intent to namespace(s)
    namespace_map = {
        "prior_auth": "lcd_policies",
        "coding": "hcpcs_codes",
        "denial": "denial_reasons",
        "documentation": "documentation_reqs",
        "general": "default",
    }
    namespace = namespace_map.get(intent, "default")

    try:
        # Query Pinecone
        results = await query_vectors(
            query_vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
        )

        chunks = []
        for result in results:
            chunks.append(
                RetrievedChunk(
                    id=result["id"],
                    text=result["metadata"].get("text", ""),
                    metadata=result["metadata"],
                    score=result["score"],
                )
            )

        return chunks

    except Exception as e:
        logger.warning(f"Retrieval failed, returning empty: {e}")
        return []


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Build context string from retrieved chunks."""
    if not chunks:
        return ""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.metadata.get("source", "Unknown")
        section = chunk.metadata.get("section", "")
        source_info = f"{source}"
        if section:
            source_info += f" - {section}"

        context_parts.append(f"[{i}] {source_info}:\n{chunk.text}\n")

    return "\n".join(context_parts)


def extract_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Extract citations from retrieved chunks."""
    citations = []
    for chunk in chunks:
        citations.append(
            Citation(
                source=chunk.metadata.get("source", "Unknown"),
                section=chunk.metadata.get("section"),
                text=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                relevance_score=chunk.score,
            )
        )
    return citations


async def query_assistant(
    query: str,
    context: Optional[dict] = None,
) -> ChatResponse:
    """
    Main RAG query pipeline.

    1. Classify intent
    2. Retrieve relevant chunks
    3. Build prompt with context
    4. Generate response with Claude
    5. Return with citations
    """
    settings = get_settings()

    # Classify query intent
    intent = await classify_intent(query)
    logger.info(f"Query intent: {intent}")

    # Retrieve relevant chunks
    chunks = await retrieve_chunks(query, intent, top_k=settings.retrieval_top_k)

    # Build context from chunks
    rag_context = build_context(chunks)

    # Add any user-provided context (patient info, etc.)
    user_context = ""
    if context:
        user_context = "\n\nAdditional context provided:\n"
        for key, value in context.items():
            user_context += f"- {key}: {value}\n"

    # Build the full prompt
    system_prompt = get_system_prompt(intent)

    user_message = query
    if rag_context:
        user_message = f"""Reference Information:
{rag_context}
{user_context}
---

User Question: {query}

Please answer based on the reference information above. Cite sources using [1], [2], etc."""

    # Generate response
    answer = await generate(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
    )

    # Extract citations
    citations = extract_citations(chunks)

    # Calculate confidence based on retrieval scores
    avg_score = sum(c.score for c in chunks) / len(chunks) if chunks else 0.5
    confidence = min(avg_score * 1.2, 1.0)  # Scale up slightly, cap at 1.0

    return ChatResponse(
        answer=answer,
        citations=citations,
        intent=intent,
        confidence=confidence,
    )
