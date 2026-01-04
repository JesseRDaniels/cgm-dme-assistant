# CGM DME Assistant - Project Instructions

## Current Status (Jan 4, 2026)
- Backend: Built with Verity API integration, tested locally
- Frontend: Built, not deployed
- Pinecone: **14 vectors indexed** (LCD policies, HCPCS codes, denial reasons)
- Verity API: **Integrated** into backend (codes, prior-auth, audit routers)
- Verity MCP: **Configured** with working API key

## Next Steps
1. **Deploy backend to Railway** - create project, set env vars, deploy
2. **Deploy frontend** - Vercel or Railway static
3. **Test end-to-end** - verify all endpoints work in production

## Tech Stack
- Backend: FastAPI + Python 3.11+
- Vector DB: Pinecone (serverless, 512 dimensions, index: `cgm-dme`)
- LLM: Claude 3.5 Sonnet (claude-sonnet-4-20250514)
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

## MCP Integration (for development)
- **Verity MCP**: Configured with working API key in Claude Code
  - `mcp__verity__lookup_code("A9276")` - Code coverage info
  - `mcp__verity__search_policies("CGM")` - Search LCDs/NCDs
  - `mcp__verity__get_policy("L33822")` - Full LCD details
  - `mcp__verity__check_prior_auth(["A9276"])` - Prior auth requirements

## Pinecone Index Contents
- **lcd_policies** (4 vectors): L33822 coverage, codes, documentation, denials
- **hcpcs_codes** (5 vectors): A9276, A9277, A9278, K0553, K0554
- **denial_reasons** (5 vectors): CO-4, CO-16, CO-167, CO-197, PR-204

## Key Files
- `backend/main.py` - FastAPI entrypoint
- `backend/services/verity.py` - Verity API client
- `backend/routers/audit.py` - Claim validation with Verity enrichment
- `backend/routers/codes.py` - HCPCS lookup via Verity
- `backend/routers/prior_auth.py` - Prior auth checks via Verity
- `backend/services/rag.py` - Core RAG pipeline
- `backend/services/llm.py` - Claude integration
- `frontend/src/App.jsx` - React app with tabs
- `data/chunks/all_chunks.json` - Knowledge base chunks (14 total)

## Domain Knowledge
- LCD L33822: CGM coverage criteria
- HCPCS: A9276 (sensor), A9277 (transmitter), A9278 (receiver), K0553 (monthly), K0554
- Key modifiers: KX (medical necessity), NU (new), RR (rental)
- Valid diabetes DX: E10.x, E11.x, E13.x, O24.x

## API Endpoints
- `POST /api/chat` - RAG chat
- `POST /api/audit/claim` - Full claim validation (Verity-enriched)
- `POST /api/audit/quick` - Quick code check (Verity-enriched)
- `POST /api/prior-auth/check` - Prior auth check via Verity
- `GET /api/prior-auth/jurisdictions` - List MAC jurisdictions
- `POST /api/generate/prior-auth` - Generate prior auth letter
- `POST /api/generate/dwo` - Generate detailed written order
- `GET /api/codes/{code}` - HCPCS lookup via Verity

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
```
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
VERITY_API_KEY=vrt_live_ruzkWh-LGh5VepXYnK72xZRiF2VIjfX-NoS-8zQXH84_b3e9
```

## Deployment (Railway)
```bash
# Backend
cd ~/cgm-dme-assistant
railway login
railway init  # or railway link
railway up

# Set env vars (including new VERITY_API_KEY)
railway variables set ANTHROPIC_API_KEY=... PINECONE_API_KEY=... VOYAGE_API_KEY=... VERITY_API_KEY=...
```
