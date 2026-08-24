from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_db: str = "qualitypilot"
    postgres_user: str = "qualitypilot"
    postgres_password: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    ollama_base_url: str = "http://ollama:11434"
    chat_model: str = "qwen3:4b"
    embedding_model: str = "embeddinggemma"
    embedding_dimensions: int = 768

    chunk_size: int = 180
    chunk_overlap: int = 40

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        database = quote_plus(self.postgres_db)

        return (
            f"postgresql://{user}:{password}@"
            f"{self.postgres_host}:{self.postgres_port}/{database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
