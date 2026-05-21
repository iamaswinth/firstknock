from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # External data (optional — pipeline degrades gracefully without them)
    proxycurl_api_key: str = ""
    crunchbase_api_key: str = ""
    github_token: str = ""

    # Databases
    postgres_url: str = "postgresql+asyncpg://firstknock:firstknock@localhost:5432/firstknock"
    memgraph_url: str = "bolt://localhost:7687"
    memgraph_user: str = ""
    memgraph_password: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # App
    env: str = "development"
    log_level: str = "INFO"

    # Pipeline tuning
    extraction_model: str = "claude-sonnet-4-6"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    skill_alias_match_threshold: int = 92
    company_match_threshold: int = 88


settings = Settings()
