import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "AI PDF Chatter"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_USER: str = "pdfuser"
    POSTGRES_PASSWORD: str = "pdfpassword"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pdfchatter"
    DATABASE_URL: str = "postgresql+asyncpg://pdfuser:pdfpassword@localhost:5432/pdfchatter"

    # Security
    JWT_SECRET: str = "CHANGE_THIS_TO_A_SECURE_SECRET_KEY_IN_PRODUCTION_32_BYTES_MIN"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage
    STORAGE_BACKEND: str = "local" # "local", "s3", "minio"
    LOCAL_STORAGE_DIR: str = "./storage_data"
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadminpassword"
    S3_BUCKET_NAME: str = "pdfchatter-documents"
    S3_REGION: str = "us-east-1"

    # AI & Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "ollama"  # "mock", "openai", "ollama"
    EMBEDDING_MODEL: str = "embeddinggemma"
    EMBEDDING_DIMENSION: int = 768

    LLM_PROVIDER: str = "ollama"        # "mock", "openai", "anthropic", "ollama"
    LLM_MODEL: str = "qwen3:4b-instruct"

    # Ollama Local AI Configuration Slot
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"


    RAG_TOP_K: int = 5
    MAX_CONVERSATION_HISTORY_MESSAGES: int = 6

    # Phase 8 Advanced Retrieval Configuration
    DENSE_TOP_K: int = 10
    LEXICAL_TOP_K: int = 10
    RRF_K: float = 60.0
    RERANK_TOP_K: int = 10
    FINAL_TOP_K: int = 5
    ENABLE_HYBRID_RETRIEVAL: bool = True
    ENABLE_RERANKING: bool = True
    ENABLE_QUERY_EXPANSION: bool = True
    RERANKER_PROVIDER: str = "mock"  # "mock", "cohere", "disabled"
    RETRIEVAL_MIN_SCORE_THRESHOLD: float = 0.0
    RETRIEVAL_PIPELINE_VERSION: str = "hybrid-v1"


    # Phase 4 Context Budget Configuration
    CONTEXT_MAX_SELECTION_TOKENS: int = 500
    CONTEXT_MAX_PAGE_TOKENS: int = 1000
    CONTEXT_MAX_SECTION_TOKENS: int = 800
    CONTEXT_MAX_CONVERSATION_TOKENS: int = 1500
    CONTEXT_MAX_RETRIEVAL_TOKENS: int = 1500
    CONTEXT_MAX_TOTAL_TOKENS: int = 4000

    # Phase 5 Conversation Memory Configuration
    CONVERSATION_MAX_HISTORY_MESSAGES: int = 10
    CONVERSATION_MAX_HISTORY_TOKENS: int = 1500
    CONVERSATION_SUMMARY_TRIGGER_MESSAGES: int = 10
    CONVERSATION_SUMMARY_MAX_TOKENS: int = 500
    CONVERSATION_MEMORY_MAX_TOTAL_TOKENS: int = 2000

    # Phase 6 & Ingestion Scalability Configuration
    MAX_UPLOAD_SIZE_BYTES: int = 524_288_000  # 500 MB default configurable limit
    PROCESSING_BATCH_SIZE: int = 50
    EMBEDDING_BATCH_SIZE: int = 50

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    COHERE_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
