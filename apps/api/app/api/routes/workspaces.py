from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Commander, commander, current_account, reader
from app.core.errors import DomainError, not_permitted
from app.db.session import get_db
from app.models.identity import Account, AuditEvent, WorkspaceGrant, WorkspaceNote
from app.schemas.commands import CommandResult, NoteCreate, NoteUpdate
from app.schemas.identity import (
    AuditEventOut,
    MemberOut,
    NoteOut,
    TimelineEntry,
    TodayOut,
    WorkspaceCreate,
    WorkspaceOut,
)
from app.services import worklist
from app.services.command_service import Ctx, target
from app.services.workspaces import create_workspace

router = APIRouter(tags=["workspaces"])


@router.post("/workspaces", response_model=WorkspaceOut)
def create(body: WorkspaceCreate, account: Account = Depends(current_account), db: Session = Depends(get_db)):
    """Empty workspace for imports/restores. Requires an account that manages at least one workspace."""
    grants = db.scalars(select(WorkspaceGrant).where(WorkspaceGrant.account_id == account.id)).all()
    if not any("workspace.manage" in g.capabilities for g in grants):
        raise not_permitted("Only an account with the workspace.manage grant can create a workspace.")
    name = body.name.strip()
    if not name:
        raise DomainError(422, "validation_failed", "A workspace name is required.")
    ws = create_workspace(db, name, created_by=account.id)
    db.commit()
    grant = db.scalar(select(WorkspaceGrant).where(WorkspaceGrant.workspace_id == ws.id, WorkspaceGrant.account_id == account.id))
    return {"id": ws.id, "name": ws.name, "data_label": ws.data_label, "capabilities": grant.capabilities,
            "sequence": ws.sequence, "active_container_id": ws.active_container_id}


@router.get("/workspaces/{workspace_id}/notes", response_model=list[NoteOut])
def list_notes(ctx: Ctx = Depends(reader)):
    return ctx.all(WorkspaceNote)


@router.post("/workspaces/{workspace_id}/notes", response_model=CommandResult)
def create_note(workspace_id: UUID, body: NoteCreate, cmd: Commander = Depends(commander)):
    def handler(ctx: Ctx):
        if not body.text.strip():
            raise DomainError(422, "validation_failed", "A note needs some text.")
        note = ctx.new(WorkspaceNote, text=body.text.strip())
        ctx.audit("note.create", note)
        return target(note)
    return cmd.run(workspace_id, "note.create", body, handler, "note.write")


@router.post("/workspaces/{workspace_id}/notes/{note_id}/update", response_model=CommandResult)
def update_note(workspace_id: UUID, note_id: UUID, body: NoteUpdate, cmd: Commander = Depends(commander)):
    def handler(ctx: Ctx):
        note = ctx.get(WorkspaceNote, note_id)
        ctx.expect(note, body.expected_revision)
        if body.text is not None:
            note.text = body.text.strip()
        if body.status in ("open", "done"):
            note.status = body.status
        ctx.touch(note)
        ctx.audit("note.update", note)
        return target(note)
    return cmd.run(workspace_id, "note.update", body, handler, "note.write")


@router.get("/workspaces/{workspace_id}/audit", response_model=list[AuditEventOut])
def audit_log(target_id: UUID | None = None, limit: int = 200, ctx: Ctx = Depends(reader)):
    where = [AuditEvent.target_id == target_id] if target_id else []
    rows = ctx.all(AuditEvent, *where, order=(AuditEvent.recorded_seq.desc(), AuditEvent.recorded_at.desc()))
    return rows[: max(1, min(limit, 1000))]



@router.get("/workspaces/{workspace_id}/today", response_model=TodayOut)
def today(ctx: Ctx = Depends(reader)):
    """Owned work for the signed-in account (identity is always server-derived)."""
    return worklist.today(ctx)


@router.get("/workspaces/{workspace_id}/patients/{patient_id}/timeline", response_model=list[TimelineEntry])
def patient_timeline(patient_id: UUID, ctx: Ctx = Depends(reader)):
    return worklist.timeline(ctx, patient_id)


@router.get("/workspaces/{workspace_id}/members", response_model=list[MemberOut])
def members(workspace_id: UUID, ctx: Ctx = Depends(reader)):
    rows = ctx.db.execute(select(Account, WorkspaceGrant).join(WorkspaceGrant, WorkspaceGrant.account_id == Account.id)
                          .where(WorkspaceGrant.workspace_id == workspace_id, Account.active.is_(True)).order_by(Account.display_name)).all()
    # Only accounts with record access can own or review work; the operator is never offered as an owner.
    return [{"id": a.id, "username": a.username, "display_name": a.display_name, "role_title": a.role_title, "capabilities": g.capabilities}
            for a, g in rows if "records.read" in g.capabilities]
