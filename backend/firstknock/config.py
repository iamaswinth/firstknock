from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # External data (optional — pipeline degrades gracefully without them)
    perplexity_api_key: str = ""
    github_token: str = ""
    apify_api_key: str = ""

    # Databases
    postgres_url: str = "postgresql+asyncpg://firstknock:firstknock@localhost:5432/firstknock"
    memgraph_url: str = "bolt://localhost:7687"
    memgraph_user: str = ""
    memgraph_password: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Clerk auth
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # App
    env: str = "development"
    log_level: str = "INFO"

    # Redis file storage (ingestion pipeline — bytes keyed by resume_id)
    redis_file_key_prefix: str = "ingest:file:"
    redis_file_ttl_seconds: int = 900   # 15 min — covers any queue backlog

    # Pipeline tuning
    extraction_model: str = "claude-sonnet-4-6"
    inference_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    skill_alias_match_threshold: int = 92
    company_match_threshold: int = 88

    # LangSmith tracing (optional — set in .env to enable)
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "firstknock"


settings = Settings()
