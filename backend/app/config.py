from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from app/; backend/ is one level up.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Support .env in backend/ or repo root (where docker-compose reads it).
        env_file=(_BACKEND_DIR / ".env", _ROOT_DIR / ".env"),
        extra="ignore",
    )

    # Paid providers (optional — leave blank when using Ollama)
    anthropic_api_key: str = ""
    voyage_api_key: str = ""

    # Free local defaults — no API keys required
    llm_provider: str = "ollama"  # ollama | anthropic
    embedding_provider: str = "ollama"  # ollama | voyage
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    database_url: str = "postgresql://finsight:finsight@localhost:5432/finsight"
    pgvector_collection: str = "transaction_embeddings"
    environment: str = "development"

    # When true, backend uses Supabase hosted Postgres (requires supabase_db_password)
    use_supabase_db: bool = False
    supabase_db_password: str = ""

    # Local Postgres used when Supabase direct/pooler is unreachable (campus Wi-Fi, etc.)
    database_fallback_url: str = "postgresql://finsight:finsight@localhost:5432/finsight"
    database_fallback_enabled: bool = True

    # Optional — when set, all routes except /health and docs require X-API-Key
    finsight_api_key: str = ""

    # Supabase — set DATABASE_URL to your Supabase Postgres connection string
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""
    require_auth: bool = False

    # Chat rate limit — requests per minute per client IP (0 = disabled)
    chat_rate_limit_per_minute: int = 30

    # Production / deploy
    cors_origins: str = ""  # comma-separated allowed origins (e.g. https://app.up.railway.app)
    finnhub_api_key: str = ""  # optional — live quotes via Finnhub; Yahoo used as fallback
    db_pool_size: int = 5
    db_max_overflow: int = 10
    log_level: str = "INFO"
    app_version: str = "1.2.0"

    # Web search — Tavily optional; DuckDuckGo fallback when enabled
    tavily_api_key: str = ""
    web_search_enabled: bool = True

    # Plaid — compliant live bank linking (optional; sandbox free at dashboard.plaid.com)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox | development | production

    @property
    def plaid_enabled(self) -> bool:
        return bool(self.plaid_client_id and self.plaid_secret)

    @property
    def cors_origin_list(self) -> list[str]:
        defaults = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ]
        if self.environment != "production":
            return defaults
        extra = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return extra or defaults

    @property
    def auth_enforced(self) -> bool:
        """True when API routes should require a valid Supabase JWT."""
        return self.require_auth or self.supabase_auth_enabled

    @property
    def supabase_auth_enabled(self) -> bool:
        """True when Supabase URL (JWKS / ES256) or legacy JWT secret is set."""
        return bool(self.supabase_url or self.supabase_jwt_secret)

    @property
    def embedding_dim(self) -> int:
        return 1024 if self.embedding_provider == "voyage" else 768

    @property
    def embeddings_configured(self) -> bool:
        if self.embedding_provider == "voyage":
            return bool(self.voyage_api_key)
        return True

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return True

    @property
    def database_url_resolved(self) -> str:
        """Postgres URL — use DATABASE_URL if Supabase pooler/direct, else build from password."""
        url = self.database_url
        if "supabase.co" in url or "pooler.supabase.com" in url:
            return url
        if not self.use_supabase_db and not self.supabase_db_password:
            return url
        if not self.supabase_url or not self.supabase_db_password:
            return url
        from urllib.parse import quote_plus

        host = self.supabase_url.rstrip("/").replace("https://", "").replace("http://", "")
        ref = host.replace(".supabase.co", "")
        pwd = quote_plus(self.supabase_db_password)
        return f"postgresql://postgres:{pwd}@db.{ref}.supabase.co:5432/postgres"

    @property
    def using_supabase_postgres(self) -> bool:
        url = self.database_url_resolved
        return "supabase.co" in url or "pooler.supabase.com" in url


settings = Settings()
