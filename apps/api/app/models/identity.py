import uuid

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base, Record, flag, jdict, jlist, num, req, ts, txt, uid


class Account(Base):
    """Fictional development identity. Not an institutional account; grants are demonstration policy."""

    __tablename__ = "accounts"
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = req(unique=True)
    display_name = req()
    role_title = req()
    password_hash = req()
    is_development = flag(True)
    active = flag(True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    token_hash = req(unique=True)
    csrf_token = req()
    created_at = ts(False, server_default=func.now())
    expires_at = ts(False)
    revoked_at = ts()


class Workspace(Base):
    __tablename__ = "workspaces"
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = req()
    data_label = req(default="fictional")
    active_container_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspace_containers.id", use_alter=True, name="fk_workspace_active_container"), nullable=True)
    sequence = mapped_column(BigInteger, default=0, nullable=False)
    created_at = ts(False, server_default=func.now())


class WorkspaceContainer(Base):
    """Physical container namespacing logical record ids so a restore never rewrites active records."""

    __tablename__ = "workspace_containers"
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    status = req(default="active")  # active|staging|validated|failed|retired
    origin = req(default="created")  # created|demo_seed|legacy_import|archive_restore
    provenance = jdict()
    created_at = ts(False, server_default=func.now())
    created_by = uid()


class WorkspaceGrant(Base):
    __tablename__ = "workspace_grants"
    __table_args__ = (UniqueConstraint("workspace_id", "account_id"),)
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    account_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    capabilities = jlist()


class CommandReceipt(Record):
    """Idempotency receipt; `id` is the client command id, unique per workspace container."""

    __tablename__ = "command_receipts"
    kind = "command_receipt"
    action = req()
    input_digest = req()
    result = jdict()


class AuditEvent(Record):
    __tablename__ = "audit_events"
    kind = "audit_event"
    command_id = uid()
    action = req()
    target_kind = req()
    target_id = uid()
    target_revision = num()
    reason = txt()
    detail = jdict()


class WorkspaceNote(Record):
    """Non-clinical team note; the minimal safe command exercising the full guarded boundary."""

    __tablename__ = "workspace_notes"
    kind = "workspace_note"
    text = req()
    status = req(default="open")
