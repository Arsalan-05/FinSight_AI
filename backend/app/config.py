from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql://finsight:finsight@db:5432/finsight"
    pgvector_collection: str = "transaction_embeddings"
    environment: str = "development"


settings = Settings()
