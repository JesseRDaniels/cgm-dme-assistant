#!/usr/bin/env python3
"""
Build Pinecone index from processed chunks using Voyage embeddings.
"""
import json
import time
from pathlib import Path
import sys
import httpx

from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

CHUNKS_FILE = Path(__file__).parent.parent / "data" / "chunks" / "all_chunks.json"

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "cgm-dme")
EMBEDDING_MODEL = "voyage-3-lite"
EMBEDDING_DIMENSIONS = 512  # voyage-3-lite uses 512 dimensions
BATCH_SIZE = 5  # Very small batches to avoid rate limits
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds
RECREATE_INDEX = False  # Set True to delete and recreate


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings using Voyage AI with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {VOYAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": texts,
                    "input_type": "document",
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                print(f"    Rate limited, waiting {RETRY_DELAY}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
                continue
            raise
    return []


def main():
    """Build the Pinecone index."""
    if not PINECONE_API_KEY:
        print("Error: PINECONE_API_KEY not set in .env")
        return

    if not VOYAGE_API_KEY:
        print("Error: VOYAGE_API_KEY not set in .env")
        return

    if not CHUNKS_FILE.exists():
        print(f"Error: Chunks file not found: {CHUNKS_FILE}")
        print("Run process_docs.py first.")
        return

    # Load chunks
    with open(CHUNKS_FILE) as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks)} chunks")

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check/create index
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if INDEX_NAME in existing_indexes:
        if RECREATE_INDEX:
            print(f"Index '{INDEX_NAME}' exists. Deleting and recreating...")
            pc.delete_index(INDEX_NAME)
            time.sleep(5)  # Wait for deletion
        else:
            print(f"Index '{INDEX_NAME}' exists. Adding/updating vectors...")

    if INDEX_NAME not in existing_indexes or RECREATE_INDEX:
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    # Wait for index to be ready
    while True:
        desc = pc.describe_index(INDEX_NAME)
        if desc.status.ready:
            break
        print("Waiting for index to be ready...")
        time.sleep(2)

    index = pc.Index(INDEX_NAME)
    print("Index ready!")

    # Group chunks by type for namespace organization
    type_to_namespace = {
        "lcd_policy": "lcd_policies",
        "hcpcs_code": "hcpcs_codes",
        "denial_reason": "denial_reasons",
    }

    # Process and upsert in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"Processing batch {batch_num}/{total_batches}...")

        # Get embeddings
        texts = [chunk["text"] for chunk in batch]
        try:
            embeddings = get_embeddings(texts)
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            continue

        # Prepare vectors grouped by namespace
        namespace_vectors = {}
        for chunk, embedding in zip(batch, embeddings):
            chunk_type = chunk["metadata"].get("type", "default")
            namespace = type_to_namespace.get(chunk_type, "default")

            if namespace not in namespace_vectors:
                namespace_vectors[namespace] = []

            namespace_vectors[namespace].append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": {
                    **chunk["metadata"],
                    "text": chunk["text"][:1000],  # Truncate for metadata limit
                },
            })

        # Upsert to each namespace
        for namespace, vectors in namespace_vectors.items():
            index.upsert(vectors=vectors, namespace=namespace)
            print(f"  Upserted {len(vectors)} vectors to namespace '{namespace}'")

        # Delay between batches to avoid rate limits
        time.sleep(5)

    # Print index stats
    stats = index.describe_index_stats()
    print(f"\nIndex stats:")
    print(f"  Total vectors: {stats.total_vector_count}")
    for ns, ns_stats in stats.namespaces.items():
        print(f"  Namespace '{ns}': {ns_stats.vector_count} vectors")

    print("\nDone! Index is ready for queries.")


if __name__ == "__main__":
    main()
