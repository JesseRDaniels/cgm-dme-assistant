"""Sync router for triggering vector database updates."""
import os
import json
import time
import httpx
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config import get_settings
from services.pinecone_client import get_index, upsert_vectors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])

# Paths - check multiple locations for Railway vs local
def get_data_paths():
    """Get data file paths, checking Railway and local locations."""
    # In Railway, backend/ is root, so data/ is at ../data/ or we use backend/data/
    # Locally, we're in backend/ and data/ is at ../data/
    possible_roots = [
        Path(__file__).parent.parent / "data",  # backend/data/ (Railway)
        Path(__file__).parent.parent.parent / "data",  # ../data/ (local)
    ]

    for root in possible_roots:
        chunks = root / "chunks" / "all_chunks.json"
        if chunks.exists():
            return root, chunks, root / "sync_state.json"

    # Default to backend/data/ for Railway (will be created)
    root = Path(__file__).parent.parent / "data"
    return root, root / "chunks" / "all_chunks.json", root / "sync_state.json"

DATA_DIR, CHUNKS_FILE, SYNC_STATE_FILE = get_data_paths()

# Namespace mapping
TYPE_TO_NAMESPACE = {
    "lcd_policy": "lcd_policies",
    "hcpcs_code": "hcpcs_codes",
    "denial_reason": "denial_reasons",
    "documentation": "default",
    "appeal_strategy": "default",
}


class SyncStatus(BaseModel):
    status: str
    last_sync: str | None
    total_chunks: int
    message: str


class SyncResult(BaseModel):
    status: str
    chunks_updated: int
    duration_seconds: float
    message: str


def get_sync_state() -> dict:
    """Load sync state."""
    if SYNC_STATE_FILE.exists():
        return json.loads(SYNC_STATE_FILE.read_text())
    return {"last_sync": None, "synced_chunks": {}}


def save_sync_state(state: dict):
    """Save sync state."""
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(json.dumps(state, indent=2))


def load_chunks() -> list:
    """Load chunks from file."""
    if not CHUNKS_FILE.exists():
        return []
    return json.loads(CHUNKS_FILE.read_text())


def get_embeddings(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """Get embeddings from Voyage AI with retry."""
    settings = get_settings()

    for attempt in range(max_retries):
        try:
            response = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.voyage_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.embedding_model,
                    "input": texts,
                    "input_type": "document",
                },
                timeout=60,
            )
            response.raise_for_status()
            return [item["embedding"] for item in response.json()["data"]]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                logger.warning(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise
    return []


def find_changed_chunks(chunks: list, sync_state: dict) -> list:
    """Find chunks that changed since last sync."""
    changed = []
    synced = sync_state.get("synced_chunks", {})

    for chunk in chunks:
        chunk_id = chunk["id"]
        chunk_hash = hash(chunk["text"])
        if chunk_id not in synced or synced[chunk_id] != chunk_hash:
            changed.append(chunk)

    return changed


async def do_sync(full: bool = False) -> SyncResult:
    """Perform the sync operation."""
    start_time = time.time()

    state = get_sync_state()
    chunks = load_chunks()

    if not chunks:
        return SyncResult(
            status="error",
            chunks_updated=0,
            duration_seconds=0,
            message="No chunks file found"
        )

    # Find what needs updating
    if full:
        changed = chunks
    else:
        changed = find_changed_chunks(chunks, state)

    if not changed:
        return SyncResult(
            status="success",
            chunks_updated=0,
            duration_seconds=time.time() - start_time,
            message="Already up to date"
        )

    # Group by namespace
    by_namespace = {}
    for chunk in changed:
        chunk_type = chunk["metadata"].get("type", "default")
        namespace = TYPE_TO_NAMESPACE.get(chunk_type, "default")
        if namespace not in by_namespace:
            by_namespace[namespace] = []
        by_namespace[namespace].append(chunk)

    # Upsert each namespace
    total_updated = 0
    for namespace, ns_chunks in by_namespace.items():
        logger.info(f"Syncing {len(ns_chunks)} chunks to {namespace}")

        # Process in batches
        batch_size = 10
        for i in range(0, len(ns_chunks), batch_size):
            batch = ns_chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]

            embeddings = get_embeddings(texts)

            vectors = []
            for chunk, embedding in zip(batch, embeddings):
                vectors.append({
                    "id": chunk["id"],
                    "values": embedding,
                    "metadata": {
                        **chunk["metadata"],
                        "text": chunk["text"][:1000],
                    },
                })

            await upsert_vectors(vectors, namespace=namespace)
            total_updated += len(vectors)
            time.sleep(5)  # Rate limit

    # Update sync state
    now = datetime.now(timezone.utc).isoformat()
    state["last_sync"] = now
    state["synced_chunks"] = {c["id"]: hash(c["text"]) for c in chunks}
    save_sync_state(state)

    return SyncResult(
        status="success",
        chunks_updated=total_updated,
        duration_seconds=time.time() - start_time,
        message=f"Synced {total_updated} chunks"
    )


@router.get("/status", response_model=SyncStatus)
async def get_sync_status():
    """Get current sync status."""
    state = get_sync_state()
    chunks = load_chunks()

    return SyncStatus(
        status="ok",
        last_sync=state.get("last_sync"),
        total_chunks=len(chunks),
        message="Ready"
    )


@router.post("/run", response_model=SyncResult)
async def run_sync(full: bool = False, background_tasks: BackgroundTasks = None):
    """
    Trigger a sync operation.

    - **full**: If true, re-embed all chunks. Otherwise only changed chunks.

    This endpoint is designed to be called by Railway cron.
    """
    # For cron jobs, we want this to complete synchronously
    # so Railway knows if it succeeded
    try:
        result = await do_sync(full=full)
        logger.info(f"Sync completed: {result.message}")
        return result
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
