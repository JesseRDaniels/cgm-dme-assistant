# Medical Record Eligibility Checker - Implementation Plan

## Overview
Add ability to upload medical record PDFs and check patient eligibility against LCD criteria (starting with L33822 for CGM). Uses Claude Vision for extraction and returns detailed pass/fail breakdown with evidence quotes.

## Architecture

```
PDF Upload → PDF-to-Images → Claude Vision Extraction → Eligibility Analysis → Results
```

---

## Phase 1: Backend Core

### 1.1 New Files to Create

| File | Purpose |
|------|---------|
| `backend/services/pdf_vision.py` | PDF-to-image conversion + Claude Vision extraction |
| `backend/services/eligibility_analyzer.py` | Analyze extracted data against LCD criteria |
| `backend/routers/eligibility.py` | Upload, status, results endpoints |
| `backend/prompts/eligibility.py` | Extraction + analysis prompts |

### 1.2 `backend/services/pdf_vision.py`

```python
# Key functions:
async def pdf_to_images(pdf_content: bytes, max_pages: int = 20) -> list[dict]
    # Returns: [{"page_num": 1, "base64_image": "...", "media_type": "image/png"}]
    # Use pymupdf (fitz) - pure Python, no system deps

async def extract_medical_record(images: list[dict]) -> dict
    # Send to Claude Vision with extraction prompt
    # Returns structured patient data (diagnoses, meds, labs, encounters)
```

### 1.3 `backend/routers/eligibility.py`

**Models:**
```python
class CriterionResult(BaseModel):
    criterion_id: str
    criterion_name: str
    status: str  # "met", "not_met", "insufficient_evidence", "partial"
    confidence: float
    evidence_quotes: list[str]
    page_references: list[int]
    explanation: str
    recommendation: Optional[str] = None

class LCDEligibilityResult(BaseModel):
    lcd_id: str
    lcd_title: str
    overall_status: str  # "qualified", "not_qualified", "review_needed"
    criteria_results: list[CriterionResult]
    met_count: int
    total_count: int
    gaps_identified: list[str]
    summary: str

class EligibilityCheckResponse(BaseModel):
    check_id: str
    status: str  # "pending", "processing", "completed", "failed"
    lcd_results: list[LCDEligibilityResult]
    pages_processed: int
    extraction_confidence: float
```

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/eligibility/upload` | POST | Upload PDF, return check_id |
| `/api/eligibility/{check_id}/status` | GET | Poll processing status |
| `/api/eligibility/{check_id}/results` | GET | Get completed results |
| `/api/eligibility/lcds` | GET | List available LCDs |

### 1.4 `backend/prompts/eligibility.py`

**Extraction prompt** - Extract from medical record:
- Patient demographics
- Diagnoses (with ICD-10 codes)
- Medications/insulin therapy
- Lab values (A1C)
- Encounter dates
- Hypoglycemia history
- Medical necessity statements

**Analysis prompt** - For each LCD criterion:
- Determine status: met/not_met/insufficient_evidence/partial
- Quote supporting evidence
- Reference page numbers
- Explain reasoning
- Recommend if not met

### 1.5 LCD L33822 Criteria (Hardcoded Fallback)

```python
LCD_L33822_CRITERIA = [
    {"id": "diabetes_diagnosis", "name": "Diabetes Diagnosis", "required": True},
    {"id": "face_to_face", "name": "Face-to-Face Encounter (6 months)", "required": True},
    {"id": "training_documented", "name": "Patient Training", "required": True},
    {"id": "intensive_insulin", "name": "Intensive Insulin (3+/day or pump)", "required": False, "alternative_to": "hypoglycemia"},
    {"id": "problematic_hypoglycemia", "name": "Problematic Hypoglycemia", "required": False, "alternative_to": "insulin"},
    {"id": "written_order", "name": "Prescription/Written Order", "required": True},
]
```

---

## Phase 2: Frontend

### 2.1 New Component: `frontend/src/components/EligibilityChecker.jsx`

**Layout:**
- Left side: LCD selector checkboxes + PDF dropzone + state selector (optional)
- Right side: Processing status → Results display

**Results display:**
- Overall status card (qualified/not_qualified/review_needed) with color coding
- Expandable criteria rows with:
  - Status icon (✓/✗/?/~)
  - Criterion name
  - Confidence percentage
  - Expandable evidence quotes + page references
  - Recommendations for unmet criteria
- Gaps summary section

### 2.2 API Client: `frontend/src/api.js`

Add functions:
- `uploadEligibilityCheck(file, lcdIds, patientState)`
- `getEligibilityStatus(checkId)`
- `getEligibilityResults(checkId)`
- `getAvailableLCDs()`

### 2.3 App.jsx

Add "Eligibility" tab with icon "📋" between "Audit" and "Prior Auth"

---

## Phase 3: Dependencies

Add to `requirements.txt`:
```
pymupdf>=1.24.0  # PDF rendering (pure Python, no poppler needed)
```

---

## Implementation Order

1. **pdf_vision.py** - PDF-to-image + Claude Vision extraction
2. **prompts/eligibility.py** - Extraction and analysis prompts
3. **eligibility_analyzer.py** - Criteria matching logic
4. **routers/eligibility.py** - Endpoints with background processing
5. **main.py** - Register eligibility router
6. **api.js** - Frontend API client functions
7. **EligibilityChecker.jsx** - Full component with dropzone + results
8. **App.jsx** - Add tab

---

## Key Patterns to Follow

- **File upload**: Copy from `batch.py` - multipart upload → background task → polling
- **Results display**: Copy from `ClaimAuditor.jsx` - score card + issues list
- **Claude calls**: Extend `llm.py` with Vision message format
- **Verity integration**: Use `verity.py` get_policy() for live LCD criteria

---

## Critical Files Reference

| Pattern | File |
|---------|------|
| Upload + polling | `backend/routers/batch.py` |
| Issue model | `backend/routers/audit.py` (AuditIssue) |
| Results UI | `frontend/src/components/ClaimAuditor.jsx` |
| Dropzone UI | `frontend/src/components/BatchUpload.jsx` |
| Claude client | `backend/services/llm.py` |
| Verity client | `backend/services/verity.py` |
