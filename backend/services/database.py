"""PostgreSQL database service with connection pooling for vector snapshots."""
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg

from config import get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_database() -> None:
    """Initialize database connection pool and create tables."""
    global _pool
    settings = get_settings()

    if not settings.database_url:
        logger.warning("DATABASE_URL not set, skipping database initialization")
        return

    try:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database connection pool initialized")

        # Create tables
        await _create_tables()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def _create_tables() -> None:
    """Create required tables if they don't exist."""
    if not _pool:
        return

    async with _pool.acquire() as conn:
        # vector_snapshots table - stores full snapshots of vector data
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vector_snapshots (
                id SERIAL PRIMARY KEY,
                snapshot_id VARCHAR(64) UNIQUE NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                chunk_count INTEGER NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                chunks JSONB NOT NULL,
                metadata JSONB DEFAULT '{}',
                is_active BOOLEAN DEFAULT FALSE,
                deployed_at TIMESTAMPTZ
            )
        """)

        # sync_history table - tracks sync operations
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                snapshot_id VARCHAR(64) REFERENCES vector_snapshots(snapshot_id),
                chunks_added INTEGER DEFAULT 0,
                chunks_updated INTEGER DEFAULT 0,
                chunks_removed INTEGER DEFAULT 0,
                error_message TEXT,
                triggered_by VARCHAR(50) DEFAULT 'manual'
            )
        """)

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_created_at
            ON vector_snapshots(created_at DESC)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_active
            ON vector_snapshots(is_active) WHERE is_active = TRUE
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_history_started
            ON sync_history(started_at DESC)
        """)

        logger.info("Database tables created/verified")


@asynccontextmanager
async def get_connection():
    """Get a database connection from the pool."""
    if not _pool:
        raise RuntimeError("Database not initialized")
    async with _pool.acquire() as conn:
        yield conn


def compute_content_hash(chunks: list) -> str:
    """Compute a hash of chunk content for change detection."""
    # Sort chunks by ID for consistent hashing
    sorted_chunks = sorted(chunks, key=lambda c: c.get("id", ""))
    content = json.dumps(sorted_chunks, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def generate_snapshot_id() -> str:
    """Generate a unique snapshot ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
    return f"snap_{timestamp}_{random_suffix}"


async def save_snapshot(chunks: list, metadata: dict = None) -> dict:
    """
    Save a new vector snapshot to the database.

    Returns snapshot info including ID and change statistics.
    """
    if not _pool:
        raise RuntimeError("Database not initialized")

    snapshot_id = generate_snapshot_id()
    content_hash = compute_content_hash(chunks)

    async with _pool.acquire() as conn:
        # Check if content already exists (no changes)
        existing = await conn.fetchrow(
            "SELECT snapshot_id, chunk_count FROM vector_snapshots WHERE content_hash = $1",
            content_hash
        )
        if existing:
            return {
                "snapshot_id": existing["snapshot_id"],
                "status": "unchanged",
                "chunk_count": existing["chunk_count"],
                "message": "Content unchanged from existing snapshot"
            }

        # Get current active snapshot for comparison
        active = await conn.fetchrow(
            "SELECT snapshot_id, chunks, chunk_count FROM vector_snapshots WHERE is_active = TRUE"
        )

        # Calculate changes
        changes = {"added": 0, "updated": 0, "removed": 0}
        if active:
            active_chunks = active["chunks"] if isinstance(active["chunks"], list) else json.loads(active["chunks"])
            old_chunks = {c["id"]: c for c in active_chunks}
            new_chunks = {c["id"]: c for c in chunks}

            for chunk_id, chunk in new_chunks.items():
                if chunk_id not in old_chunks:
                    changes["added"] += 1
                elif hash(chunk.get("text", "")) != hash(old_chunks[chunk_id].get("text", "")):
                    changes["updated"] += 1

            for chunk_id in old_chunks:
                if chunk_id not in new_chunks:
                    changes["removed"] += 1

        # Save new snapshot
        await conn.execute("""
            INSERT INTO vector_snapshots (snapshot_id, chunk_count, content_hash, chunks, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, snapshot_id, len(chunks), content_hash, json.dumps(chunks), json.dumps(metadata or {}))

        return {
            "snapshot_id": snapshot_id,
            "status": "created",
            "chunk_count": len(chunks),
            "changes": changes,
            "content_hash": content_hash
        }


async def activate_snapshot(snapshot_id: str) -> bool:
    """
    Mark a snapshot as active (deployed to Pinecone).

    Deactivates any previously active snapshot.
    """
    if not _pool:
        raise RuntimeError("Database not initialized")

    async with _pool.acquire() as conn:
        async with conn.transaction():
            # Deactivate current active snapshot
            await conn.execute(
                "UPDATE vector_snapshots SET is_active = FALSE WHERE is_active = TRUE"
            )

            # Activate the new snapshot
            result = await conn.execute("""
                UPDATE vector_snapshots
                SET is_active = TRUE, deployed_at = NOW()
                WHERE snapshot_id = $1
            """, snapshot_id)

            return result == "UPDATE 1"


async def get_active_snapshot() -> Optional[dict]:
    """Get the currently active snapshot."""
    if not _pool:
        return None

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM vector_snapshots WHERE is_active = TRUE"
        )
        if row:
            return {
                "snapshot_id": row["snapshot_id"],
                "created_at": row["created_at"].isoformat(),
                "deployed_at": row["deployed_at"].isoformat() if row["deployed_at"] else None,
                "chunk_count": row["chunk_count"],
                "content_hash": row["content_hash"],
                "chunks": row["chunks"] if isinstance(row["chunks"], list) else json.loads(row["chunks"]),
                "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
            }
        return None


async def get_snapshot(snapshot_id: str) -> Optional[dict]:
    """Get a specific snapshot by ID."""
    if not _pool:
        return None

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM vector_snapshots WHERE snapshot_id = $1",
            snapshot_id
        )
        if row:
            return {
                "snapshot_id": row["snapshot_id"],
                "created_at": row["created_at"].isoformat(),
                "deployed_at": row["deployed_at"].isoformat() if row["deployed_at"] else None,
                "chunk_count": row["chunk_count"],
                "content_hash": row["content_hash"],
                "chunks": row["chunks"] if isinstance(row["chunks"], list) else json.loads(row["chunks"]),
                "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
                "is_active": row["is_active"]
            }
        return None


async def list_snapshots(limit: int = 10) -> list:
    """List recent snapshots."""
    if not _pool:
        return []

    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT snapshot_id, created_at, deployed_at, chunk_count, is_active, metadata
            FROM vector_snapshots
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

        return [
            {
                "snapshot_id": row["snapshot_id"],
                "created_at": row["created_at"].isoformat(),
                "deployed_at": row["deployed_at"].isoformat() if row["deployed_at"] else None,
                "chunk_count": row["chunk_count"],
                "is_active": row["is_active"],
                "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]) if row["metadata"] else {}
            }
            for row in rows
        ]


async def record_sync_start(triggered_by: str = "manual") -> int:
    """Record the start of a sync operation. Returns sync history ID."""
    if not _pool:
        return -1

    async with _pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO sync_history (triggered_by, status)
            VALUES ($1, 'running')
            RETURNING id
        """, triggered_by)
        return row["id"]


async def record_sync_complete(
    sync_id: int,
    snapshot_id: str,
    chunks_added: int = 0,
    chunks_updated: int = 0,
    chunks_removed: int = 0
) -> None:
    """Record successful completion of a sync operation."""
    if not _pool or sync_id < 0:
        return

    async with _pool.acquire() as conn:
        await conn.execute("""
            UPDATE sync_history
            SET completed_at = NOW(), status = 'success', snapshot_id = $2,
                chunks_added = $3, chunks_updated = $4, chunks_removed = $5
            WHERE id = $1
        """, sync_id, snapshot_id, chunks_added, chunks_updated, chunks_removed)


async def record_sync_error(sync_id: int, error_message: str) -> None:
    """Record a failed sync operation."""
    if not _pool or sync_id < 0:
        return

    async with _pool.acquire() as conn:
        await conn.execute("""
            UPDATE sync_history
            SET completed_at = NOW(), status = 'failed', error_message = $2
            WHERE id = $1
        """, sync_id, error_message)


async def record_sync_paused(sync_id: int, reason: str) -> None:
    """Record a paused sync operation (e.g., safety threshold exceeded)."""
    if not _pool or sync_id < 0:
        return

    async with _pool.acquire() as conn:
        await conn.execute("""
            UPDATE sync_history
            SET completed_at = NOW(), status = 'paused', error_message = $2
            WHERE id = $1
        """, sync_id, reason)


async def get_sync_history(limit: int = 20) -> list:
    """Get recent sync history."""
    if not _pool:
        return []

    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, started_at, completed_at, status, snapshot_id,
                   chunks_added, chunks_updated, chunks_removed, error_message, triggered_by
            FROM sync_history
            ORDER BY started_at DESC
            LIMIT $1
        """, limit)

        return [
            {
                "id": row["id"],
                "started_at": row["started_at"].isoformat(),
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "status": row["status"],
                "snapshot_id": row["snapshot_id"],
                "chunks_added": row["chunks_added"],
                "chunks_updated": row["chunks_updated"],
                "chunks_removed": row["chunks_removed"],
                "error_message": row["error_message"],
                "triggered_by": row["triggered_by"]
            }
            for row in rows
        ]


async def is_database_ready() -> bool:
    """Check if database is initialized and ready."""
    return _pool is not None
