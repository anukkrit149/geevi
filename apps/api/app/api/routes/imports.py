from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_account, member, reader
from app.core.errors import not_found, not_permitted
from app.db.session import get_db
from app.models.identity import Account
from app.models.imports import ImportJob, LegacyRecord, RecoverySnapshot
from app.schemas import imports as s
from app.schemas.archives import Archive, ArchiveImportBody
from app.services import archives, legacy_import, staging
from app.services.command_service import Ctx

router = APIRouter(tags=["imports"])
W = "/workspaces/{workspace_id}"
IMPORT_CAPS = {"legacy": "legacy.import", "archive": "archive.import"}


def _operator(ctx: Ctx) -> None:
    if not (ctx.can("legacy.import") or ctx.can("archive.import")):
        raise not_permitted("Import and recovery views need an import grant in this workspace.")


@router.get(W + "/imports", response_model=list[s.ImportJobOut])
def list_jobs(workspace_id: UUID, ctx: Ctx = Depends(member)):
    _operator(ctx)
    return list(ctx.db.scalars(select(ImportJob).where(ImportJob.workspace_id == workspace_id).order_by(ImportJob.created_at)))


@router.get(W + "/imports/{job_id}", response_model=s.ImportJobOut)
def get_job(workspace_id: UUID, job_id: UUID, ctx: Ctx = Depends(member)):
    _operator(ctx)
    job = ctx.db.get(ImportJob, job_id)
    if job is None or job.workspace_id != workspace_id:
        raise not_found("import_job", job_id)
    return job


@router.post(W + "/imports/legacy", response_model=s.ImportJobOut)
def import_legacy(workspace_id: UUID, body: s.LegacyImportBody, account: Account = Depends(current_account), db: Session = Depends(get_db)):
    """Stage an explicit legacy conversion. Nothing becomes active until a separate activation command."""
    prepared = legacy_import.prepare(body)
    return staging.stage(db, account, workspace_id, capability="legacy.import", kind="legacy", command_id=body.command_id,
                         fingerprint=prepared.fingerprint, origin="legacy_import", provenance={"source": "legacy casebook prototype"},
                         builder=lambda ctx: legacy_import.convert(ctx, prepared))


@router.get(W + "/archive", response_model=Archive, response_model_by_alias=True)
def export_archive(workspace_id: UUID, mode: str = "full", account: Account = Depends(current_account), db: Session = Depends(get_db)):
    """Consistent snapshot of every record and original. mode=review omits bytes and is labelled incomplete."""
    return archives.export(db, account, workspace_id, "full" if mode == "full" else "review")


@router.post(W + "/imports/archive", response_model=s.ImportJobOut)
def import_archive(workspace_id: UUID, body: ArchiveImportBody, request: Request, account: Account = Depends(current_account),
                   db: Session = Depends(get_db)):
    """Validate an archive into a separate staging container. Activation is a distinct operator command."""
    archives.check_size(request.headers.get("content-length"))
    prepared = archives.prepare(body.archive)
    return staging.stage(db, account, workspace_id, capability="archive.import", kind="archive", command_id=body.command_id,
                         fingerprint=prepared["fingerprint"], origin="archive_restore",
                         provenance={"source": "archive", "source_workspace": prepared["header"].get("workspace"),
                                     "source_container": prepared["header"].get("container")},
                         builder=lambda ctx: archives.restore(ctx, prepared))


@router.post(W + "/imports/{job_id}/activate", response_model=s.ActivationOut)
def activate(workspace_id: UUID, job_id: UUID, body: s.ActivateBody, account: Account = Depends(current_account), db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    capability = IMPORT_CAPS.get(job.kind if job else "", "archive.import")
    job, replayed = staging.activate(db, account, workspace_id, job_id, body.command_id, capability)
    return {"job": job, "active_container_id": job.staging_container_id, "replayed": replayed}


@router.post(W + "/imports/{job_id}/discard", response_model=s.ImportJobOut)
def discard(workspace_id: UUID, job_id: UUID, body: s.DiscardBody, account: Account = Depends(current_account), db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    return staging.discard(db, account, workspace_id, job_id, IMPORT_CAPS.get(job.kind if job else "", "archive.import"))


@router.get(W + "/legacy-records", response_model=list[s.LegacyRecordOut])
def legacy_records(patient_id: UUID | None = None, ctx: Ctx = Depends(reader)):
    where = [LegacyRecord.patient_id == patient_id] if patient_id else []
    return ctx.all(LegacyRecord, *where)


@router.get(W + "/recovery-snapshots", response_model=list[s.RecoverySnapshotOut])
def recovery_snapshots(ctx: Ctx = Depends(member)):
    if not (ctx.can("records.read") or ctx.can("archive.import") or ctx.can("legacy.import")):
        raise not_permitted("This account cannot view recovery evidence in this workspace.")
    return ctx.all(RecoverySnapshot)
