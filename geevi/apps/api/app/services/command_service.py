"""KTD3 transactional command boundary.

Every material write locks the workspace row, checks the idempotency receipt, runs the guarded
handler, appends audit events and stores the receipt in ONE transaction. Actor identity always
comes from the authenticated server session, never from the request body or headers.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError, not_found, not_permitted, stale
from app.core.security import digest
from app.db.base import Record
from app.models.identity import Account, AuditEvent, CommandReceipt, Workspace, WorkspaceGrant


@dataclass
class Ctx:
    db: Session
    account: Account
    workspace: Workspace
    container_id: UUID
    caps: frozenset[str]
    seq: int = 0
    command_id: UUID | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def actor(self) -> dict[str, str]:
        return {"id": str(self.account.id), "name": self.account.display_name}

    def can(self, capability: str) -> bool:
        return capability in self.caps

    def require(self, capability: str, target: tuple[str, Any] | None = None) -> None:
        if capability not in self.caps:
            raise not_permitted(
                f"{self.account.display_name} does not hold the '{capability}' grant in this workspace.",
                target=target, next_action="Ask an account holding this grant to perform the action.",
                details={"required_capability": capability})

    def new(self, cls: type[Record], **values) -> Any:
        obj = cls(container_id=self.container_id, recorded_seq=self.seq, recorded_by=self.account.id,
                  recorded_by_name=self.account.display_name, **values)
        if obj.id is None:
            import uuid
            obj.id = uuid.uuid4()
        if obj.revision is None:
            obj.revision = 1
        self.db.add(obj)
        return obj

    def get(self, cls: type[Record], id_: Any, *, lock: bool = False) -> Any:
        obj = self.db.get(cls, (self.container_id, id_)) if id_ else None
        if obj is None:
            raise not_found(cls.kind, id_)
        return obj

    def find(self, cls: type[Record], id_: Any) -> Any | None:
        return self.db.get(cls, (self.container_id, id_)) if id_ else None

    def all(self, cls: type[Record], *where, order=None) -> list[Any]:
        q = select(cls).where(cls.container_id == self.container_id, *where)
        q = q.order_by(*(order if isinstance(order, tuple | list) else (order,))) if order is not None else q.order_by(cls.recorded_seq, cls.recorded_at)
        return list(self.db.scalars(q))

    def expect(self, obj: Record, expected_revision: int | None) -> None:
        """Entity-level compare-and-set: a stale editor cannot silently overwrite newer state."""
        if expected_revision is not None and obj.revision != expected_revision:
            raise stale(f"This {obj.kind.replace('_', ' ')} changed since it was loaded.", target=(obj.kind, obj.id),
                        next_action="Reload the current version, re-apply your change and submit again.",
                        details={"expected_revision": expected_revision, "current_revision": obj.revision})

    def touch(self, obj: Record) -> None:
        obj.revision = (obj.revision or 0) + 1

    def audit(self, action: str, obj: Record | None = None, *, reason: str | None = None, detail: dict | None = None,
              target: tuple[str, Any, int | None] | None = None) -> None:
        kind, tid, rev = target if target else (obj.kind, obj.id, obj.revision)
        self.new(AuditEvent, command_id=self.command_id, action=action, target_kind=kind, target_id=tid,
                 target_revision=rev, reason=reason, detail=detail or {})


class CommandBase(BaseModel):
    """Every mutation carries a client-generated command id (idempotency key)."""

    command_id: UUID


def load_grant(db: Session, workspace_id: UUID, account: Account) -> WorkspaceGrant:
    grant = db.scalar(select(WorkspaceGrant).where(WorkspaceGrant.workspace_id == workspace_id,
                                                   WorkspaceGrant.account_id == account.id))
    if grant is None:
        # Same answer for a missing workspace and one the account cannot reach.
        raise not_permitted("This account has no access to the requested workspace.", target=("workspace", workspace_id))
    return grant


def read_context(db: Session, account: Account, workspace_id: UUID) -> Ctx:
    grant = load_grant(db, workspace_id, account)
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.active_container_id is None:
        raise not_found("workspace", workspace_id)
    return Ctx(db, account, ws, ws.active_container_id, frozenset(grant.capabilities), seq=ws.sequence)


def _before_commit(ctx: Ctx) -> None:
    """Seam used by fault-injection tests to prove an aborted commit leaves no partial state."""


def run_command(db: Session, account: Account, workspace_id: UUID, action: str, body: CommandBase, scope: str,
                handler: Callable[[Ctx], dict[str, Any]], capability: str | None = None) -> dict[str, Any]:
    input_digest = digest({"actor": account.id, "action": action, "scope": scope, "body": body.model_dump(mode="json")})
    db.rollback()
    try:
        load_grant(db, workspace_id, account)
        ws = db.execute(select(Workspace).where(Workspace.id == workspace_id).with_for_update()).scalar_one_or_none()
        if ws is None or ws.active_container_id is None:
            raise not_found("workspace", workspace_id)
        grant = load_grant(db, workspace_id, account)
        receipt = db.get(CommandReceipt, (ws.active_container_id, body.command_id))
        if receipt is not None:
            if receipt.input_digest != input_digest:
                raise DomainError(409, "command_id_conflict",
                                  "This command id was already used with a different actor or payload.",
                                  target=("command", body.command_id),
                                  next_action="Start a new action; never reuse a command id for changed content.")
            db.rollback()
            return {**receipt.result, "replayed": True}
        ws.sequence += 1
        ctx = Ctx(db, account, ws, ws.active_container_id, frozenset(grant.capabilities), seq=ws.sequence,
                  command_id=body.command_id)
        if capability:
            ctx.require(capability)
        outcome = handler(ctx) or {}
        db.flush()
        result = {"command_id": str(body.command_id), "action": action, "sequence": ws.sequence,
                  "target": outcome.get("target"), "data": outcome.get("data", {}), "replayed": False}
        ctx.new(CommandReceipt, id=body.command_id, action=action, input_digest=input_digest, result=result)
        _before_commit(ctx)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def target(obj: Record, **data) -> dict[str, Any]:
    return {"target": {"kind": obj.kind, "id": str(obj.id), "revision": obj.revision}, "data": data}
