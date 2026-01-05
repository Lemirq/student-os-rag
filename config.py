from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Chunking Configuration
    max_chunk_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
