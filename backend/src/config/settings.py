"""
Configuration settings for the RAG Chatbot system.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables (override=True ensures .env file takes precedence over system env vars)
load_dotenv(override=True)

class Settings:
    """Application settings loaded from environment variables."""

    # API Keys and Endpoints
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # Processing Parameters
    CHUNK_SIZE_TOKENS: int = int(os.getenv("CHUNK_SIZE_TOKENS", "512"))
    OVERLAP_PERCENTAGE: int = int(os.getenv("OVERLAP_PERCENTAGE", "20"))
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "1000"))
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "myfirst_book")

    # LLM Configuration
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

    # Performance and Limits
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    RESPONSE_TIMEOUT_SECONDS: int = int(os.getenv("RESPONSE_TIMEOUT_SECONDS", "30"))

    # File and Directory Paths
    DOCS_DIRECTORY: str = os.getenv("DOCS_DIRECTORY", "my-book/docs/")
    PROCESSED_CHUNKS_DIR: str = os.getenv("PROCESSED_CHUNKS_DIR", "data/processed_chunks/")

    # Validation
    def validate(self) -> list[str]:
        """Validate settings and return list of validation errors."""
        errors = []

        if not self.COHERE_API_KEY:
            errors.append("COHERE_API_KEY is required")

        if not self.QDRANT_URL and not self.QDRANT_HOST:
            errors.append("Either QDRANT_URL or QDRANT_HOST must be specified")

        # Check if either Cohere or Gemini API key is provided
        if not self.COHERE_API_KEY and not self.GEMINI_API_KEY:
            errors.append("Either COHERE_API_KEY or GEMINI_API_KEY must be provided")

        return errors

# Global settings instance
settings = Settings()

# Validate settings at startup
validation_errors = settings.validate()
if validation_errors:
    raise ValueError(f"Configuration validation failed: {'; '.join(validation_errors)}")