# CGM DME Assistant - Project Instructions

## Current Status (Jan 4, 2026)
- **Backend**: Deployed to Railway
- **Frontend**: Deployed to Railway
- **Pinecone**: 14 vectors indexed (LCD policies, HCPCS codes, denial reasons)
- **Verity API**: Integrated into backend (codes, prior-auth, audit routers)

## Production URLs
| Service | URL |
|---------|-----|
| Frontend | https://secure-benevolence-production.up.railway.app |
| Backend | https://cgm-dme-assistant-production.up.railway.app |

## Tech Stack
- Backend: FastAPI + Python 3.11+
- Vector DB: Pinecone (serverless, 512 dimensions, index: `cgm-dme`)
- LLM: Claude Sonnet (claude-sonnet-4-20250514)
- Embeddings: Voyage AI (voyage-3-lite)
- Coverage API: Verity Healthcare API
- Frontend: React + Vite + Tailwind CSS v4

## Verity API Integration
The backend directly integrates with Verity Healthcare API for:
- **Code Lookups** (`/api/codes/{code}`) - HCPCS/CPT/ICD-10 with policies
- **Prior Auth Checks** (`/api/prior-auth/check`) - PA requirements with documentation checklist
- **Claim Auditing** (`/api/audit/claim`) - Enriched with Verity policy data

Key files:
- `backend/services/verity.py` - Verity API client
- `backend/routers/codes.py` - Code lookup with Verity
- `backend/routers/prior_auth.py` - Prior auth with Verity
- `backend/routers/audit.py` - Claim audit with Verity enrichment

## Pinecone Index Contents (70 vectors)
- **hcpcs_codes** (31 vectors): All CGM/glucose HCPCS codes from L33822
- **lcd_policies** (23 vectors): Coverage criteria by section (documentation, frequency, indications, limitations)
- **denial_reasons** (10 vectors): CO-4, CO-16, CO-27, CO-29, CO-50, CO-96, CO-119, CO-167, CO-197, PR-204
- **default** (6 vectors): Documentation requirements, appeal strategies

## Key Files
- `backend/main.py` - FastAPI entrypoint
- `backend/services/verity.py` - Verity API client
- `backend/routers/audit.py` - Claim validation with Verity enrichment
- `backend/routers/codes.py` - HCPCS lookup via Verity
- `backend/routers/prior_auth.py` - Prior auth checks via Verity
- `backend/services/rag.py` - Core RAG pipeline
- `backend/services/llm.py` - Claude integration
- `frontend/src/App.jsx` - React app with tabs
- `frontend/src/api.js` - API client (uses VITE_API_URL env var)

## Domain Knowledge
- LCD L33822: CGM coverage criteria
- HCPCS: A9276 (sensor), A9277 (transmitter), A9278 (receiver), K0553 (monthly), K0554
- Key modifiers: KX (medical necessity), NU (new), RR (rental)
- Valid diabetes DX: E10.x, E11.x, E13.x, O24.x

## API Endpoints
- `GET /health` - Health check
- `POST /api/chat` - RAG chat
- `POST /api/audit/claim` - Full claim validation (Verity-enriched)
- `POST /api/audit/quick` - Quick code check (Verity-enriched)
- `POST /api/prior-auth/check` - Prior auth check via Verity
- `GET /api/prior-auth/jurisdictions` - List MAC jurisdictions
- `POST /api/generate/prior-auth` - Generate prior auth letter
- `POST /api/generate/dwo` - Generate detailed written order
- `GET /api/codes/{code}` - HCPCS lookup via Verity
- `GET /api/policies/{policy_id}` - Full policy detail with criteria/codes
- `GET /api/policies/compare/jurisdictions?codes=...` - Compare coverage across MACs
- `GET /api/policies/changes/recent` - Track recent policy updates
- `GET /api/sync/status` - Check sync status and last sync time
- `POST /api/sync/run` - Trigger vector sync (used by Railway cron)

## Running Locally
```bash
# Backend (port 8001)
cd ~/cgm-dme-assistant
source venv/bin/activate
cd backend && uvicorn main:app --port 8001

# Frontend (port 5173)
cd frontend && npm run dev
```

## Environment Variables

### Backend (Railway)
```
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
VERITY_API_KEY=vrt_live_...
```

### Frontend (Railway)
```
VITE_API_URL=https://cgm-dme-assistant-production.up.railway.app
```

## Railway Services
- **cgm-dme-assistant** - Backend (root: `backend/`)
- **secure-benevolence** - Frontend (root: `frontend/`)

Both auto-deploy from GitHub on push to main.
