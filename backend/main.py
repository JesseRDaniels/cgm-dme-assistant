"""CGM DME Assistant - FastAPI Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, batch, generate, codes, audit, prior_auth
from services.pinecone_client import init_pinecone


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    await init_pinecone()
    yield


app = FastAPI(
    title="CGM DME Assistant",
    description="RAG-based assistant for CGM/Diabetic DME billing",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch Processing"])
app.include_router(generate.router, prefix="/api/generate", tags=["Document Generation"])
app.include_router(codes.router, prefix="/api/codes", tags=["Code Lookup"])
app.include_router(audit.router, prefix="/api/audit", tags=["Claim Audit"])
app.include_router(prior_auth.router, prefix="/api/prior-auth", tags=["Prior Authorization"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "cgm-dme-assistant"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "CGM DME Assistant",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
