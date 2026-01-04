# CGM DME Assistant - Project Instructions

## Project Overview
RAG-based assistant for CGM/Diabetic DME billing workflows.

## Tech Stack
- Backend: FastAPI + Python 3.11+
- Vector DB: Pinecone (serverless, 512 dimensions)
- LLM: Claude 3.5 Sonnet (claude-sonnet-4-20250514)
- Embeddings: Voyage AI (voyage-3-lite)
- Frontend: React + Vite + Tailwind CSS v4

## MCP Integrations
- **Verity MCP**: LCD/NCD lookups, prior auth checks, HCPCS/CPT/ICD-10 codes
  - `lookup_code("A9276")` - Code coverage info
  - `search_policies("CGM")` - Search LCDs/NCDs
  - `get_policy("L33822")` - Full LCD details
  - `check_prior_auth(["A9276"])` - Prior auth requirements

## Key Files
- `backend/main.py` - FastAPI entrypoint
- `backend/routers/audit.py` - Claim validation (LCD L33822)
- `backend/services/rag.py` - Core RAG pipeline
- `backend/services/llm.py` - Claude integration
- `frontend/src/App.jsx` - React app with tabs
- `frontend/src/components/ClaimAuditor.jsx` - Claim validation UI
- `frontend/src/components/PriorAuthGenerator.jsx` - Prior auth letter generator

## Domain Knowledge
- LCD L33822: CGM coverage criteria
- HCPCS: A9276 (sensor), A9277 (transmitter), A9278 (receiver), K0553 (monthly), K0554
- Key modifiers: KX (medical necessity), NU (new), RR (rental)
- Valid diabetes DX: E10.x, E11.x, E13.x, O24.x

## API Endpoints
- `POST /api/chat` - RAG chat
- `POST /api/audit/claim` - Full claim validation
- `POST /api/audit/quick` - Quick code check
- `POST /api/generate/prior-auth` - Generate prior auth letter
- `POST /api/generate/dwo` - Generate detailed written order
- `GET /api/codes/{code}` - HCPCS lookup

## Running Locally
```bash
# Backend (port 8001)
cd /Users/jessedaniels/cgm-dme-assistant
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
VERITY_API_KEY=vrt_live_...
```
