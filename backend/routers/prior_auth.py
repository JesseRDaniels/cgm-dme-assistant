"""Prior authorization check endpoints using Verity API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.verity import get_verity_client, VerityAPIError


router = APIRouter()


class PriorAuthRequest(BaseModel):
    """Prior auth check request."""
    procedure_codes: list[str]
    state: Optional[str] = None  # Two-letter state code (e.g., "TX", "FL")
    diagnosis_codes: Optional[list[str]] = None


class MatchedPolicy(BaseModel):
    """Policy matched in prior auth check."""
    policy_id: str
    title: str
    policy_type: str
    jurisdiction: Optional[str] = None
    codes: Optional[list[dict]] = None


class CriteriaDetails(BaseModel):
    """Coverage criteria details."""
    indications: Optional[list[dict]] = None
    limitations: Optional[list[dict]] = None


class PriorAuthResponse(BaseModel):
    """Prior auth check response."""
    pa_required: bool
    confidence: str  # "high", "medium", "low"
    reason: str
    matched_policies: list[MatchedPolicy]
    documentation_checklist: list[str]
    criteria_details: Optional[CriteriaDetails] = None


@router.post("/check", response_model=PriorAuthResponse)
async def check_prior_auth(request: PriorAuthRequest):
    """
    Check if prior authorization is required for procedures.

    Returns:
    - **pa_required**: Whether PA is needed
    - **confidence**: Confidence level (high/medium/low)
    - **matched_policies**: Medicare LCDs and commercial policies
    - **documentation_checklist**: Required documentation items
    - **criteria_details**: Coverage indications and limitations
    """
    client = get_verity_client()

    try:
        data = await client.check_prior_auth(
            procedure_codes=request.procedure_codes,
            state=request.state,
            diagnosis_codes=request.diagnosis_codes,
        )

        # Parse matched policies
        matched_policies = []
        for policy in data.get("matched_policies", []):
            matched_policies.append(MatchedPolicy(
                policy_id=policy.get("policy_id", ""),
                title=policy.get("title", ""),
                policy_type=policy.get("policy_type", ""),
                jurisdiction=policy.get("jurisdiction"),
                codes=policy.get("codes"),
            ))

        # Parse criteria details if present
        criteria_details = None
        if "criteria_details" in data:
            cd = data["criteria_details"]
            criteria_details = CriteriaDetails(
                indications=cd.get("indications"),
                limitations=cd.get("limitations"),
            )

        return PriorAuthResponse(
            pa_required=data.get("pa_required", False),
            confidence=data.get("confidence", "low"),
            reason=data.get("reason", ""),
            matched_policies=matched_policies,
            documentation_checklist=data.get("documentation_checklist", []),
            criteria_details=criteria_details,
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")


@router.get("/jurisdictions")
async def list_jurisdictions():
    """
    List Medicare Administrative Contractor (MAC) jurisdictions.

    Returns jurisdiction codes, names, and covered states.
    """
    client = get_verity_client()

    try:
        data = await client.list_jurisdictions()
        return {"jurisdictions": data}
    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")
