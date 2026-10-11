import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column

from app.db.base import Base, Record, jdict, ref, req, ts, txt, uid


class ImportJob(Base):
    """Workspace-level staging receipt for a legacy conversion or archive restore (never inside a container)."""

    __tablename__ = "import_jobs"
    __table_args__ = (UniqueConstraint("workspace_id", "command_id"),)
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    kind = req()  # legacy|archive
    command_id = uid(False)
    source_fingerprint = req()
    status = req(default="staged")  # staged|validated|failed|activated|discarded
    staging_container_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspace_containers.id", ondelete="SET NULL"), nullable=True)
    previous_container_id = uid()
    report = jdict()
    created_by = uid()
    created_by_name = txt()
    created_at = ts(False, server_default=func.now())
    activated_at = ts()
    activation_command_id = uid()


class RecoverySnapshot(Record):
    """Evidence of where a container came from: source fingerprint, preserved payload, validation state."""

    __tablename__ = "recovery_snapshots"
    kind = "recovery_snapshot"
    source_kind = req()  # legacy|archive
    source_fingerprint = req()
    preserved_payload = mapped_column(JSONB, nullable=True)
    validation_state = jdict()
    note = txt()


class LegacyRecord(Record):
    """Preserved legacy history that has no reviewed equivalent here. Never a publication or signature."""

    __tablename__ = "legacy_records"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "legacy_record"
    legacy_kind = req()
    legacy_ref = txt()
    patient_id = uid()
    payload = mapped_column(JSONB, nullable=True)
    mapping_status = req(default="unmapped")
    note = txt()
