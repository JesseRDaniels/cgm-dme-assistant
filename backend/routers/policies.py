"""Policy management endpoints using Verity API."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from enum import Enum

from services.verity import get_verity_client, VerityAPIError


router = APIRouter()


class ChangeType(str, Enum):
    """Policy change types."""
    created = "created"
    updated = "updated"
    retired = "retired"
    codes_changed = "codes_changed"
    criteria_changed = "criteria_changed"
    metadata_changed = "metadata_changed"


class CriterionItem(BaseModel):
    """Single coverage criterion."""
    block_id: Optional[str] = None
    text: str
    tags: Optional[list[str]] = None


class CriteriaBySection(BaseModel):
    """Coverage criteria organized by section."""
    documentation: Optional[list[CriterionItem]] = None
    frequency: Optional[list[CriterionItem]] = None
    indications: Optional[list[CriterionItem]] = None
    limitations: Optional[list[CriterionItem]] = None


class CodeItem(BaseModel):
    """Code in policy."""
    code: str
    display: Optional[str] = None
    disposition: str  # covered, not_covered, conditional


class PolicyDetail(BaseModel):
    """Full policy detail response."""
    policy_id: str
    title: str
    policy_type: str
    status: str
    summary: Optional[str] = None
    jurisdiction: Optional[str] = None
    effective_date: Optional[str] = None
    mac: Optional[str] = None
    source_url: Optional[str] = None
    criteria: Optional[CriteriaBySection] = None
    codes: Optional[dict[str, list[CodeItem]]] = None  # e.g., {"HCPCS": [...]}


class PolicyChange(BaseModel):
    """Policy change record."""
    policy_id: str
    change_type: str
    changed_at: str
    title: Optional[str] = None
    summary: Optional[str] = None
    details: Optional[dict] = None


class PolicyChangesResponse(BaseModel):
    """Policy changes response."""
    changes: list[PolicyChange]
    total: int
    cursor: Optional[str] = None


class JurisdictionCoverage(BaseModel):
    """Coverage info for a jurisdiction."""
    jurisdiction: str
    mac_name: Optional[str] = None
    policy_id: Optional[str] = None
    disposition: str  # "covered", "not_covered", "conditional"
    notes: Optional[str] = None


class PolicyComparison(BaseModel):
    """Policy comparison across jurisdictions."""
    procedure_codes: list[str]
    jurisdictions: list[JurisdictionCoverage]
    national_policy: Optional[dict] = None


@router.get("/{policy_id}", response_model=PolicyDetail)
async def get_policy(
    policy_id: str,
    include_criteria: bool = True,
    include_codes: bool = True,
):
    """
    Get detailed information about a specific Medicare coverage policy.

    - **policy_id**: Policy ID (e.g., L33822, A52458, NCD220.6)
    - **include_criteria**: Include coverage criteria sections
    - **include_codes**: Include list of covered codes
    """
    client = get_verity_client()

    try:
        data = await client.get_policy(
            policy_id=policy_id.upper(),
            include_criteria=include_criteria,
            include_codes=include_codes,
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Policy {policy_id} not found",
            )

        # Parse criteria by section
        criteria = None
        if data.get("criteria") and isinstance(data["criteria"], dict):
            criteria = CriteriaBySection(
                documentation=[
                    CriterionItem(
                        block_id=c.get("block_id"),
                        text=c.get("text", ""),
                        tags=c.get("tags"),
                    )
                    for c in data["criteria"].get("documentation", [])
                ] or None,
                frequency=[
                    CriterionItem(
                        block_id=c.get("block_id"),
                        text=c.get("text", ""),
                        tags=c.get("tags"),
                    )
                    for c in data["criteria"].get("frequency", [])
                ] or None,
                indications=[
                    CriterionItem(
                        block_id=c.get("block_id"),
                        text=c.get("text", ""),
                        tags=c.get("tags"),
                    )
                    for c in data["criteria"].get("indications", [])
                ] or None,
                limitations=[
                    CriterionItem(
                        block_id=c.get("block_id"),
                        text=c.get("text", ""),
                        tags=c.get("tags"),
                    )
                    for c in data["criteria"].get("limitations", [])
                ] or None,
            )

        # Parse codes by system
        codes = None
        if data.get("codes") and isinstance(data["codes"], dict):
            codes = {}
            for system, code_list in data["codes"].items():
                codes[system] = [
                    CodeItem(
                        code=c.get("code", ""),
                        display=c.get("display"),
                        disposition=c.get("disposition", "unknown"),
                    )
                    for c in code_list
                ]

        # Get MAC name from nested object
        mac_name = None
        if data.get("mac") and isinstance(data["mac"], dict):
            mac_name = data["mac"].get("name")

        return PolicyDetail(
            policy_id=data.get("policy_id", policy_id),
            title=data.get("title", ""),
            policy_type=data.get("policy_type", ""),
            status=data.get("status", "active"),
            summary=data.get("summary"),
            jurisdiction=data.get("jurisdiction"),
            effective_date=data.get("effective_date"),
            mac=mac_name,
            source_url=data.get("source_url"),
            criteria=criteria,
            codes=codes,
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")


@router.get("/compare/jurisdictions", response_model=PolicyComparison)
async def compare_policies(
    codes: str = Query(..., description="Comma-separated procedure codes (e.g., K0553,A9276)"),
    jurisdictions: Optional[str] = Query(None, description="Comma-separated MAC jurisdictions (e.g., JM,JH)"),
):
    """
    Compare coverage policies across MAC jurisdictions for specific procedures.

    Useful for understanding regional coverage differences.

    - **codes**: Comma-separated CPT/HCPCS codes to compare
    - **jurisdictions**: Optional comma-separated MAC jurisdiction codes

    Note: This endpoint aggregates data from code lookups. For full comparison
    functionality, use the Verity MCP tools directly.
    """
    client = get_verity_client()

    procedure_codes = [c.strip().upper() for c in codes.split(",")]

    try:
        # Since compare API doesn't exist, we'll aggregate from code lookups
        # and return basic coverage info
        all_policies = {}

        for code in procedure_codes:
            try:
                code_data = await client.lookup_code(code=code, include_policies=True)
                if code_data.get("policies"):
                    for policy in code_data["policies"]:
                        policy_id = policy.get("policy_id", "")
                        if policy_id not in all_policies:
                            all_policies[policy_id] = {
                                "policy_id": policy_id,
                                "title": policy.get("title", ""),
                                "jurisdiction": policy.get("jurisdiction"),
                                "mac_name": policy.get("mac_name"),
                                "codes": [],
                            }
                        all_policies[policy_id]["codes"].append({
                            "code": code,
                            "disposition": policy.get("disposition", "covered"),
                        })
            except VerityAPIError:
                continue

        # Build jurisdiction coverage from policies
        jurisdiction_coverage = []
        for policy_id, policy_info in all_policies.items():
            jurisdiction_coverage.append(JurisdictionCoverage(
                jurisdiction=policy_info.get("jurisdiction") or "National",
                mac_name=policy_info.get("mac_name"),
                policy_id=policy_id,
                disposition="covered",  # If policy exists, codes are covered
                notes=f"Covers: {', '.join(c['code'] for c in policy_info['codes'])}",
            ))

        return PolicyComparison(
            procedure_codes=procedure_codes,
            jurisdictions=jurisdiction_coverage,
            national_policy=None,
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")


@router.get("/changes/recent", response_model=PolicyChangesResponse)
async def get_policy_changes(
    since: Optional[str] = Query(None, description="ISO8601 timestamp (e.g., 2026-01-01T00:00:00Z)"),
    policy_id: Optional[str] = Query(None, description="Filter to a specific policy"),
    change_type: Optional[ChangeType] = Query(None, description="Filter by change type"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """
    Track recent changes to Medicare coverage policies.

    Monitor LCD updates, new policies, retirements, and code changes.

    - **since**: Only show changes after this date
    - **policy_id**: Filter to a specific policy (e.g., L33822)
    - **change_type**: Filter by type of change
    - **limit**: Max results (1-100)
    """
    client = get_verity_client()

    try:
        result = await client.get_policy_changes(
            since=since,
            policy_id=policy_id.upper() if policy_id else None,
            change_type=change_type.value if change_type else None,
            limit=limit,
        )

        # API returns list directly in data, not data.changes
        change_list = result if isinstance(result, list) else result.get("changes", [])

        # Parse changes
        changes = []
        for change in change_list:
            changes.append(PolicyChange(
                policy_id=change.get("policy_id", ""),
                change_type=change.get("change_type", ""),
                changed_at=change.get("changed_at", ""),
                title=change.get("policy_title"),  # API uses policy_title
                summary=change.get("change_summary"),  # API uses change_summary
                details=change.get("details"),
            ))

        return PolicyChangesResponse(
            changes=changes,
            total=len(changes),
            cursor=None,  # Pagination handled separately via meta
        )

    except VerityAPIError as e:
        raise HTTPException(status_code=502, detail=f"Verity API error: {e.message}")
