#!/usr/bin/env python3
"""
Build Pinecone index from processed chunks.
"""
import json
import asyncio
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

CHUNKS_FILE = Path(__file__).parent.parent / "data" / "chunks" / "all_chunks.json"

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "cgm-dme")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 100


def get_embeddings(texts: list[str], client: OpenAI) -> list[list[float]]:
    """Get embeddings for a batch of texts."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def main():
    """Build the Pinecone index."""
    if not PINECONE_API_KEY:
        print("Error: PINECONE_API_KEY not set in .env")
        return

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set in .env")
        return

    if not CHUNKS_FILE.exists():
        print(f"Error: Chunks file not found: {CHUNKS_FILE}")
        print("Run process_docs.py first.")
        return

    # Load chunks
    with open(CHUNKS_FILE) as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks)} chunks")

    # Initialize clients
    pc = Pinecone(api_key=PINECONE_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    # Check/create index
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if INDEX_NAME in existing_indexes:
        print(f"Index '{INDEX_NAME}' exists. Deleting and recreating...")
        pc.delete_index(INDEX_NAME)
        import time
        time.sleep(5)  # Wait for deletion

    print(f"Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIMENSIONS,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

    # Wait for index to be ready
    import time
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
        print(f"Processing batch {i // BATCH_SIZE + 1}/{(len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE}...")

        # Get embeddings
        texts = [chunk["text"] for chunk in batch]
        embeddings = get_embeddings(texts, openai_client)

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

    # Print index stats
    stats = index.describe_index_stats()
    print(f"\nIndex stats:")
    print(f"  Total vectors: {stats.total_vector_count}")
    for ns, ns_stats in stats.namespaces.items():
        print(f"  Namespace '{ns}': {ns_stats.vector_count} vectors")

    print("\nDone! Index is ready for queries.")


if __name__ == "__main__":
    main()
