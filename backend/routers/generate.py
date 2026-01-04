"""Document generation endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date

from services.generators import generate_dwo, generate_prior_auth, generate_appeal


router = APIRouter()


class PatientInfo(BaseModel):
    """Patient information for document generation."""
    first_name: str
    last_name: str
    dob: date
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    insurance_id: Optional[str] = None


class DWORequest(BaseModel):
    """Request for DWO generation."""
    patient: PatientInfo
    diagnosis_codes: list[str]  # ICD-10 codes
    device_type: str  # e.g., "Dexcom G7", "Freestyle Libre 3"
    prescribing_physician: str
    physician_npi: Optional[str] = None
    notes: Optional[str] = None


class PriorAuthRequest(BaseModel):
    """Request for prior authorization letter."""
    patient: PatientInfo
    device_type: str
    diagnosis_codes: list[str]
    a1c_value: Optional[float] = None
    insulin_regimen: Optional[str] = None
    hypoglycemia_history: Optional[str] = None
    additional_justification: Optional[str] = None


class AppealRequest(BaseModel):
    """Request for appeal letter generation."""
    patient: PatientInfo
    claim_number: str
    denial_date: date
    denial_reason_code: str
    denial_reason_text: Optional[str] = None
    original_service_date: date
    hcpcs_codes: list[str]
    supporting_documentation: Optional[str] = None


class GeneratedDocument(BaseModel):
    """Generated document response."""
    document_type: str
    content: str
    metadata: dict


@router.post("/dwo", response_model=GeneratedDocument)
async def create_dwo(request: DWORequest):
    """
    Generate a Detailed Written Order (DWO) for CGM.

    Includes:
    - Patient demographics
    - Diagnosis codes
    - Device specifications
    - Medical necessity statement
    - Physician attestation
    """
    try:
        content = await generate_dwo(request)
        return GeneratedDocument(
            document_type="DWO",
            content=content,
            metadata={
                "patient": f"{request.patient.last_name}, {request.patient.first_name}",
                "device": request.device_type,
                "generated_date": str(date.today()),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prior-auth", response_model=GeneratedDocument)
async def create_prior_auth(request: PriorAuthRequest):
    """
    Generate a prior authorization request letter.

    Includes:
    - Medical necessity justification based on LCD L33822
    - A1C and insulin therapy documentation
    - Hypoglycemia history if applicable
    """
    try:
        content = await generate_prior_auth(request)
        return GeneratedDocument(
            document_type="Prior Authorization",
            content=content,
            metadata={
                "patient": f"{request.patient.last_name}, {request.patient.first_name}",
                "device": request.device_type,
                "generated_date": str(date.today()),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/appeal", response_model=GeneratedDocument)
async def create_appeal(request: AppealRequest):
    """
    Generate an appeal letter for a denied claim.

    Includes:
    - Denial reason analysis
    - Counter-arguments based on LCD criteria
    - Supporting documentation references
    """
    try:
        content = await generate_appeal(request)
        return GeneratedDocument(
            document_type="Appeal Letter",
            content=content,
            metadata={
                "patient": f"{request.patient.last_name}, {request.patient.first_name}",
                "claim_number": request.claim_number,
                "denial_code": request.denial_reason_code,
                "generated_date": str(date.today()),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
