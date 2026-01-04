"""Chat endpoint for querying the CGM DME assistant."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.rag import query_assistant
from services.models import ChatResponse, Citation


router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str
    context: Optional[dict] = None  # Optional patient/claim context


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Query the CGM DME assistant.

    Supports queries about:
    - Prior authorization requirements
    - Medical necessity criteria (LCD L33822)
    - HCPCS codes and modifiers
    - Denial reasons and appeals
    - DWO/SWO requirements
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        response = await query_assistant(
            query=request.query,
            context=request.context,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
