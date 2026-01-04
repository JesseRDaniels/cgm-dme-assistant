"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API Keys
    anthropic_api_key: str = ""
    voyage_api_key: str = ""  # For embeddings (Voyage AI)
    verity_api_key: str = ""  # For Medicare coverage intelligence

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "cgm-dme"

    # App Settings
    debug: bool = False
    log_level: str = "INFO"

    # LLM Settings
    claude_model: str = "claude-sonnet-4-20250514"
    embedding_model: str = "voyage-3-lite"
    embedding_dimensions: int = 512  # voyage-3-lite uses 512

    # RAG Settings
    retrieval_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = "../.env"  # Project root .env
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars from Railway


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
