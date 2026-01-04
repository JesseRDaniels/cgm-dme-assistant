"""Claim auditing and validation endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter()


class ClaimAuditRequest(BaseModel):
    """Request for claim audit."""
    hcpcs_code: str
    modifier: Optional[str] = None
    diagnosis_codes: list[str]  # ICD-10 codes
    device_type: Optional[str] = None  # e.g., "Dexcom G7", "Freestyle Libre 3"
    service_date: Optional[date] = None
    # Documentation flags
    has_face_to_face: bool = False
    has_written_order: bool = False
    has_medical_necessity: bool = False
    insulin_therapy: Optional[str] = None  # "pump", "mdi" (multiple daily injections), "none"
    a1c_documented: bool = False


class AuditIssue(BaseModel):
    """Single audit issue."""
    severity: str  # "error", "warning", "info"
    category: str  # "hcpcs", "modifier", "diagnosis", "documentation", "lcd", "bundling"
    message: str
    recommendation: str


class ClaimAuditResponse(BaseModel):
    """Audit results."""
    passed: bool
    score: int  # 0-100
    issues: list[AuditIssue]
    lcd_reference: str
    summary: str


# CGM HCPCS validation rules
CGM_CODES = {
    "A9276": {"type": "sensor", "requires_kx": True, "lcd": "L33822"},
    "A9277": {"type": "transmitter", "requires_kx": True, "lcd": "L33822"},
    "A9278": {"type": "receiver", "requires_kx": True, "lcd": "L33822"},
    "K0553": {"type": "monthly_supply", "requires_kx": True, "lcd": "L33822", "bundling_exclusive": ["A9276", "A9277", "A9278"]},
    "K0554": {"type": "receiver_k0553", "requires_kx": True, "lcd": "L33822"},
    "E2102": {"type": "adjunctive_receiver", "requires_kx": False, "lcd": None},
    "E2103": {"type": "non_adjunctive_receiver", "requires_kx": True, "lcd": "L33822"},
}

# Valid diabetes diagnosis codes for CGM (ICD-10)
VALID_DIABETES_DX = [
    "E10",  # Type 1 diabetes
    "E11",  # Type 2 diabetes
    "E13",  # Other specified diabetes
    "O24",  # Gestational diabetes
]

# LCD L33822 requirements
LCD_REQUIREMENTS = {
    "diagnosis": "Documented diagnosis of diabetes (Type 1, Type 2, or gestational)",
    "face_to_face": "Face-to-face encounter within 6 months prior to order",
    "written_order": "Detailed written order from treating physician",
    "medical_necessity": "Medical necessity documentation supporting CGM use",
    "insulin_or_hypoglycemia": "Intensive insulin therapy (3+ injections/day or pump) OR documented problematic hypoglycemia",
}


def validate_hcpcs(code: str) -> list[AuditIssue]:
    """Validate HCPCS code is valid for CGM."""
    issues = []
    code = code.upper().strip()

    if code not in CGM_CODES:
        issues.append(AuditIssue(
            severity="error",
            category="hcpcs",
            message=f"Code {code} is not a recognized CGM HCPCS code",
            recommendation=f"Valid CGM codes: A9276, A9277, A9278, K0553, K0554, E2102, E2103"
        ))

    return issues


def validate_modifier(code: str, modifier: Optional[str]) -> list[AuditIssue]:
    """Validate required modifiers."""
    issues = []
    code = code.upper().strip()

    if code not in CGM_CODES:
        return issues

    code_info = CGM_CODES[code]

    if code_info.get("requires_kx") and (not modifier or "KX" not in modifier.upper()):
        issues.append(AuditIssue(
            severity="error",
            category="modifier",
            message=f"Code {code} requires KX modifier but it's missing",
            recommendation="Add KX modifier to indicate medical necessity documentation is on file (LCD L33822 criteria met)"
        ))

    return issues


def validate_diagnosis(diagnosis_codes: list[str]) -> list[AuditIssue]:
    """Validate diagnosis codes support CGM coverage."""
    issues = []

    if not diagnosis_codes:
        issues.append(AuditIssue(
            severity="error",
            category="diagnosis",
            message="No diagnosis codes provided",
            recommendation="Add ICD-10 diabetes diagnosis code (E10.x, E11.x, E13.x, or O24.x)"
        ))
        return issues

    # Check for valid diabetes diagnosis
    has_valid_dx = False
    for dx in diagnosis_codes:
        dx_prefix = dx.upper().split(".")[0]
        if dx_prefix in VALID_DIABETES_DX:
            has_valid_dx = True
            break

    if not has_valid_dx:
        issues.append(AuditIssue(
            severity="error",
            category="diagnosis",
            message=f"No valid diabetes diagnosis found in {diagnosis_codes}",
            recommendation="CGM requires diabetes diagnosis: E10.x (Type 1), E11.x (Type 2), E13.x (Other), or O24.x (Gestational)"
        ))

    return issues


def validate_documentation(request: ClaimAuditRequest) -> list[AuditIssue]:
    """Validate documentation requirements per LCD L33822."""
    issues = []

    if not request.has_face_to_face:
        issues.append(AuditIssue(
            severity="error",
            category="documentation",
            message="Face-to-face encounter not documented",
            recommendation="Document face-to-face encounter with treating physician within 6 months prior to CGM order"
        ))

    if not request.has_written_order:
        issues.append(AuditIssue(
            severity="error",
            category="documentation",
            message="Written order (DWO) not on file",
            recommendation="Obtain detailed written order from prescribing physician with diagnosis, device, and medical necessity"
        ))

    if not request.has_medical_necessity:
        issues.append(AuditIssue(
            severity="warning",
            category="documentation",
            message="Medical necessity statement not documented",
            recommendation="Document why CGM is medically necessary for this patient (glycemic control, hypoglycemia risk, etc.)"
        ))

    # Check insulin therapy requirement
    if request.insulin_therapy not in ["pump", "mdi"]:
        issues.append(AuditIssue(
            severity="warning",
            category="lcd",
            message="Intensive insulin therapy not documented",
            recommendation="LCD L33822 requires intensive insulin regimen (3+ daily injections or pump) OR documented problematic hypoglycemia"
        ))

    return issues


def validate_bundling(code: str) -> list[AuditIssue]:
    """Check for bundling rule warnings."""
    issues = []
    code = code.upper().strip()

    if code == "K0553":
        issues.append(AuditIssue(
            severity="info",
            category="bundling",
            message="K0553 is an all-inclusive monthly code",
            recommendation="Do NOT bill A9276, A9277, or A9278 with K0553 - they are mutually exclusive"
        ))

    if code in ["A9276", "A9277", "A9278"]:
        issues.append(AuditIssue(
            severity="info",
            category="bundling",
            message=f"{code} is a component code",
            recommendation="If using monthly supply model, use K0553 instead. Do not mix component codes with K0553."
        ))

    return issues


@router.post("/claim", response_model=ClaimAuditResponse)
async def audit_claim(request: ClaimAuditRequest):
    """
    Audit a CGM claim for LCD compliance and coding accuracy.

    Checks:
    - HCPCS code validity
    - Required modifiers (KX)
    - Diagnosis code coverage
    - Documentation requirements (LCD L33822)
    - Bundling rules
    """
    all_issues = []

    # Run all validations
    all_issues.extend(validate_hcpcs(request.hcpcs_code))
    all_issues.extend(validate_modifier(request.hcpcs_code, request.modifier))
    all_issues.extend(validate_diagnosis(request.diagnosis_codes))
    all_issues.extend(validate_documentation(request))
    all_issues.extend(validate_bundling(request.hcpcs_code))

    # Calculate score
    error_count = sum(1 for i in all_issues if i.severity == "error")
    warning_count = sum(1 for i in all_issues if i.severity == "warning")

    if error_count == 0 and warning_count == 0:
        score = 100
    elif error_count == 0:
        score = max(70, 100 - (warning_count * 10))
    else:
        score = max(0, 60 - (error_count * 20) - (warning_count * 5))

    passed = error_count == 0

    # Generate summary
    if passed and warning_count == 0:
        summary = "Claim passes all LCD L33822 requirements. Ready for submission."
    elif passed:
        summary = f"Claim passes but has {warning_count} warning(s) to review before submission."
    else:
        summary = f"Claim has {error_count} error(s) that must be fixed before submission."

    return ClaimAuditResponse(
        passed=passed,
        score=score,
        issues=all_issues,
        lcd_reference="L33822",
        summary=summary,
    )


class QuickAuditRequest(BaseModel):
    """Quick audit with minimal info."""
    hcpcs_code: str
    modifier: Optional[str] = None
    diagnosis_code: str


@router.post("/quick", response_model=ClaimAuditResponse)
async def quick_audit(request: QuickAuditRequest):
    """Quick audit with just code, modifier, and diagnosis."""
    full_request = ClaimAuditRequest(
        hcpcs_code=request.hcpcs_code,
        modifier=request.modifier,
        diagnosis_codes=[request.diagnosis_code],
        has_face_to_face=True,  # Assume documented for quick check
        has_written_order=True,
        has_medical_necessity=True,
        insulin_therapy="mdi",
    )
    return await audit_claim(full_request)
