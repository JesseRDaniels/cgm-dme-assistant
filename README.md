# CGM DME Assistant

RAG-based AI assistant for CGM/Diabetic DME billing, prior authorization, and denial management.

## Features

- **Prior Authorization**: Generate medical necessity letters, check coverage criteria
- **DWO/SWO Generation**: Auto-generate detailed written orders
- **Denial Analyzer**: Understand denial reasons, generate appeals
- **Code Helper**: HCPCS code lookup, modifier guidance
- **Batch Processing**: CSV upload for bulk claim processing

## Stack

- **Backend**: FastAPI + Python
- **LLM**: Claude 3.5 Sonnet (Anthropic)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: Pinecone
- **Frontend**: React + Vite

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
cp ../.env.example ../.env  # Edit with your API keys
uvicorn main:app --reload

# Frontend (coming soon)
cd frontend
npm install
npm run dev
```

## Knowledge Base

The system uses RAG over:
- LCD L33822 (CGM Coverage)
- HCPCS codes (A9276-A9278, K0553-K0554)
- Medicare Benefit Policy Manual
- Denial reason codes and appeal strategies

## API Endpoints

```
POST /api/chat              - Query the assistant
POST /api/batch/upload      - Upload CSV for processing
POST /api/generate/dwo      - Generate DWO
POST /api/generate/appeal   - Generate appeal letter
GET  /api/codes/{hcpcs}     - Code lookup
```

## Development

```bash
# Run tests
pytest

# Build knowledge base
python scripts/scrape_lcd.py
python scripts/process_docs.py
python scripts/build_index.py
```
