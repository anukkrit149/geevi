"""Staged import shared by legacy conversion (U2) and archive restore (U13).

Material is converted into a separate staging container and validated there. The active container
is only switched by a distinct, explicit activation command; any failure leaves it untouched.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError, blocked, not_found
from app.core.security import sha256_bytes
from app.models.identity import Account, Workspace, WorkspaceContainer
from app.models.imports import ImportJob
from app.models.sources import SourceBlob
from app.services.command_service import Ctx, load_grant


def _locked(db: Session, account: Account, workspace_id: UUID, capability: str) -> tuple[Workspace, frozenset[str]]:
    db.rollback()
    load_grant(db, workspace_id, account)
    ws = db.execute(select(Workspace).where(Workspace.id == workspace_id).with_for_update()).scalar_one_or_none()
    if ws is None:
        raise not_found("workspace", workspace_id)
    caps = frozenset(load_grant(db, workspace_id, account).capabilities)
    if capability not in caps:
        raise DomainError(403, "actor_not_permitted", f"{account.display_name} does not hold the '{capability}' grant in this workspace.",
                          details={"required_capability": capability})
    return ws, caps


def _before_stage_commit(job: ImportJob) -> None:
    """Fault-injection seam: an interruption here must leave no staged or activated state."""


def stage(db: Session, account: Account, workspace_id: UUID, *, capability: str, kind: str, command_id: UUID, fingerprint: str,
          origin: str, provenance: dict, builder: Callable[[Ctx], dict]) -> ImportJob:
    try:
        ws, caps = _locked(db, account, workspace_id, capability)
        job = db.scalar(select(ImportJob).where(ImportJob.workspace_id == ws.id, ImportJob.command_id == command_id))
        if job is not None:
            if job.source_fingerprint != fingerprint or job.kind != kind:
                raise DomainError(409, "command_id_conflict", "This command id was already used for different import content.",
                                  target=("import_job", job.id))
            db.rollback()
            return job
        job = ImportJob(workspace_id=ws.id, kind=kind, command_id=command_id, source_fingerprint=fingerprint, status="staged",
                        created_by=account.id, created_by_name=account.display_name, report={})
        db.add(job)
        db.flush()
        failure: dict | None = None
        savepoint = db.begin_nested()
        try:
            container = WorkspaceContainer(workspace_id=ws.id, status="staging", origin=origin, created_by=account.id,
                                           provenance={**provenance, "fingerprint": fingerprint, "import_job_id": str(job.id)})
            db.add(container)
            db.flush()
            ctx = Ctx(db, account, ws, container.id, caps, seq=ws.sequence)
            report = builder(ctx)
            db.flush()
            db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))  # prove every reference stays inside the staging container
            container.status = "validated"
            container.provenance = {**container.provenance, "sequence": report.get("sequence", ws.sequence)}
            savepoint.commit()
            job.status, job.staging_container_id, job.report = "validated", container.id, report
        except DomainError as exc:
            savepoint.rollback()
            failure = exc.body()["error"]
        except (IntegrityError, DBAPIError) as exc:
            savepoint.rollback()
            failure = {"code": "reference_validation_failed", "target": None, "details": {"database": type(exc.orig).__name__ if exc.orig else None},
                       "message": "The import contains records whose identities or references are invalid or point outside its own scope.",
                       "next_action": "Supply an intact archive or snapshot."}
        if failure:
            job.status, job.report = "failed", {"errors": [failure], "complete": False}
        _before_stage_commit(job)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if job.status == "failed":
        error = job.report["errors"][0]
        raise DomainError(422, error["code"], error["message"], target=("import_job", job.id), next_action=error.get("next_action"),
                          details={**(error.get("details") or {}), "job_id": str(job.id), "active_workspace_unchanged": True})
    return job


def activate(db: Session, account: Account, workspace_id: UUID, job_id: UUID, command_id: UUID, capability: str) -> tuple[ImportJob, bool]:
    try:
        ws, _ = _locked(db, account, workspace_id, capability)
        job = db.get(ImportJob, job_id)
        if job is None or job.workspace_id != ws.id:
            raise not_found("import_job", job_id)
        if job.status == "activated":
            if job.activation_command_id == command_id:
                db.rollback()
                return job, True
            raise DomainError(409, "already_activated", "This import was already activated; activation is never duplicated.",
                              target=("import_job", job.id))
        if job.status != "validated" or job.staging_container_id is None:
            raise blocked("not_validated", "Only a validated staged import can be activated.", target=("import_job", job.id),
                          next_action="Stage the import again from intact input.")
        staging = db.get(WorkspaceContainer, job.staging_container_id)
        # Re-check staged originals at activation: bytes must still match their content address.
        for blob in db.scalars(select(SourceBlob).where(SourceBlob.container_id == staging.id)):
            if blob.data is not None and (sha256_bytes(bytes(blob.data)) != blob.sha256 or len(blob.data) != blob.length):
                job.status = "failed"
                job.report = {**job.report, "errors": [{"code": "original_hash_mismatch", "message": "A staged original no longer matches its hash."}]}
                db.commit()
                raise blocked("original_hash_mismatch", "A staged original no longer matches its hash; activation was refused.",
                              target=("import_job", job.id))
        previous = db.get(WorkspaceContainer, ws.active_container_id) if ws.active_container_id else None
        if previous is not None:
            previous.status = "retired"
        staging.status = "active"
        job.previous_container_id = ws.active_container_id
        ws.active_container_id = staging.id
        ws.sequence = max(ws.sequence, int(staging.provenance.get("sequence", 0))) + 1
        job.status, job.activated_at, job.activation_command_id = "activated", datetime.now(UTC), command_id
        db.commit()
        return job, False
    except Exception:
        db.rollback()
        raise


def discard(db: Session, account: Account, workspace_id: UUID, job_id: UUID, capability: str) -> ImportJob:
    try:
        ws, _ = _locked(db, account, workspace_id, capability)
        job = db.get(ImportJob, job_id)
        if job is None or job.workspace_id != ws.id:
            raise not_found("import_job", job_id)
        if job.status == "activated":
            raise blocked("already_activated", "An activated import cannot be discarded.", target=("import_job", job.id))
        if job.staging_container_id:
            staging = db.get(WorkspaceContainer, job.staging_container_id)
            job.staging_container_id = None
            db.flush()
            db.delete(staging)
        job.status = "discarded"
        db.commit()
        return job
    except Exception:
        db.rollback()
        raise
