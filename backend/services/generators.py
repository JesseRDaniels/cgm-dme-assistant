"""Document generators for DWO, prior auth, and appeals."""
from datetime import date
from services.llm import generate
from prompts.dwo import DWO_PROMPT
from prompts.prior_auth import PRIOR_AUTH_PROMPT
from prompts.denial import APPEAL_PROMPT


async def generate_dwo(request) -> str:
    """Generate a Detailed Written Order (DWO)."""
    patient = request.patient

    context = f"""Patient Information:
- Name: {patient.first_name} {patient.last_name}
- DOB: {patient.dob}
- Address: {patient.address or 'N/A'}, {patient.city or ''}, {patient.state or ''} {patient.zip_code or ''}
- Phone: {patient.phone or 'N/A'}
- Insurance ID: {patient.insurance_id or 'N/A'}

Device Information:
- Device Type: {request.device_type}
- Diagnosis Codes: {', '.join(request.diagnosis_codes)}

Prescribing Physician:
- Name: {request.prescribing_physician}
- NPI: {request.physician_npi or 'N/A'}

Additional Notes: {request.notes or 'None'}

Today's Date: {date.today()}"""

    return await generate(
        system_prompt=DWO_PROMPT,
        user_message=context,
        max_tokens=2000,
        temperature=0.2,
    )


async def generate_prior_auth(request) -> str:
    """Generate a prior authorization request letter."""
    patient = request.patient

    context = f"""Patient Information:
- Name: {patient.first_name} {patient.last_name}
- DOB: {patient.dob}
- Insurance ID: {patient.insurance_id or 'N/A'}

Device Requested: {request.device_type}
Diagnosis Codes: {', '.join(request.diagnosis_codes)}

Clinical Information:
- A1C Value: {request.a1c_value or 'Not provided'}
- Insulin Regimen: {request.insulin_regimen or 'Not specified'}
- Hypoglycemia History: {request.hypoglycemia_history or 'Not documented'}

Additional Justification: {request.additional_justification or 'None'}

Today's Date: {date.today()}"""

    return await generate(
        system_prompt=PRIOR_AUTH_PROMPT,
        user_message=context,
        max_tokens=2500,
        temperature=0.2,
    )


async def generate_appeal(request) -> str:
    """Generate an appeal letter for a denied claim."""
    patient = request.patient

    context = f"""Claim Information:
- Claim Number: {request.claim_number}
- Service Date: {request.original_service_date}
- Denial Date: {request.denial_date}
- HCPCS Codes: {', '.join(request.hcpcs_codes)}

Denial Details:
- Reason Code: {request.denial_reason_code}
- Reason Text: {request.denial_reason_text or 'Not provided'}

Patient Information:
- Name: {patient.first_name} {patient.last_name}
- DOB: {patient.dob}
- Insurance ID: {patient.insurance_id or 'N/A'}

Supporting Documentation: {request.supporting_documentation or 'None specified'}

Today's Date: {date.today()}"""

    return await generate(
        system_prompt=APPEAL_PROMPT,
        user_message=context,
        max_tokens=3000,
        temperature=0.2,
    )
