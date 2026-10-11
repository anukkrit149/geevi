from typing import Any

from pydantic import BaseModel, Field

from app.schemas.commands import CommandBase

ARCHIVE_SCHEMA = "geevi-archive/1"


class ArchiveOriginal(BaseModel):
    sha256: str
    length: int
    media_type: str
    available: bool
    base64: str | None = None


class Archive(BaseModel):
    """Portable workspace archive. Never contains passwords, sessions, grants or server secrets."""

    archive_schema: str = Field(alias="schema")
    archive_version: int
    kind: str  # full_backup|review_packet
    complete: bool
    incomplete_reasons: list[str]
    workspace: dict[str, Any]
    container: dict[str, Any]
    snapshot: dict[str, Any]
    labels: dict[str, Any]
    counts: dict[str, int]
    excluded: list[str]
    content_digest: str
    tables: dict[str, list[dict[str, Any]]]
    originals: list[ArchiveOriginal]

    model_config = {"populate_by_name": True}


class ArchiveImportBody(CommandBase):
    archive: dict[str, Any]
