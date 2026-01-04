"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "cgm-dme"

    # App Settings
    debug: bool = False
    log_level: str = "INFO"

    # LLM Settings
    claude_model: str = "claude-3-5-sonnet-20241022"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # RAG Settings
    retrieval_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
