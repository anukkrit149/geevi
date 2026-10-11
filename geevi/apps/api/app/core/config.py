from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]
# Repository layout: <root>/apps/api/app/core/config.py. In a packaged deployment the API may sit alone.
REPO_ROOT = API_ROOT.parents[1] if len(API_ROOT.parents) > 1 else API_ROOT
PACKAGED_FIXTURES = API_ROOT / "app" / "demo_data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GEEVI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://geevi@127.0.0.1:5433/geevi"
    # Development mode enables fictional development identities, demo seeding and fixture loading.
    dev_mode: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Also accept a write whose Origin is the very host it was sent to (set where a platform serves the
    # frontend and the API from one public origin, so the URL need not be known in advance).
    same_origin_writes: bool = False
    # One short-lived connection per request for serverless hosts; the database's own pooler does the pooling.
    serverless: bool = False
    session_hours: int = 12
    cookie_secure: bool = False
    cookie_name: str = "geevi_session"
    max_upload_bytes: int = 5_000_000
    max_archive_bytes: int = 60_000_000
    fixtures_dir: Path = REPO_ROOT / "fixtures" / "department-journey"
    credentials_file: Path = API_ROOT / ".dev-credentials.json"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg(cls, value: str) -> str:
        """Hosted providers hand out postgres:// or postgresql:// URLs; this app uses the psycopg driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
