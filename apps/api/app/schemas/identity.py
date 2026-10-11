from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.identity import AuditEvent, WorkspaceNote
from app.schemas.auto import schema_for


class LoginRequest(BaseModel):
    username: str
    password: str


class AccountOut(BaseModel):
    id: UUID
    username: str
    display_name: str
    role_title: str
    is_development: bool


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    data_label: str
    capabilities: list[str]
    sequence: int
    active_container_id: UUID | None


class SessionOut(BaseModel):
    account: AccountOut
    csrf_token: str
    workspaces: list[WorkspaceOut]
    identity_notice: str = "Fictional development identity. Not an institutional account or verified clinical signature."


class DevIdentity(BaseModel):
    username: str
    display_name: str
    role_title: str
    label: str = "Development identity"


class WorkspaceCreate(BaseModel):
    command_id: UUID
    name: str


NoteOut = schema_for(WorkspaceNote, "NoteOut")
AuditEventOut = schema_for(AuditEvent, "AuditEventOut")


class WorkEntry(BaseModel):
    kind: str
    title: str
    detail: str | None = None
    patient_id: UUID | None = None
    target_kind: str | None = None
    target_id: UUID | None = None
    owner: str | None = None
    next_action: str | None = None
    state: str | None = None


class TodayOut(BaseModel):
    account: str
    items: list[WorkEntry]
    counts: dict[str, int]


class TimelineEntry(BaseModel):
    seq: int
    recorded_at: datetime
    lane: str  # source|decision|handoff|planned|actual|concern|impact
    kind: str
    title: str
    detail: str | None = None
    clinical_time: dict[str, Any] | None = None
    actor: str | None = None
    target_kind: str
    target_id: UUID


class MemberOut(BaseModel):
    """A development identity with a grant in this workspace (for owner/reviewer pickers)."""

    id: UUID
    username: str
    display_name: str
    role_title: str
    capabilities: list[str]
