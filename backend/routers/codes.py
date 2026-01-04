"""HCPCS code lookup endpoints using Verity API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.verity import get_verity_client, VerityAPIError


router = APIRouter()


class CodeResponse(BaseModel):
    """Code lookup response."""
    code: str
    code_system: str
    description: str
    short_description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    rvu: Optional[dict] = None
    policies: Optional[list[dict]] = None


class PolicySummary(BaseModel):
    """Policy summary in code response."""
    policy_id: str
    title: str
    policy_type: str
    disposition: str
    jurisdiction: Optional[str] = None


class CodeSearchResult(BaseModel):
    """Code search results."""
    query: str
    results: list[dict]
    total: int


@router.get("/{code}", response_model=CodeResponse)
async def lookup_code(
    code: str,
    include_policies: bool = True,
    include_rvu: bool = True,
):
    """
    Look up a HCPCS/CPT/ICD-10 code with coverage policies.

    - **code**: The medical code (e.g., A9276, 76942)
    - **include_policies**: Include related Medicare/commercial policies
    - **include_rvu**: Include RVU pricing data
    """
    code = code.upper().strip()
    client = get_verity_client()

    try:
        data = await client.lookup_code(
            code=code,
            include_policies=include_policies,
            include_rvu=include_rvu,
        )

        if not data.get("found", False):
            raise HTTPException(
                status_code=404,
                detail=f"Code {code} not found",
            )

        return CodeResponse(
            code=data["code"],
            code_system=data.get("code_system", "HCPCS"),
            description=data.get("description", ""),
            short_description=data.get("short_description"),
            category=data.get("category"),
            is_active=data.get("is_active", True),
            rvu=data.get("rvu"),
            policies=data.get("policies"),
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")


@router.get("/", response_model=CodeSearchResult)
async def search_codes(
    q: str,
    code_system: Optional[str] = None,
    limit: int = 20,
):
    """
    Search for medical codes.

    - **q**: Search query (code or description text)
    - **code_system**: Filter by system (HCPCS, CPT, ICD10CM)
    - **limit**: Max results (default 20)
    """
    client = get_verity_client()

    try:
        # Use codes/search endpoint if available, otherwise lookup single code
        # For now, try direct lookup if it looks like a code
        if q and len(q) <= 10 and q.replace("-", "").replace(".", "").isalnum():
            # Looks like a code, try direct lookup
            try:
                data = await client.lookup_code(code=q.upper())
                if data.get("found"):
                    return CodeSearchResult(
                        query=q,
                        results=[data],
                        total=1,
                    )
            except VerityAPIError:
                pass

        # Return empty for text searches (Verity may not support free-text code search)
        return CodeSearchResult(
            query=q,
            results=[],
            total=0,
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")
