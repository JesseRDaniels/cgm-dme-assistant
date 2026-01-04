"""HCPCS code lookup endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.code_lookup import get_code_info, search_codes


router = APIRouter()


class HCPCSCode(BaseModel):
    """HCPCS code information."""
    code: str
    short_description: str
    long_description: str
    category: str  # CGM, diabetic_supplies, etc.
    pricing_type: str  # rental, purchase, consumable
    common_modifiers: list[str]
    bundling_rules: Optional[list[str]] = None
    medical_necessity_required: bool
    lcd_reference: Optional[str] = None


class CodeSearchResult(BaseModel):
    """Code search results."""
    query: str
    results: list[HCPCSCode]
    total: int


# CGM-specific code database
CGM_CODES = {
    "A9276": HCPCSCode(
        code="A9276",
        short_description="CGM sensor",
        long_description="Sensor; invasive (e.g., subcutaneous), disposable, for use with interstitial continuous glucose monitoring system, one unit",
        category="cgm",
        pricing_type="consumable",
        common_modifiers=["KX", "NU"],
        bundling_rules=["Cannot bill with A9277 or A9278 from different system"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
    "A9277": HCPCSCode(
        code="A9277",
        short_description="CGM transmitter",
        long_description="Transmitter; external, for use with interstitial continuous glucose monitoring system",
        category="cgm",
        pricing_type="consumable",
        common_modifiers=["KX", "NU"],
        bundling_rules=["Must match sensor system (A9276)"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
    "A9278": HCPCSCode(
        code="A9278",
        short_description="CGM receiver",
        long_description="Receiver (monitor); external, for use with interstitial continuous glucose monitoring system",
        category="cgm",
        pricing_type="purchase",
        common_modifiers=["KX", "NU", "RR"],
        bundling_rules=["One receiver per beneficiary unless lost/broken"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
    "K0553": HCPCSCode(
        code="K0553",
        short_description="CGM receiver with voice",
        long_description="Supply allowance for therapeutic continuous glucose monitor (cgm), includes all supplies and accessories, 1 month supply",
        category="cgm",
        pricing_type="monthly_supply",
        common_modifiers=["KX"],
        bundling_rules=["All-inclusive monthly code"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
    "K0554": HCPCSCode(
        code="K0554",
        short_description="CGM receiver for K0553",
        long_description="Receiver (monitor); dedicated, for use with therapeutic glucose continuous monitor system",
        category="cgm",
        pricing_type="purchase",
        common_modifiers=["KX", "NU"],
        bundling_rules=["Use with K0553 system only"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
    "E2102": HCPCSCode(
        code="E2102",
        short_description="Adjunctive CGM receiver",
        long_description="Adjunctive continuous glucose monitor or receiver",
        category="cgm",
        pricing_type="purchase",
        common_modifiers=["NU", "RR"],
        bundling_rules=["For non-therapeutic/adjunctive use"],
        medical_necessity_required=False,
        lcd_reference=None,
    ),
    "E2103": HCPCSCode(
        code="E2103",
        short_description="Non-adjunctive CGM receiver",
        long_description="Non-adjunctive continuous glucose monitor or receiver",
        category="cgm",
        pricing_type="purchase",
        common_modifiers=["KX", "NU", "RR"],
        medical_necessity_required=True,
        lcd_reference="L33822",
    ),
}


@router.get("/{code}", response_model=HCPCSCode)
async def lookup_code(code: str):
    """Look up a specific HCPCS code."""
    code = code.upper().strip()
    if code not in CGM_CODES:
        raise HTTPException(status_code=404, detail=f"Code {code} not found in CGM database")
    return CGM_CODES[code]


@router.get("/", response_model=CodeSearchResult)
async def search_hcpcs(q: Optional[str] = None, category: Optional[str] = None):
    """
    Search HCPCS codes.

    - q: Search term (searches code, description)
    - category: Filter by category (cgm, diabetic_supplies)
    """
    results = []

    for code_data in CGM_CODES.values():
        # Filter by category
        if category and code_data.category != category.lower():
            continue

        # Search by query
        if q:
            q_lower = q.lower()
            if (
                q_lower in code_data.code.lower()
                or q_lower in code_data.short_description.lower()
                or q_lower in code_data.long_description.lower()
            ):
                results.append(code_data)
        else:
            results.append(code_data)

    return CodeSearchResult(
        query=q or "",
        results=results,
        total=len(results),
    )
