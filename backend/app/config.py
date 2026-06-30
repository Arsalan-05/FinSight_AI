from __future__ import annotations

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
    # Session pooler host (Supabase → Connect → Session pooler)
    supabase_pooler_host: str = ""

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
    app_version: str = "1.3.0"

    # Web search — Tavily optional; DuckDuckGo fallback when enabled
    tavily_api_key: str = ""
    web_search_enabled: bool = True

    # Plaid — compliant live bank linking (optional; sandbox free at dashboard.plaid.com)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"  # sandbox | development | production
    plaid_token_encryption_key: str = ""
    plaid_sync_interval_seconds: int = 14_400  # 4 hours
    plaid_webhook_secret: str = ""

    # Beta invite-only access (comma-separated emails; empty = open)
    beta_allowed_emails: str = ""

    # SMTP for weekly digest emails (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

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
        return self.effective_llm_provider == "anthropic" and bool(self.anthropic_api_key)

    @property
    def effective_llm_provider(self) -> str:
        """Use Anthropic on cloud when a key is set; Ollama is local-only."""
        if self.llm_provider == "anthropic":
            return "anthropic"
        if self.environment == "production" and self.anthropic_api_key:
            return "anthropic"
        return "ollama"

    @property
    def database_url_resolved(self) -> str:
        """Postgres URL — prefer session pooler; direct db.* hosts fail from cloud deploys."""
        url = self.database_url
        pooler = _supabase_session_pooler_url(self, url)

        if "pooler.supabase.com" in url:
            return _normalize_supabase_database_url(url)
        if _is_direct_supabase_db_url(url):
            return pooler or _normalize_supabase_database_url(url)
        if pooler and (self.use_supabase_db or self.supabase_db_password):
            return pooler
        if "supabase.co" in url:
            return _normalize_supabase_database_url(url)
        return url

    @property
    def using_supabase_postgres(self) -> bool:
        url = self.database_url_resolved
        return "supabase.co" in url or "pooler.supabase.com" in url


def _supabase_project_ref(supabase_url: str) -> str | None:
    host = supabase_url.rstrip("/").replace("https://", "").replace("http://", "")
    if not host.endswith(".supabase.co"):
        return None
    return host.replace(".supabase.co", "")


def _is_direct_supabase_db_url(url: str) -> bool:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    return host.startswith("db.") and host.endswith(".supabase.co")


def _supabase_session_pooler_url(settings: Settings, database_url: str = "") -> str | None:
    """Build session-pooler URL from SUPABASE_URL + password (no manual URL encoding)."""
    from urllib.parse import quote_plus, unquote, urlparse

    ref = _supabase_project_ref(settings.supabase_url) if settings.supabase_url else None
    if not ref and database_url:
        host = urlparse(database_url).hostname or ""
        if host.startswith("db.") and host.endswith(".supabase.co"):
            ref = host.removeprefix("db.").removesuffix(".supabase.co")

    password = settings.supabase_db_password
    if not password and database_url:
        parsed = urlparse(database_url)
        if parsed.password:
            password = unquote(parsed.password)

    if not ref or not password:
        return None

    pooler_host = settings.supabase_pooler_host or "aws-1-us-east-2.pooler.supabase.com"
    pwd = quote_plus(password)
    return (
        f"postgresql://postgres.{ref}:{pwd}@{pooler_host}:5432/postgres?sslmode=require"
    )


def _normalize_supabase_database_url(url: str) -> str:
    """Ensure Supabase pooler URLs include sslmode and pgbouncer when required."""
    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 5432
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if "sslmode" not in params:
        params["sslmode"] = "require"
    if "pooler.supabase.com" in host and port == 6543 and "pgbouncer" not in params:
        params["pgbouncer"] = "true"

    return urlunparse(parsed._replace(query=urlencode(params)))


settings = Settings()
