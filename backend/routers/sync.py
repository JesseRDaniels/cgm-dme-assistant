"""Sync router for vector database updates with Postgres snapshots."""
import time
import httpx
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config import get_settings
from services.pinecone_client import upsert_vectors
from services.database import (
    save_snapshot, activate_snapshot, get_active_snapshot, get_snapshot,
    list_snapshots, record_sync_start, record_sync_complete, record_sync_error,
    record_sync_paused, get_sync_history, is_database_ready
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])

# Safety threshold: pause if more than 30% of vectors would change
SAFETY_THRESHOLD_PERCENT = 30

# Namespace mapping
TYPE_TO_NAMESPACE = {
    "lcd_policy": "lcd_policies",
    "hcpcs_code": "hcpcs_codes",
    "denial_reason": "denial_reasons",
    "documentation": "default",
    "appeal_strategy": "default",
}

# Verity API config
VERITY_BASE_URL = "https://verity.backworkai.com/api/v1"

# Backend URL for links in Slack messages
BACKEND_URL = "https://cgm-dme-assistant-production.up.railway.app"


def send_slack_notification(message: str, emoji: str = "🔄", color: str = None):
    """Send notification to Slack webhook."""
    settings = get_settings()
    if not settings.slack_webhook_url:
        return

    try:
        payload = {
            "text": f"{emoji} *CGM DME Sync*",
            "attachments": [
                {
                    "color": color or "#36a64f",
                    "text": message,
                    "footer": "CGM DME Assistant",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        httpx.post(settings.slack_webhook_url, json=payload, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to send Slack notification: {e}")


def notify_sync_success(snapshot_id: str, chunks: int, duration: float, changes: dict):
    """Notify Slack of successful sync."""
    added = changes.get("added", 0)
    updated = changes.get("updated", 0)
    removed = changes.get("removed", 0)

    if added == 0 and updated == 0 and removed == 0:
        message = f"No changes detected. Content unchanged.\n`{snapshot_id}`"
        send_slack_notification(message, "✅", "#36a64f")
    else:
        message = (
            f"Synced *{chunks}* vectors in {duration:.1f}s\n"
            f"• Added: {added}\n• Updated: {updated}\n• Removed: {removed}\n"
            f"`{snapshot_id}`"
        )
        send_slack_notification(message, "✅", "#36a64f")


def notify_sync_paused(snapshot_id: str, change_percent: float, changes: dict):
    """Notify Slack that sync was paused due to safety threshold."""
    message = (
        f"⚠️ *Sync paused* - {change_percent:.1f}% change exceeds {SAFETY_THRESHOLD_PERCENT}% threshold\n"
        f"• Added: {changes.get('added', 0)}\n"
        f"• Updated: {changes.get('updated', 0)}\n"
        f"• Removed: {changes.get('removed', 0)}\n\n"
        f"To approve:\n```\ncurl -X POST {BACKEND_URL}/api/sync/approve/{snapshot_id}\n```"
    )
    send_slack_notification(message, "⚠️", "#ff9800")


def notify_sync_failed(error: str):
    """Notify Slack of sync failure."""
    message = f"Sync failed:\n```{error[:500]}```"
    send_slack_notification(message, "❌", "#dc3545")


class SyncStatus(BaseModel):
    status: str
    last_sync: str | None
    total_chunks: int
    active_snapshot: str | None
    database_ready: bool
    message: str


class SyncResult(BaseModel):
    status: str
    snapshot_id: str | None
    chunks_updated: int
    duration_seconds: float
    message: str
    changes: dict | None = None


class SnapshotInfo(BaseModel):
    snapshot_id: str
    created_at: str
    deployed_at: str | None
    chunk_count: int
    is_active: bool


class RollbackResult(BaseModel):
    status: str
    rolled_back_to: str
    chunks_restored: int
    message: str


# --- Verity API Functions ---

def verity_request(endpoint: str, params: dict = None) -> dict:
    """Make request to Verity API."""
    settings = get_settings()
    resp = httpx.get(
        f"{VERITY_BASE_URL}{endpoint}",
        headers={"Authorization": f"Bearer {settings.verity_api_key}"},
        params=params or {},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", data)


def get_policy_details(policy_id: str) -> dict:
    """Get full policy with criteria and codes."""
    return verity_request(f"/policies/{policy_id}", {"include": "criteria,codes"})


def get_code_details(code: str) -> dict:
    """Get code with policies."""
    return verity_request("/codes/lookup", {"code": code, "include": "policies,rvu"})


# --- Chunk Creation Functions ---

def create_hcpcs_chunks(policy_data: dict) -> list:
    """Create chunks for all HCPCS codes in a policy."""
    chunks = []
    codes = policy_data.get("codes", {}).get("HCPCS", [])

    for code_info in codes:
        code = code_info.get("code", "")
        if not code:
            continue

        try:
            details = get_code_details(code)
            description = details.get("description", "No description available")
            short_desc = details.get("short_description", "")
            category = details.get("category", "DME")
        except Exception:
            description = "CGM/Glucose monitoring related code"
            short_desc = ""
            category = "DME"

        text = f"""HCPCS Code: {code}
Description: {description}
{f'Short Description: {short_desc}' if short_desc else ''}
Category: {category}
Coverage: {code_info.get('disposition', 'covered').title()} under LCD L33822
Policy: Glucose Monitors - Medicare Part B DME benefit

Billing Requirements:
- Requires KX modifier to certify medical necessity
- Must have diabetes diagnosis (E10.x, E11.x, E13.x, O24.x)
- Documentation must support LCD L33822 criteria
- Face-to-face visit within 6 months for CGM codes"""

        chunks.append({
            "id": f"hcpcs_{code}",
            "text": text.strip(),
            "metadata": {
                "source": "Verity API + LCD L33822",
                "code": code,
                "category": category,
                "type": "hcpcs_code",
                "policy_id": "L33822",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })

    return chunks


def create_criteria_chunks(policy_data: dict) -> list:
    """Create chunks for each coverage criteria section."""
    chunks = []
    criteria = policy_data.get("criteria", {})
    policy_id = policy_data.get("policy_id", "L33822")
    title = policy_data.get("title", "Glucose Monitors")

    section_descriptions = {
        "documentation": "Documentation Requirements",
        "frequency": "Frequency and Quantity Limits",
        "indications": "Coverage Indications",
        "limitations": "Coverage Limitations and Exclusions",
    }

    for section, items in criteria.items():
        if not items:
            continue

        section_title = section_descriptions.get(section, section.title())

        items_text = "\n\n".join([
            f"• {item.get('text', '')}"
            for item in items
        ])

        text = f"""LCD {policy_id}: {title}
Section: {section_title}

{items_text}

Tags: {', '.join(set(tag for item in items for tag in item.get('tags', [])))}"""

        chunks.append({
            "id": f"lcd_{policy_id}_{section}",
            "text": text.strip(),
            "metadata": {
                "source": f"LCD {policy_id}",
                "policy_id": policy_id,
                "section": section,
                "type": "lcd_policy",
                "category": section_title,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })

        # Individual chunks for key criteria
        for i, item in enumerate(items[:5]):
            item_text = item.get("text", "")
            if len(item_text) > 100:
                chunks.append({
                    "id": f"lcd_{policy_id}_{section}_{i}",
                    "text": f"""LCD {policy_id} - {section_title}

{item_text}

Related Tags: {', '.join(item.get('tags', []))}""",
                    "metadata": {
                        "source": f"LCD {policy_id}",
                        "policy_id": policy_id,
                        "section": section,
                        "type": "lcd_policy",
                        "block_id": item.get("block_id", ""),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                })

    return chunks


def create_denial_chunks() -> list:
    """Create chunks for common denial codes with resolution strategies."""
    denials = [
        {
            "code": "CO-4",
            "description": "Procedure code inconsistent with modifier or required modifier missing",
            "cgm_causes": "Missing KX modifier. CGM claims require KX to certify medical necessity documentation is on file.",
            "resolution": "Add KX modifier. Verify medical necessity documentation meets LCD L33822 criteria. Rebill with corrected modifier.",
            "appeal_strategy": "Submit copy of medical records showing diabetes diagnosis, insulin treatment, and prescriber attestation of medical necessity.",
        },
        {
            "code": "CO-16",
            "description": "Claim/service lacks information needed for adjudication",
            "cgm_causes": "Missing diagnosis code, incomplete patient demographics, missing referring physician NPI, or incomplete order.",
            "resolution": "Review claim for completeness. Add missing ICD-10 diabetes diagnosis, verify all NPIs, ensure complete Detailed Written Order on file.",
            "appeal_strategy": "Submit corrected claim with all required fields. Include copy of DWO if order completeness was the issue.",
        },
        {
            "code": "CO-167",
            "description": "Diagnosis not covered / doesn't support medical necessity",
            "cgm_causes": "Non-diabetic diagnosis submitted, or ICD-10 code doesn't qualify under LCD L33822 (must be E10.x, E11.x, E13.x, or O24.x).",
            "resolution": "Verify patient has qualifying diabetes diagnosis. If correct diagnosis exists, rebill with proper ICD-10 code.",
            "appeal_strategy": "Submit medical records documenting diabetes diagnosis. Include A1C results, treatment history, and physician attestation.",
        },
        {
            "code": "CO-197",
            "description": "Precertification/authorization/notification absent",
            "cgm_causes": "Prior authorization was required but not obtained before dispensing CGM equipment or supplies.",
            "resolution": "Obtain prior authorization if still within timely filing. Some MACs allow retroactive authorization within 14 days.",
            "appeal_strategy": "Request retroactive authorization. Submit all medical necessity documentation with appeal.",
        },
        {
            "code": "PR-204",
            "description": "This service/equipment/drug is not covered under the patient's current benefit plan",
            "cgm_causes": "Patient may not have Part B DME coverage, or CGM benefit may be exhausted.",
            "resolution": "Verify patient's Medicare Part B enrollment and DME benefit status. Check if patient has secondary insurance.",
            "appeal_strategy": "Verify eligibility. If patient has coverage, appeal with eligibility documentation.",
        },
        {
            "code": "CO-96",
            "description": "Non-covered charge(s) / Not medically necessary",
            "cgm_causes": "CGM not deemed medically necessary. Patient may not meet LCD L33822 criteria.",
            "resolution": "Review LCD L33822 criteria. Ensure documentation supports: diabetes diagnosis, insulin treatment, training, and 6-month visit.",
            "appeal_strategy": "Submit comprehensive documentation package: progress notes, training records, face-to-face attestation, and letter of medical necessity.",
        },
        {
            "code": "CO-27",
            "description": "Expenses incurred after coverage terminated",
            "cgm_causes": "Service date is after patient's Medicare coverage ended or before it began.",
            "resolution": "Verify patient eligibility on date of service. If coverage was active, provide eligibility documentation.",
            "appeal_strategy": "Submit eligibility verification from CMS or MAC showing active coverage on service date.",
        },
        {
            "code": "CO-29",
            "description": "Time limit for filing has expired",
            "cgm_causes": "Claim submitted after Medicare's 12-month timely filing deadline.",
            "resolution": "Generally cannot be appealed. Consider if any exceptions apply.",
            "appeal_strategy": "If exception applies, document the circumstances that prevented timely filing.",
        },
        {
            "code": "CO-50",
            "description": "Non-covered service / not a Medicare benefit",
            "cgm_causes": "Specific CGM model not covered, or service billed is not a DME benefit.",
            "resolution": "Verify CGM device is FDA-approved and listed on PDAC Product Classification List.",
            "appeal_strategy": "Submit PDAC documentation, FDA clearance letter, and manufacturer specifications.",
        },
        {
            "code": "CO-119",
            "description": "Benefit maximum for this time period has been reached",
            "cgm_causes": "Patient has already received maximum allowable CGM supplies for the billing period.",
            "resolution": "Review utilization. CGM supplies are typically 1 month supply at a time, 3 months max per delivery.",
            "appeal_strategy": "If utilization is appropriate, submit documentation justifying medical necessity for higher utilization.",
        },
    ]

    chunks = []
    for denial in denials:
        text = f"""Denial Code: {denial['code']}
Description: {denial['description']}

Common Causes for CGM/DME Claims:
{denial['cgm_causes']}

Resolution Steps:
{denial['resolution']}

Appeal Strategy:
{denial['appeal_strategy']}

Related LCD: L33822 (Glucose Monitors)
Applies to: CGM supplies (K0553, A9276-A9278) and blood glucose monitors"""

        chunks.append({
            "id": f"denial_{denial['code'].replace('-', '_')}",
            "text": text.strip(),
            "metadata": {
                "source": "Denial Code Reference",
                "denial_code": denial["code"],
                "type": "denial_reason",
                "category": "Claims Resolution",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })

    return chunks


def create_documentation_chunks() -> list:
    """Create chunks about documentation requirements."""
    docs = [
        {
            "id": "doc_dwo_requirements",
            "title": "Detailed Written Order (DWO) Requirements",
            "content": """A Detailed Written Order (DWO) is required for all CGM claims.

Required Elements:
• Patient's name, address, and date of birth
• Date of the order
• Prescriber's name, NPI, and signature
• Detailed description of the item (CGM device name, model)
• Quantity to be dispensed
• Diagnosis code (ICD-10)
• Length of need (if not lifetime)

For CGM specifically:
• Must specify the CGM system being ordered
• Must include statement of medical necessity
• Prescriber must have conducted face-to-face visit within 6 months"""
        },
        {
            "id": "doc_face_to_face",
            "title": "Face-to-Face Visit Requirements for CGM",
            "content": """Medicare requires a face-to-face encounter for CGM coverage under LCD L33822.

Initial CGM Order:
• Treating practitioner must have a face-to-face visit within 6 months PRIOR to the initial CGM order
• Visit can be in-person OR Medicare-approved telehealth

Continued Coverage:
• Every 6 months thereafter, patient must have face-to-face visit
• Visit must evaluate glycemic control and verify CGM adherence"""
        },
        {
            "id": "doc_medical_necessity",
            "title": "Medical Necessity Documentation for CGM",
            "content": """To establish medical necessity for CGM under LCD L33822:

1. Diabetes Diagnosis: ICD-10 codes E10.x (Type 1), E11.x (Type 2), E13.x (Other specified), O24.x (Gestational)
2. Insulin Treatment OR Problematic Hypoglycemia
3. Training and Competency documentation
4. Prescriber Attestation
5. FDA Indications compliance"""
        },
        {
            "id": "doc_refill_requirements",
            "title": "CGM Refill and Resupply Documentation",
            "content": """Medicare requirements for CGM refills:

• Contact beneficiary no sooner than 30 days before supply end
• Obtain affirmative refill request
• Deliver no sooner than 10 days before supply end
• Maximum 90-day supply per delivery
• No automatic shipments without affirmative request"""
        },
    ]

    chunks = []
    for doc in docs:
        chunks.append({
            "id": doc["id"],
            "text": f"""{doc['title']}

{doc['content']}""",
            "metadata": {
                "source": "Documentation Requirements Guide",
                "title": doc["title"],
                "type": "documentation",
                "category": "Compliance",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        })

    return chunks


def create_appeal_chunks() -> list:
    """Create chunks about appeal strategies."""
    chunks = [
        {
            "id": "appeal_general_strategy",
            "text": """General CGM Denial Appeal Strategy

1. Identify the Denial Reason from EOB/remittance
2. Gather Documentation: medical records, DWO, face-to-face visit, A1C, insulin records, training docs
3. Draft Appeal Letter referencing LCD L33822 criteria
4. Submit Appeal: Level 1 (120 days), Level 2 QIC (180 days), Level 3 ALJ
5. Track and follow up on appeal status""",
            "metadata": {
                "source": "Appeal Strategy Guide",
                "title": "General CGM Denial Appeal Strategy",
                "type": "appeal_strategy",
                "category": "Appeals",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        {
            "id": "appeal_medical_necessity",
            "text": """Appealing Medical Necessity Denials (CO-96)

Required Documentation:
1. Diabetes Diagnosis: Lab results (A1C, fasting glucose), clinical notes
2. Insulin Treatment: Prescription records, progress notes
3. Face-to-Face Visit: Visit note within 6 months, attestation
4. CGM Training: Training record with date, competency statement
5. Letter of Medical Necessity: Why CGM is needed, expected benefits""",
            "metadata": {
                "source": "Appeal Strategy Guide",
                "title": "Appealing Medical Necessity Denials",
                "type": "appeal_strategy",
                "category": "Appeals",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    ]
    return chunks


# --- Embedding Functions ---

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


# --- Main Sync Functions ---

async def fetch_fresh_chunks() -> list:
    """Fetch fresh data from Verity API and create chunks."""
    all_chunks = []

    # Fetch L33822 policy from Verity
    logger.info("Fetching LCD L33822 from Verity API...")
    try:
        policy = get_policy_details("L33822")
        logger.info(f"Got policy: {policy.get('title')}")

        # Create HCPCS code chunks
        hcpcs_chunks = create_hcpcs_chunks(policy)
        all_chunks.extend(hcpcs_chunks)
        logger.info(f"Created {len(hcpcs_chunks)} HCPCS chunks")

        # Create criteria chunks
        criteria_chunks = create_criteria_chunks(policy)
        all_chunks.extend(criteria_chunks)
        logger.info(f"Created {len(criteria_chunks)} criteria chunks")

    except Exception as e:
        logger.error(f"Error fetching policy from Verity: {e}")
        # Continue with static chunks

    # Create denial code chunks (static data)
    denial_chunks = create_denial_chunks()
    all_chunks.extend(denial_chunks)
    logger.info(f"Created {len(denial_chunks)} denial chunks")

    # Create documentation chunks (static data)
    doc_chunks = create_documentation_chunks()
    all_chunks.extend(doc_chunks)
    logger.info(f"Created {len(doc_chunks)} documentation chunks")

    # Create appeal chunks (static data)
    appeal_chunks = create_appeal_chunks()
    all_chunks.extend(appeal_chunks)
    logger.info(f"Created {len(appeal_chunks)} appeal chunks")

    return all_chunks


def calculate_change_percent(old_count: int, changes: dict) -> float:
    """Calculate the percentage of vectors that would change."""
    if old_count == 0:
        return 0.0
    total_changes = changes.get("added", 0) + changes.get("updated", 0) + changes.get("removed", 0)
    return (total_changes / old_count) * 100


async def deploy_to_pinecone(chunks: list) -> int:
    """Deploy chunks to Pinecone. Returns count of vectors upserted."""
    # Group by namespace
    by_namespace = {}
    for chunk in chunks:
        chunk_type = chunk["metadata"].get("type", "default")
        namespace = TYPE_TO_NAMESPACE.get(chunk_type, "default")
        if namespace not in by_namespace:
            by_namespace[namespace] = []
        by_namespace[namespace].append(chunk)

    total_upserted = 0

    for namespace, ns_chunks in by_namespace.items():
        logger.info(f"Upserting {len(ns_chunks)} chunks to {namespace}")

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
            total_upserted += len(vectors)
            time.sleep(3)  # Rate limit

    return total_upserted


async def do_sync(
    full: bool = False,
    force: bool = False,
    triggered_by: str = "manual"
) -> SyncResult:
    """
    Perform sync operation with Postgres snapshots.

    1. Fetch fresh data from Verity API
    2. Compare with current snapshot
    3. Check safety threshold (>30% change = pause)
    4. Save new snapshot to Postgres
    5. Deploy to Pinecone
    6. Activate new snapshot
    """
    start_time = time.time()

    # Check if database is ready
    if not await is_database_ready():
        return SyncResult(
            status="error",
            snapshot_id=None,
            chunks_updated=0,
            duration_seconds=time.time() - start_time,
            message="Database not initialized"
        )

    # Record sync start
    sync_id = await record_sync_start(triggered_by)

    try:
        # Fetch fresh chunks
        logger.info("Fetching fresh chunks from Verity...")
        new_chunks = await fetch_fresh_chunks()

        if not new_chunks:
            await record_sync_error(sync_id, "No chunks generated")
            return SyncResult(
                status="error",
                snapshot_id=None,
                chunks_updated=0,
                duration_seconds=time.time() - start_time,
                message="No chunks generated from Verity API"
            )

        logger.info(f"Generated {len(new_chunks)} total chunks")

        # Save snapshot
        snapshot_result = await save_snapshot(
            chunks=new_chunks,
            metadata={"triggered_by": triggered_by, "full_sync": full}
        )

        if snapshot_result["status"] == "unchanged":
            await record_sync_complete(sync_id, snapshot_result["snapshot_id"], 0, 0, 0)
            return SyncResult(
                status="success",
                snapshot_id=snapshot_result["snapshot_id"],
                chunks_updated=0,
                duration_seconds=time.time() - start_time,
                message="Content unchanged, no update needed"
            )

        snapshot_id = snapshot_result["snapshot_id"]
        changes = snapshot_result.get("changes", {})

        # Get current active snapshot for safety check
        active = await get_active_snapshot()
        old_count = active["chunk_count"] if active else 0

        # Safety threshold check
        if old_count > 0 and not force:
            change_percent = calculate_change_percent(old_count, changes)
            if change_percent > SAFETY_THRESHOLD_PERCENT:
                reason = f"Safety threshold exceeded: {change_percent:.1f}% change (threshold: {SAFETY_THRESHOLD_PERCENT}%)"
                logger.warning(reason)
                await record_sync_paused(sync_id, reason)
                notify_sync_paused(snapshot_id, change_percent, changes)
                return SyncResult(
                    status="paused",
                    snapshot_id=snapshot_id,
                    chunks_updated=0,
                    duration_seconds=time.time() - start_time,
                    message=reason,
                    changes=changes
                )

        # Deploy to Pinecone
        logger.info("Deploying to Pinecone...")
        total_upserted = await deploy_to_pinecone(new_chunks)

        # Activate snapshot
        await activate_snapshot(snapshot_id)

        # Record success
        await record_sync_complete(
            sync_id,
            snapshot_id,
            changes.get("added", 0),
            changes.get("updated", 0),
            changes.get("removed", 0)
        )

        duration = time.time() - start_time
        notify_sync_success(snapshot_id, total_upserted, duration, changes)

        return SyncResult(
            status="success",
            snapshot_id=snapshot_id,
            chunks_updated=total_upserted,
            duration_seconds=duration,
            message=f"Synced {total_upserted} vectors",
            changes=changes
        )

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        await record_sync_error(sync_id, str(e))
        notify_sync_failed(str(e))
        raise HTTPException(status_code=500, detail=str(e))


# --- API Endpoints ---

@router.get("/status", response_model=SyncStatus)
async def get_sync_status():
    """Get current sync status including snapshot info."""
    db_ready = await is_database_ready()
    active = await get_active_snapshot() if db_ready else None

    history = await get_sync_history(limit=1) if db_ready else []
    last_sync = history[0]["completed_at"] if history else None

    return SyncStatus(
        status="ok" if db_ready else "degraded",
        last_sync=last_sync,
        total_chunks=active["chunk_count"] if active else 0,
        active_snapshot=active["snapshot_id"] if active else None,
        database_ready=db_ready,
        message="Ready" if db_ready else "Database not initialized"
    )


@router.post("/run", response_model=SyncResult)
async def run_sync(
    full: bool = False,
    force: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Trigger a sync operation.

    - **full**: If true, re-embed all chunks
    - **force**: If true, bypass safety threshold

    This endpoint is designed to be called by Railway cron.
    """
    return await do_sync(full=full, force=force, triggered_by="api")


@router.get("/snapshots", response_model=list[SnapshotInfo])
async def list_all_snapshots(limit: int = 10):
    """List recent snapshots."""
    snapshots = await list_snapshots(limit=limit)
    return [
        SnapshotInfo(
            snapshot_id=s["snapshot_id"],
            created_at=s["created_at"],
            deployed_at=s["deployed_at"],
            chunk_count=s["chunk_count"],
            is_active=s["is_active"]
        )
        for s in snapshots
    ]


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot_details(snapshot_id: str):
    """Get details of a specific snapshot."""
    snapshot = await get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


@router.post("/rollback/{snapshot_id}", response_model=RollbackResult)
async def rollback_to_snapshot(snapshot_id: str):
    """
    Rollback to a previous snapshot.

    This will:
    1. Load the specified snapshot's chunks
    2. Re-deploy them to Pinecone
    3. Mark the snapshot as active
    """
    # Get the snapshot
    snapshot = await get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    if snapshot["is_active"]:
        return RollbackResult(
            status="no_change",
            rolled_back_to=snapshot_id,
            chunks_restored=snapshot["chunk_count"],
            message="Snapshot is already active"
        )

    # Record rollback sync
    sync_id = await record_sync_start("rollback")

    try:
        # Deploy snapshot chunks to Pinecone
        chunks = snapshot["chunks"]
        total_upserted = await deploy_to_pinecone(chunks)

        # Activate the snapshot
        await activate_snapshot(snapshot_id)

        await record_sync_complete(sync_id, snapshot_id, 0, total_upserted, 0)

        return RollbackResult(
            status="success",
            rolled_back_to=snapshot_id,
            chunks_restored=total_upserted,
            message=f"Successfully rolled back to {snapshot_id}"
        )

    except Exception as e:
        await record_sync_error(sync_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 20):
    """Get sync operation history."""
    return await get_sync_history(limit=limit)


@router.post("/approve/{snapshot_id}", response_model=SyncResult)
async def approve_paused_sync(snapshot_id: str):
    """
    Approve a paused sync and deploy the snapshot.

    Use this when a sync was paused due to safety threshold.
    """
    snapshot = await get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    if snapshot["is_active"]:
        return SyncResult(
            status="no_change",
            snapshot_id=snapshot_id,
            chunks_updated=0,
            duration_seconds=0,
            message="Snapshot is already active"
        )

    sync_id = await record_sync_start("approve")

    try:
        chunks = snapshot["chunks"]
        total_upserted = await deploy_to_pinecone(chunks)
        await activate_snapshot(snapshot_id)

        await record_sync_complete(sync_id, snapshot_id, 0, total_upserted, 0)

        return SyncResult(
            status="success",
            snapshot_id=snapshot_id,
            chunks_updated=total_upserted,
            duration_seconds=0,
            message=f"Approved and deployed {total_upserted} vectors"
        )

    except Exception as e:
        await record_sync_error(sync_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
