# CGM DME Assistant - Project Instructions

## Project Overview
RAG-based assistant for CGM/Diabetic DME billing workflows.

## Tech Stack
- Backend: FastAPI + Python 3.11+
- Vector DB: Pinecone
- LLM: Claude 3.5 Sonnet
- Embeddings: OpenAI text-embedding-3-small
- Frontend: React + Vite (planned)

## Key Files
- `backend/main.py` - FastAPI entrypoint
- `backend/services/rag.py` - Core RAG pipeline
- `backend/services/llm.py` - Claude integration
- `backend/prompts/` - System prompts for different features
- `scripts/` - Data processing and indexing scripts

## Domain Knowledge
- LCD L33822: CGM coverage criteria
- HCPCS: A9276 (sensor), A9277 (transmitter), A9278 (receiver)
- Key modifiers: KX (medical necessity), NU (new), RR (rental)

## Coding Conventions
- Use async/await for I/O operations
- Type hints on all functions
- Pydantic models for request/response
- Keep prompts in separate files for easy iteration

## Running Locally
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

## Testing
```bash
pytest -v
```
