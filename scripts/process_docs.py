#!/usr/bin/env python3
"""
Process raw documents into chunks for embedding.
"""
import json
from pathlib import Path
import tiktoken

INPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed"
CHUNKS_DIR = Path(__file__).parent.parent / "data" / "chunks"

# Tokenizer for counting
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    return len(enc.encode(text))


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """
    Chunk text into overlapping segments.

    Returns list of {text, start_char, end_char, token_count}
    """
    if not text:
        return []

    chunks = []
    tokens = enc.encode(text)

    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)

        chunks.append({
            "text": chunk_text,
            "token_count": len(chunk_tokens),
            "start_token": start,
            "end_token": end,
        })

        # Move forward, accounting for overlap
        start = end - overlap
        if start >= len(tokens):
            break

    return chunks


def process_lcd_document(lcd_file: Path) -> list[dict]:
    """Process an LCD JSON file into chunks."""
    with open(lcd_file) as f:
        data = json.load(f)

    if "error" in data:
        print(f"Skipping {lcd_file.name} - has error")
        return []

    chunks = []
    lcd_id = data.get("id", "unknown")
    lcd_name = data.get("name", "Unknown LCD")

    content = data.get("content", {})

    # Process by sections if available
    sections = content.get("sections", {})
    if sections:
        for section_name, section_text in sections.items():
            section_chunks = chunk_text(section_text)
            for i, chunk in enumerate(section_chunks):
                chunks.append({
                    "id": f"{lcd_id}_{section_name.lower().replace(' ', '_')}_{i}",
                    "text": chunk["text"],
                    "metadata": {
                        "source": f"LCD {lcd_id}",
                        "source_name": lcd_name,
                        "section": section_name,
                        "chunk_index": i,
                        "token_count": chunk["token_count"],
                        "type": "lcd_policy",
                    },
                })
    else:
        # Chunk full text
        full_text = content.get("full_text", "")
        if full_text:
            text_chunks = chunk_text(full_text)
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    "id": f"{lcd_id}_full_{i}",
                    "text": chunk["text"],
                    "metadata": {
                        "source": f"LCD {lcd_id}",
                        "source_name": lcd_name,
                        "section": "Full Document",
                        "chunk_index": i,
                        "token_count": chunk["token_count"],
                        "type": "lcd_policy",
                    },
                })

    return chunks


def create_hcpcs_chunks() -> list[dict]:
    """Create chunks for HCPCS codes (hardcoded for now)."""
    # CGM-specific codes with full documentation
    codes = [
        {
            "code": "A9276",
            "description": "Sensor; invasive (e.g., subcutaneous), disposable, for use with interstitial continuous glucose monitoring system, one unit",
            "category": "CGM Supplies",
            "notes": "Consumable sensor, typically replaced every 10-14 days depending on device. Requires KX modifier for medical necessity. Covered under LCD L33822.",
        },
        {
            "code": "A9277",
            "description": "Transmitter; external, for use with interstitial continuous glucose monitoring system",
            "category": "CGM Supplies",
            "notes": "Reusable transmitter component. Replacement frequency varies by device (90 days to 1 year). Requires KX modifier.",
        },
        {
            "code": "A9278",
            "description": "Receiver (monitor); external, for use with interstitial continuous glucose monitoring system",
            "category": "CGM Equipment",
            "notes": "One-time purchase or rental. Many patients use smartphone as receiver. Requires KX modifier. Use NU for purchase, RR for rental.",
        },
        {
            "code": "K0553",
            "description": "Supply allowance for therapeutic continuous glucose monitor (CGM), includes all supplies and accessories, 1 month supply",
            "category": "CGM Monthly Supply",
            "notes": "All-inclusive monthly code. Covers sensor, transmitter supplies for one month. Requires KX modifier. Cannot be billed with A9276/A9277/A9278.",
        },
        {
            "code": "K0554",
            "description": "Receiver (monitor); dedicated, for use with therapeutic glucose continuous monitor system",
            "category": "CGM Equipment",
            "notes": "Receiver for use with K0553 system. One-time purchase. Requires KX modifier.",
        },
    ]

    chunks = []
    for code_info in codes:
        code = code_info["code"]
        text = f"""HCPCS Code: {code}
Description: {code_info['description']}
Category: {code_info['category']}
Billing Notes: {code_info['notes']}"""

        chunks.append({
            "id": f"hcpcs_{code}",
            "text": text,
            "metadata": {
                "source": "HCPCS Code Reference",
                "code": code,
                "category": code_info["category"],
                "type": "hcpcs_code",
            },
        })

    return chunks


def create_denial_chunks() -> list[dict]:
    """Create chunks for common denial reasons."""
    denials = [
        {
            "code": "CO-4",
            "description": "The procedure code is inconsistent with the modifier used or a required modifier is missing.",
            "common_causes": "Missing KX modifier for CGM claims. CGM requires KX to indicate medical necessity documentation is on file.",
            "resolution": "Add KX modifier and ensure medical necessity documentation (LCD L33822 criteria) is on file. Rebill with corrected modifier.",
        },
        {
            "code": "CO-16",
            "description": "Claim/service lacks information needed for adjudication.",
            "common_causes": "Missing diagnosis code, incomplete patient information, or missing referring physician info.",
            "resolution": "Review claim for completeness. Add missing information and rebill. Common fixes: add ICD-10 diabetes diagnosis, verify NPI.",
        },
        {
            "code": "CO-167",
            "description": "This diagnosis is not covered.",
            "common_causes": "Non-diabetic diagnosis, or diagnosis code doesn't support CGM coverage under LCD L33822.",
            "resolution": "Verify patient has qualifying diabetes diagnosis (E10.x, E11.x, E13.x, or O24.x for gestational). If correct diagnosis exists, rebill with proper code. If no qualifying diagnosis, CGM may not be covered.",
        },
        {
            "code": "CO-197",
            "description": "Precertification/authorization was not obtained.",
            "common_causes": "Prior authorization required but not obtained before service date.",
            "resolution": "Submit prior authorization request with medical necessity documentation per LCD L33822. Request retroactive authorization if allowed by payer. May need to appeal if timely filing allows.",
        },
        {
            "code": "PR-204",
            "description": "This service/equipment/drug is not covered under the patient's current benefit plan.",
            "common_causes": "CGM not covered by patient's specific plan, or patient has exhausted benefit.",
            "resolution": "Verify patient's DME benefit coverage. Check if alternate payer exists. May need to bill patient if truly non-covered.",
        },
    ]

    chunks = []
    for denial in denials:
        text = f"""Denial Code: {denial['code']}
Description: {denial['description']}
Common Causes for CGM Claims: {denial['common_causes']}
Resolution Steps: {denial['resolution']}"""

        chunks.append({
            "id": f"denial_{denial['code'].replace('-', '_')}",
            "text": text,
            "metadata": {
                "source": "Denial Code Reference",
                "denial_code": denial["code"],
                "type": "denial_reason",
            },
        })

    return chunks


def main():
    """Process all documents into chunks."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []

    # Process LCD files
    lcd_files = list(INPUT_DIR.glob("lcd_*.json"))
    print(f"Found {len(lcd_files)} LCD files to process")

    for lcd_file in lcd_files:
        chunks = process_lcd_document(lcd_file)
        all_chunks.extend(chunks)
        print(f"Processed {lcd_file.name}: {len(chunks)} chunks")

    # Add HCPCS code chunks
    hcpcs_chunks = create_hcpcs_chunks()
    all_chunks.extend(hcpcs_chunks)
    print(f"Added {len(hcpcs_chunks)} HCPCS code chunks")

    # Add denial code chunks
    denial_chunks = create_denial_chunks()
    all_chunks.extend(denial_chunks)
    print(f"Added {len(denial_chunks)} denial code chunks")

    # Save all chunks
    output_file = CHUNKS_DIR / "all_chunks.json"
    with open(output_file, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
