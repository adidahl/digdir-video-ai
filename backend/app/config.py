"""Application configuration settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Video RAG Platform"
    debug: bool = False
    
    # Database
    database_url: str
    vector_database_url: str
    
    # Neo4j
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    # Redis
    redis_url: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # OpenAI
    openai_api_key: str
    openai_org_id: str | None = None  # Optional organization ID
    
    # Storage
    video_storage_path: str = "/app/videos"
    lightrag_storage_path: str = "/app/lightrag_store"
    
    # LightRAG Configuration
    lightrag_use_external_storage: bool = True  # Use PostgreSQL + Neo4j instead of file storage
    lightrag_embedding_model: str = "text-embedding-ada-002"
    lightrag_llm_model: str = "gpt-4o-mini"  # For entity extraction
    
    # File upload limits
    max_upload_size: int = 2 * 1024 * 1024 * 1024  # 2GB
    
    # Whisper model
    whisper_model: str = "base"  # Can be: tiny, base, small, medium, large, turbo
    whisper_device: str = "cpu"  # cpu or cuda
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

