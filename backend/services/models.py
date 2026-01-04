"""Shared models for services."""
from pydantic import BaseModel
from typing import Optional


class Citation(BaseModel):
    """Source citation for RAG response."""
    source: str  # e.g., "LCD L33822"
    section: Optional[str] = None  # e.g., "Coverage Indications"
    text: str  # Relevant excerpt
    relevance_score: float


class ChatResponse(BaseModel):
    """Response from the chat assistant."""
    answer: str
    citations: list[Citation]
    intent: str  # prior_auth, coding, denial, general
    confidence: float


class RetrievedChunk(BaseModel):
    """Chunk retrieved from vector DB."""
    id: str
    text: str
    metadata: dict
    score: float
