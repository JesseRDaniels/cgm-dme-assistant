# CGM DME Assistant - Project Instructions

## Current Status (Jan 4, 2026)
- Backend: Built, not deployed
- Frontend: Built, not deployed
- Pinecone: **14 vectors indexed** (LCD policies, HCPCS codes, denial reasons)
- Verity MCP: **Installed** at ~/verity_mcp, configured in Claude Code

## Next Steps
1. **Test Verity MCP** - restart Claude Code, then test with `lookup_code("A9276")`
2. **Deploy backend to Railway** - create project, set env vars, deploy
3. **Deploy frontend** - Vercel or Railway static
4. **Test end-to-end** - verify RAG chat, claim auditor, prior auth generator

## Tech Stack
- Backend: FastAPI + Python 3.11+
- Vector DB: Pinecone (serverless, 512 dimensions, index: `cgm-dme`)
- LLM: Claude 3.5 Sonnet (claude-sonnet-4-20250514)
- Embeddings: Voyage AI (voyage-3-lite)
- Frontend: React + Vite + Tailwind CSS v4

## MCP Integrations
- **Verity MCP** (~/verity_mcp): Medicare LCD/NCD lookups, prior auth checks
  - `lookup_code("A9276")` - Code coverage info
  - `search_policies("CGM")` - Search LCDs/NCDs
  - `get_policy("L33822")` - Full LCD details
  - `check_prior_auth(["A9276"])` - Prior auth requirements
  - `compare_policies()` - Compare coverage across MACs
  - `search_criteria()` - Search coverage criteria

## Pinecone Index Contents
- **lcd_policies** (4 vectors): L33822 coverage, codes, documentation, denials
- **hcpcs_codes** (5 vectors): A9276, A9277, A9278, K0553, K0554
- **denial_reasons** (5 vectors): CO-4, CO-16, CO-167, CO-197, PR-204

## Key Files
- `backend/main.py` - FastAPI entrypoint
- `backend/routers/audit.py` - Claim validation (LCD L33822)
- `backend/services/rag.py` - Core RAG pipeline
- `backend/services/llm.py` - Claude integration
- `frontend/src/App.jsx` - React app with tabs (Chat, Codes, Batch, Audit, Prior Auth)
- `frontend/src/components/ClaimAuditor.jsx` - Claim validation UI
- `frontend/src/components/PriorAuthGenerator.jsx` - Prior auth letter generator
- `data/chunks/all_chunks.json` - Knowledge base chunks (14 total)

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
VERITY_API_KEY=vrt_live_4JVLAh43hfvSAZ0P
```

## Deployment (Railway)
```bash
# Backend
cd ~/cgm-dme-assistant
railway login
railway init  # or railway link
railway up

# Set env vars
railway variables set ANTHROPIC_API_KEY=... PINECONE_API_KEY=... VOYAGE_API_KEY=...
```
