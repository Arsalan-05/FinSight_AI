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


settings = Settings()
