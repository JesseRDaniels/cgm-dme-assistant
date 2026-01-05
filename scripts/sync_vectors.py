#!/usr/bin/env python3
"""
Sync Pinecone vectors with latest data from Verity API.

Checks for policy changes, updates modified chunks, and maintains sync state.
Run periodically (e.g., daily cron) or manually when policies update.

Usage:
    python scripts/sync_vectors.py              # Normal sync
    python scripts/sync_vectors.py --full       # Full rebuild
    python scripts/sync_vectors.py --dry-run    # Preview changes
"""
import json
import os
import sys
import time
import argparse
import httpx
from pathlib import Path
from datetime import datetime, timezone
from pinecone import Pinecone

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CHUNKS_FILE = PROJECT_DIR / "data" / "chunks" / "all_chunks.json"
SYNC_STATE_FILE = PROJECT_DIR / "data" / "sync_state.json"

# Load environment
def load_env():
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

load_env()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VERITY_API_KEY = os.getenv("VERITY_API_KEY")
VERITY_BASE_URL = "https://verity.backworkai.com/api/v1"
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "cgm-dme")

# Namespace mapping
TYPE_TO_NAMESPACE = {
    "lcd_policy": "lcd_policies",
    "hcpcs_code": "hcpcs_codes",
    "denial_reason": "denial_reasons",
    "documentation": "default",
    "appeal_strategy": "default",
}


def get_sync_state() -> dict:
    """Load sync state from file."""
    if SYNC_STATE_FILE.exists():
        return json.loads(SYNC_STATE_FILE.read_text())
    return {
        "last_sync": None,
        "last_policy_check": None,
        "synced_chunks": {},
    }


def save_sync_state(state: dict):
    """Save sync state to file."""
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(json.dumps(state, indent=2))


def verity_request(endpoint: str, params: dict = None) -> dict:
    """Make request to Verity API."""
    resp = httpx.get(
        f"{VERITY_BASE_URL}{endpoint}",
        headers={"Authorization": f"Bearer {VERITY_API_KEY}"},
        params=params or {},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", data)


def check_policy_changes(since: str = None) -> list:
    """Check Verity API for policy changes since last sync."""
    params = {}
    if since:
        params["since"] = since

    try:
        changes = verity_request("/policies/changes", params)
        return changes if isinstance(changes, list) else []
    except Exception as e:
        print(f"  Warning: Could not fetch policy changes: {e}")
        return []


def get_embeddings(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """Get embeddings from Voyage AI with retry logic."""
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {VOYAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "voyage-3-lite",
                    "input": texts,
                    "input_type": "document",
                },
                timeout=60,
            )
            response.raise_for_status()
            return [item["embedding"] for item in response.json()["data"]]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s, 40s
                print(f"    Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            raise
    return []


def load_chunks() -> list:
    """Load chunks from file."""
    if not CHUNKS_FILE.exists():
        return []
    return json.loads(CHUNKS_FILE.read_text())


def save_chunks(chunks: list):
    """Save chunks to file."""
    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_FILE.write_text(json.dumps(chunks, indent=2))


def find_changed_chunks(chunks: list, sync_state: dict) -> list:
    """Find chunks that have changed since last sync."""
    changed = []
    synced = sync_state.get("synced_chunks", {})

    for chunk in chunks:
        chunk_id = chunk["id"]
        chunk_hash = hash(chunk["text"])

        if chunk_id not in synced or synced[chunk_id] != chunk_hash:
            changed.append(chunk)

    return changed


def upsert_chunks(chunks: list, index, dry_run: bool = False):
    """Upsert chunks to Pinecone."""
    if not chunks:
        return

    # Group by namespace
    by_namespace = {}
    for chunk in chunks:
        chunk_type = chunk["metadata"].get("type", "default")
        namespace = TYPE_TO_NAMESPACE.get(chunk_type, "default")
        if namespace not in by_namespace:
            by_namespace[namespace] = []
        by_namespace[namespace].append(chunk)

    for namespace, ns_chunks in by_namespace.items():
        print(f"  {namespace}: {len(ns_chunks)} chunks")

        if dry_run:
            for c in ns_chunks[:3]:
                print(f"    - {c['id']}")
            if len(ns_chunks) > 3:
                print(f"    ... and {len(ns_chunks) - 3} more")
            continue

        # Get embeddings in batches
        batch_size = 10
        for i in range(0, len(ns_chunks), batch_size):
            batch = ns_chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]

            print(f"    Embedding batch {i // batch_size + 1}...")
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

            index.upsert(vectors=vectors, namespace=namespace)
            time.sleep(5)  # Rate limit - Voyage AI is strict


def sync(full: bool = False, dry_run: bool = False):
    """Main sync function."""
    print("=" * 60)
    print(f"CGM-DME Vector Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if dry_run:
        print("DRY RUN - No changes will be made\n")

    # Load state
    state = get_sync_state()
    last_sync = state.get("last_sync")
    print(f"Last sync: {last_sync or 'Never'}")

    # Check for policy changes from Verity
    print("\n1. Checking Verity API for policy changes...")
    policy_changes = check_policy_changes(last_sync)
    if policy_changes:
        print(f"   Found {len(policy_changes)} policy changes")
        for change in policy_changes[:5]:
            print(f"   - {change.get('policy_id')}: {change.get('change_type')}")
    else:
        print("   No policy changes detected")

    # Load chunks
    print("\n2. Loading chunks...")
    chunks = load_chunks()
    print(f"   Loaded {len(chunks)} chunks from {CHUNKS_FILE.name}")

    # Find changed chunks
    print("\n3. Identifying changes...")
    if full:
        changed = chunks
        print(f"   Full rebuild: {len(changed)} chunks")
    else:
        changed = find_changed_chunks(chunks, state)
        print(f"   Changed since last sync: {len(changed)} chunks")

    if not changed:
        print("\n✅ Everything is up to date!")
        return

    # Connect to Pinecone
    print("\n4. Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    stats = index.describe_index_stats()
    print(f"   Index: {INDEX_NAME} ({stats.total_vector_count} vectors)")

    # Upsert changes
    print(f"\n5. {'Would upsert' if dry_run else 'Upserting'} {len(changed)} chunks...")
    upsert_chunks(changed, index, dry_run=dry_run)

    # Update sync state
    if not dry_run:
        now = datetime.now(timezone.utc).isoformat()
        state["last_sync"] = now
        state["last_policy_check"] = now
        state["synced_chunks"] = {
            c["id"]: hash(c["text"]) for c in chunks
        }
        save_sync_state(state)
        print(f"\n6. Saved sync state")

    # Final stats
    if not dry_run:
        stats = index.describe_index_stats()
        print(f"\n" + "=" * 60)
        print(f"✅ Sync complete!")
        print(f"   Total vectors: {stats.total_vector_count}")
        for ns, ns_stats in stats.namespaces.items():
            print(f"   - {ns}: {ns_stats.vector_count}")
    else:
        print(f"\n" + "=" * 60)
        print(f"DRY RUN complete - no changes made")


def main():
    parser = argparse.ArgumentParser(description="Sync Pinecone vectors with Verity API")
    parser.add_argument("--full", action="store_true", help="Full rebuild (re-embed all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()

    if not PINECONE_API_KEY:
        print("Error: PINECONE_API_KEY not set")
        sys.exit(1)
    if not VOYAGE_API_KEY:
        print("Error: VOYAGE_API_KEY not set")
        sys.exit(1)

    sync(full=args.full, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
