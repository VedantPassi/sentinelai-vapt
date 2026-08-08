from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    anthropic_api_key: str = ""

    llm_provider: str = "ollama"  # "ollama" | "anthropic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    cors_origins: list[str] = ["http://localhost:3000"]

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentineldev"

    # BloodHound CE
    bloodhound_url: str = "http://localhost:8080"
    bloodhound_user: str = "admin"
    bloodhound_secret: str = ""

    # Integrations
    slack_webhook_url: str = ""
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""

    # OIDC / SSO
    oidc_enabled: bool = False
    oidc_issuer: str = "https://accounts.google.com"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:8000/auth/oidc/callback"

    # SIEM
    siem_enabled: bool = False
    splunk_hec_url: str = ""
    splunk_hec_token: str = ""
    splunk_index: str = "sentinelai"
    es_url: str = ""
    es_index: str = "sentinelai-findings"
    es_user: str = ""
    es_password: str = ""


settings = Settings()
