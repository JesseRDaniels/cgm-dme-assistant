"""CSV batch processing service."""
import pandas as pd
import io
import asyncio
import logging
from typing import Any

from services.rag import query_assistant

logger = logging.getLogger(__name__)


async def process_csv(
    batch_id: str,
    content: bytes,
    processing_type: str,
    jobs_store: dict,
):
    """
    Process a CSV file in the background.

    processing_type:
    - scrub: Check claims for issues
    - denial_analysis: Analyze denials
    - prior_auth: Generate prior auth checklists
    """
    try:
        # Parse CSV
        df = pd.read_csv(io.BytesIO(content))
        jobs_store[batch_id]["status"] = "processing"
        jobs_store[batch_id]["total_rows"] = len(df)

        results = []

        for idx, row in df.iterrows():
            try:
                result = await process_row(row, processing_type)
                results.append({"row": idx, "status": "success", "result": result})
                jobs_store[batch_id]["processed_rows"] += 1

            except Exception as e:
                logger.error(f"Row {idx} failed: {e}")
                results.append({"row": idx, "status": "error", "error": str(e)})
                jobs_store[batch_id]["errors"] += 1
                jobs_store[batch_id]["processed_rows"] += 1

            # Rate limiting - don't hammer the API
            await asyncio.sleep(0.5)

        jobs_store[batch_id]["status"] = "completed"
        jobs_store[batch_id]["results"] = results

    except Exception as e:
        logger.error(f"Batch {batch_id} failed: {e}")
        jobs_store[batch_id]["status"] = "failed"
        jobs_store[batch_id]["error"] = str(e)


async def process_row(row: pd.Series, processing_type: str) -> dict:
    """Process a single row based on processing type."""

    if processing_type == "scrub":
        return await scrub_claim(row)
    elif processing_type == "denial_analysis":
        return await analyze_denial(row)
    elif processing_type == "prior_auth":
        return await check_prior_auth(row)
    else:
        raise ValueError(f"Unknown processing type: {processing_type}")


async def scrub_claim(row: pd.Series) -> dict:
    """Check a claim for potential issues before submission."""
    # Build query from row data
    query = f"""Review this CGM claim for potential issues:
- Patient: {row.get('patient_name', 'Unknown')}
- HCPCS: {row.get('hcpcs_code', 'Unknown')}
- Diagnosis: {row.get('diagnosis', 'Unknown')}
- Modifier: {row.get('modifier', 'None')}

What issues might cause this claim to be denied?"""

    context = {
        "patient_name": row.get("patient_name"),
        "hcpcs_code": row.get("hcpcs_code"),
        "diagnosis": row.get("diagnosis"),
    }

    response = await query_assistant(query, context)

    return {
        "issues": response.answer,
        "risk_level": "high" if "deny" in response.answer.lower() else "low",
    }


async def analyze_denial(row: pd.Series) -> dict:
    """Analyze a denial and recommend next steps."""
    query = f"""Analyze this CGM claim denial:
- Denial Code: {row.get('denial_code', 'Unknown')}
- Denial Reason: {row.get('denial_reason', 'Not provided')}
- HCPCS: {row.get('hcpcs_code', 'Unknown')}
- Service Date: {row.get('service_date', 'Unknown')}

What caused this denial and what's the recommended next step?"""

    response = await query_assistant(query)

    return {
        "analysis": response.answer,
        "recommendation": extract_recommendation(response.answer),
        "appeal_worthy": "appeal" in response.answer.lower(),
    }


async def check_prior_auth(row: pd.Series) -> dict:
    """Check prior auth requirements for a patient."""
    query = f"""What documentation is needed for CGM prior authorization?
- Patient: {row.get('patient_name', 'Unknown')}
- Device: {row.get('device', 'CGM')}
- Diagnosis: {row.get('diagnosis', 'Unknown')}
- Current Status: {row.get('status', 'Unknown')}"""

    response = await query_assistant(query)

    return {
        "requirements": response.answer,
        "checklist": extract_checklist(response.answer),
    }


def extract_recommendation(text: str) -> str:
    """Extract the main recommendation from analysis text."""
    # Simple extraction - look for action words
    lines = text.split("\n")
    for line in lines:
        lower = line.lower()
        if any(word in lower for word in ["recommend", "should", "next step", "action"]):
            return line.strip()
    return "Review manually"


def extract_checklist(text: str) -> list[str]:
    """Extract checklist items from requirements text."""
    items = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
            # Clean up the bullet point
            clean = line.lstrip("-•*0123456789. ")
            if clean:
                items.append(clean)
    return items if items else ["Manual review required"]


def get_batch_status(batch_id: str, jobs_store: dict) -> dict:
    """Get status of a batch job."""
    return jobs_store.get(batch_id, {"status": "not_found"})


def get_batch_results(batch_id: str, jobs_store: dict) -> dict:
    """Get results of a completed batch job."""
    job = jobs_store.get(batch_id)
    if not job:
        return {"error": "Batch not found"}
    if job["status"] != "completed":
        return {"error": f"Batch not complete: {job['status']}"}
    return job["results"]
