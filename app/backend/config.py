import os
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Transcripts
    transcripts_path: Path = Path(__file__).parent.parent.parent / "transcripts"

    # CORS
    cors_origins: list[str] = ["http://localhost:4000", "http://127.0.0.1:4000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
