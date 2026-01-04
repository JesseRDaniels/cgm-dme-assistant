#!/usr/bin/env python3
"""
Expand Pinecone vectors by pulling more data from Verity API and creating richer chunks.
"""
import json
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

CHUNKS_FILE = Path(__file__).parent.parent / "data" / "chunks" / "all_chunks.json"
VERITY_API_KEY = os.getenv("VERITY_API_KEY")
VERITY_BASE_URL = "https://verity.backworkai.com/api/v1"


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


def get_policy_details(policy_id: str) -> dict:
    """Get full policy with criteria and codes."""
    return verity_request(f"/policies/{policy_id}", {"include": "criteria,codes"})


def get_code_details(code: str) -> dict:
    """Get code with policies."""
    return verity_request("/codes/lookup", {"code": code, "include": "policies,rvu"})


def create_hcpcs_chunks(policy_data: dict) -> list:
    """Create chunks for all HCPCS codes in a policy."""
    chunks = []
    codes = policy_data.get("codes", {}).get("HCPCS", [])

    for code_info in codes:
        code = code_info.get("code", "")
        if not code:
            continue

        # Get detailed code info from Verity
        try:
            details = get_code_details(code)
            description = details.get("description", "No description available")
            short_desc = details.get("short_description", "")
            category = details.get("category", "DME")
        except:
            description = f"CGM/Glucose monitoring related code"
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

        # Create one chunk per section with all items
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
            }
        })

        # Also create individual chunks for key criteria
        for i, item in enumerate(items[:5]):  # Top 5 per section
            item_text = item.get("text", "")
            if len(item_text) > 100:  # Only substantial items
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
            "resolution": "Verify patient has qualifying diabetes diagnosis. If correct diagnosis exists, rebill with proper ICD-10 code. If patient doesn't have diabetes, CGM is not covered.",
            "appeal_strategy": "Submit medical records documenting diabetes diagnosis. Include A1C results, treatment history, and physician attestation of diabetes mellitus.",
        },
        {
            "code": "CO-197",
            "description": "Precertification/authorization/notification absent",
            "cgm_causes": "Prior authorization was required but not obtained before dispensing CGM equipment or supplies.",
            "resolution": "Obtain prior authorization if still within timely filing. Some MACs allow retroactive authorization within 14 days.",
            "appeal_strategy": "Request retroactive authorization. Submit all medical necessity documentation with appeal showing patient met criteria at time of service.",
        },
        {
            "code": "PR-204",
            "description": "This service/equipment/drug is not covered under the patient's current benefit plan",
            "cgm_causes": "Patient may not have Part B DME coverage, or CGM benefit may be exhausted.",
            "resolution": "Verify patient's Medicare Part B enrollment and DME benefit status. Check if patient has secondary insurance.",
            "appeal_strategy": "Verify eligibility. If patient has coverage, appeal with eligibility documentation. Consider ABN for patient liability.",
        },
        {
            "code": "CO-96",
            "description": "Non-covered charge(s) / Not medically necessary",
            "cgm_causes": "CGM not deemed medically necessary. Patient may not meet LCD L33822 criteria (insulin treatment, training documented, face-to-face visit).",
            "resolution": "Review LCD L33822 criteria. Ensure documentation supports: diabetes diagnosis, insulin treatment (or problematic hypoglycemia), training, and 6-month visit.",
            "appeal_strategy": "Submit comprehensive documentation package: progress notes showing diabetes and insulin treatment, training records, face-to-face attestation, and letter of medical necessity.",
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
            "resolution": "Generally cannot be appealed. Consider if any exceptions apply (retroactive eligibility, natural disaster, etc.).",
            "appeal_strategy": "If exception applies, document the circumstances that prevented timely filing. Otherwise, write off the claim.",
        },
        {
            "code": "CO-50",
            "description": "Non-covered service / not a Medicare benefit",
            "cgm_causes": "Specific CGM model not covered, or service billed is not a DME benefit.",
            "resolution": "Verify CGM device is FDA-approved and listed on PDAC Product Classification List. Check HCPCS coding is correct.",
            "appeal_strategy": "Submit PDAC documentation, FDA clearance letter, and manufacturer specifications showing device meets Medicare criteria.",
        },
        {
            "code": "CO-119",
            "description": "Benefit maximum for this time period has been reached",
            "cgm_causes": "Patient has already received maximum allowable CGM supplies for the billing period.",
            "resolution": "Review utilization. CGM supplies are typically 1 month supply at a time, 3 months max per delivery. Check for duplicate billing.",
            "appeal_strategy": "If utilization is appropriate, submit documentation justifying medical necessity for higher utilization. May need treating physician attestation.",
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
            }
        })

    return chunks


def create_documentation_chunks() -> list:
    """Create chunks about documentation requirements."""
    docs = [
        {
            "id": "doc_dwo_requirements",
            "title": "Detailed Written Order (DWO) Requirements",
            "content": """A Detailed Written Order (DWO) is required for all CGM claims. The DWO must be received by the supplier before submitting a claim.

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
• Prescriber must have conducted face-to-face visit within 6 months

Common DWO Errors:
• Missing prescriber signature or date
• Using verbal order without written follow-up
• Missing quantity or length of need
• Incomplete device description"""
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
• Visit must evaluate glycemic control and verify CGM adherence
• If 6-month visit requirement not met, CGM and supplies will be denied

Documentation Requirements:
• Date of face-to-face encounter
• Practitioner's attestation of the visit
• Evaluation of diabetes management
• Verification of CGM training and proper use
• Documentation of continued medical necessity

Telehealth Visits:
• Must be Medicare-approved telehealth service
• Must meet all telehealth requirements (originating site, etc.)
• Documentation must specify telehealth modality used"""
        },
        {
            "id": "doc_medical_necessity",
            "title": "Medical Necessity Documentation for CGM",
            "content": """To establish medical necessity for CGM under LCD L33822, documentation must support:

1. Diabetes Diagnosis:
• ICD-10 codes: E10.x (Type 1), E11.x (Type 2), E13.x (Other specified), O24.x (Gestational)
• Documented in medical records with clinical findings

2. Insulin Treatment OR Problematic Hypoglycemia:
• For insulin users: Document type of insulin, frequency, and dosing regimen
• For non-insulin CGM: Document history of problematic hypoglycemia requiring intervention

3. Training and Competency:
• Patient (or caregiver) received training on the CGM device
• Documentation of training date and trainer
• Evidence of competency in device use

4. Prescriber Attestation:
• Statement that CGM is medically necessary
• Certification that all LCD criteria are met
• Signature and date

5. FDA Indications:
• CGM must be prescribed in accordance with FDA-approved indications
• Device must be on PDAC Product Classification List"""
        },
        {
            "id": "doc_refill_requirements",
            "title": "CGM Refill and Resupply Documentation",
            "content": """Medicare has specific requirements for CGM refills and resupply under LCD L33822.

Refill Contact Requirements:
• Supplier must contact beneficiary (or caregiver) before dispensing refills
• Contact must occur no sooner than 30 calendar days before expected supply end
• Must obtain affirmative refill request from beneficiary

Delivery Timing:
• Refills cannot be delivered sooner than 10 calendar days before expected supply end
• Cannot deliver more than 90-day supply at one time

Documentation Required:
• Date of refill contact
• Method of contact (phone, email, etc.)
• Beneficiary's affirmative response
• Delivery date
• Quantity dispensed

Automatic Shipment Prohibited:
• Cannot use auto-ship without beneficiary's affirmative request each time
• Pre-authorized recurring orders do not satisfy requirement

Proof of Delivery:
• Must maintain POD documentation
• POD must be available upon MAC request"""
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
            }
        })

    return chunks


def create_appeal_chunks() -> list:
    """Create chunks about appeal strategies."""
    appeals = [
        {
            "id": "appeal_general_strategy",
            "title": "General CGM Denial Appeal Strategy",
            "content": """When appealing a CGM denial, follow this structured approach:

1. Identify the Denial Reason:
• Review the EOB/remittance for specific denial code
• Understand exactly what criteria was not met

2. Gather Documentation:
• Complete medical records from 6 months prior to order
• Detailed Written Order (DWO)
• Face-to-face visit documentation
• A1C and glucose records
• Insulin treatment records
• Training documentation

3. Draft Appeal Letter:
• Reference specific LCD L33822 criteria
• Address each denial reason specifically
• Include physician attestation of medical necessity
• Cite relevant policy language

4. Submit Appeal:
• Level 1: Redetermination (within 120 days)
• Level 2: Reconsideration by QIC (within 180 days)
• Level 3: ALJ hearing (if amount in controversy met)

5. Follow Up:
• Track appeal status
• Respond promptly to additional information requests
• Document all communications"""
        },
        {
            "id": "appeal_medical_necessity",
            "title": "Appealing Medical Necessity Denials (CO-96)",
            "content": """For medical necessity denials on CGM claims, the appeal must demonstrate all LCD L33822 criteria are met:

Required Documentation:
1. Diabetes Diagnosis:
   • Lab results (A1C, fasting glucose)
   • Clinical notes documenting diabetes

2. Insulin Treatment:
   • Prescription records
   • Progress notes showing insulin regimen
   • Or: documentation of problematic hypoglycemia

3. Face-to-Face Visit:
   • Visit note within 6 months of order
   • Attestation from prescriber

4. CGM-Specific Training:
   • Training record with date
   • Prescriber statement of patient competency

5. Letter of Medical Necessity:
   • Why CGM is needed for this patient
   • How it differs from standard glucose monitoring
   • Expected clinical benefits

Sample Appeal Language:
"Patient [Name] meets all criteria for CGM coverage under LCD L33822. As documented in the attached records, the patient has [Type 1/Type 2] diabetes mellitus, is treated with [insulin regimen], completed CGM training on [date], and had a face-to-face visit on [date] during which the prescribing physician determined CGM is medically necessary for optimal glycemic management."""
        },
    ]

    chunks = []
    for appeal in appeals:
        chunks.append({
            "id": appeal["id"],
            "text": f"""{appeal['title']}

{appeal['content']}""",
            "metadata": {
                "source": "Appeal Strategy Guide",
                "title": appeal["title"],
                "type": "appeal_strategy",
                "category": "Appeals",
            }
        })

    return chunks


def main():
    """Generate expanded chunks."""
    print("Expanding vector database...")

    all_chunks = []

    # Get L33822 policy details from Verity
    print("\n1. Fetching LCD L33822 from Verity API...")
    try:
        policy = get_policy_details("L33822")
        print(f"   Got policy: {policy.get('title')}")

        # Create HCPCS code chunks
        print("\n2. Creating HCPCS code chunks...")
        hcpcs_chunks = create_hcpcs_chunks(policy)
        all_chunks.extend(hcpcs_chunks)
        print(f"   Created {len(hcpcs_chunks)} HCPCS chunks")

        # Create criteria chunks
        print("\n3. Creating coverage criteria chunks...")
        criteria_chunks = create_criteria_chunks(policy)
        all_chunks.extend(criteria_chunks)
        print(f"   Created {len(criteria_chunks)} criteria chunks")

    except Exception as e:
        print(f"   Error fetching policy: {e}")
        print("   Using fallback data...")

    # Create denial code chunks
    print("\n4. Creating denial code chunks...")
    denial_chunks = create_denial_chunks()
    all_chunks.extend(denial_chunks)
    print(f"   Created {len(denial_chunks)} denial chunks")

    # Create documentation requirement chunks
    print("\n5. Creating documentation requirement chunks...")
    doc_chunks = create_documentation_chunks()
    all_chunks.extend(doc_chunks)
    print(f"   Created {len(doc_chunks)} documentation chunks")

    # Create appeal strategy chunks
    print("\n6. Creating appeal strategy chunks...")
    appeal_chunks = create_appeal_chunks()
    all_chunks.extend(appeal_chunks)
    print(f"   Created {len(appeal_chunks)} appeal chunks")

    # Save chunks
    print(f"\n7. Saving {len(all_chunks)} total chunks...")
    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_FILE, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nDone! Saved to {CHUNKS_FILE}")
    print(f"\nChunk breakdown:")
    type_counts = {}
    for chunk in all_chunks:
        t = chunk["metadata"].get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    print(f"\nNext step: Run build_index.py to update Pinecone")


if __name__ == "__main__":
    main()
