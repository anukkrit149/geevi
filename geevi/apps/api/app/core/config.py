from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GEEVI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://geevi@127.0.0.1:5433/geevi"
    # Development mode enables fictional development identities, demo seeding and fixture loading.
    dev_mode: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    session_hours: int = 12
    cookie_secure: bool = False
    cookie_name: str = "geevi_session"
    max_upload_bytes: int = 5_000_000
    max_archive_bytes: int = 60_000_000
    fixtures_dir: Path = REPO_ROOT / "fixtures" / "department-journey"
    credentials_file: Path = REPO_ROOT / "apps" / "api" / ".dev-credentials.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
