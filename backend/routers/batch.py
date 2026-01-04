"""Batch processing endpoints for CSV uploads."""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid

from services.csv_processor import process_csv, get_batch_status, get_batch_results


router = APIRouter()


class BatchStatus(BaseModel):
    """Batch processing status."""
    batch_id: str
    status: str  # pending, processing, completed, failed
    total_rows: int
    processed_rows: int
    errors: int


class BatchResult(BaseModel):
    """Batch processing result."""
    batch_id: str
    results: list
    summary: dict


# In-memory store for batch jobs (use Redis/DB in production)
batch_jobs = {}


@router.post("/upload")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    processing_type: str = "scrub",  # scrub, denial_analysis, prior_auth
):
    """
    Upload a CSV for batch processing.

    Processing types:
    - scrub: Check claims for issues before submission
    - denial_analysis: Analyze denials and generate appeal recommendations
    - prior_auth: Generate prior auth checklists for patient list
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    batch_id = str(uuid.uuid4())

    # Read file content
    content = await file.read()

    # Store job info
    batch_jobs[batch_id] = {
        "status": "pending",
        "total_rows": 0,
        "processed_rows": 0,
        "errors": 0,
        "results": [],
    }

    # Process in background
    background_tasks.add_task(
        process_csv,
        batch_id=batch_id,
        content=content,
        processing_type=processing_type,
        jobs_store=batch_jobs,
    )

    return {"batch_id": batch_id, "status": "pending", "message": "Processing started"}


@router.get("/{batch_id}/status", response_model=BatchStatus)
async def batch_status(batch_id: str):
    """Get status of a batch processing job."""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    job = batch_jobs[batch_id]
    return BatchStatus(
        batch_id=batch_id,
        status=job["status"],
        total_rows=job["total_rows"],
        processed_rows=job["processed_rows"],
        errors=job["errors"],
    )


@router.get("/{batch_id}/results")
async def batch_results(batch_id: str):
    """Get results of a completed batch job."""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    job = batch_jobs[batch_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Batch not complete. Status: {job['status']}")

    return {
        "batch_id": batch_id,
        "results": job["results"],
        "summary": {
            "total": job["total_rows"],
            "processed": job["processed_rows"],
            "errors": job["errors"],
        },
    }
