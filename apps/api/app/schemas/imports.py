from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import imports as m
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase


class OriginalFile(BaseModel):
    filename: str
    media_type: str
    content_base64: str


class LegacyImportBody(CommandBase):
    """Explicitly supplied legacy material. The server never reads the old origin's browser storage."""

    snapshots: dict[str, Any] = Field(default_factory=dict, description="Captured localStorage values keyed by their legacy store name.")
    packets: list[dict[str, Any]] = Field(default_factory=list, description="Legacy 'export case' packets (may omit bytes/history).")
    originals: list[OriginalFile] = []


class ActivateBody(CommandBase):
    pass


class DiscardBody(CommandBase):
    reason: str | None = None


ImportJobOut = schema_for(m.ImportJob)
LegacyRecordOut = schema_for(m.LegacyRecord)
RecoverySnapshotOut = schema_for(m.RecoverySnapshot, exclude={"preserved_payload"})


class ActivationOut(BaseModel):
    job: ImportJobOut
    active_container_id: UUID
    replayed: bool = False
