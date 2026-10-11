from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import Commander, commander, reader
from app.core.errors import DomainError
from app.models import sources as m
from app.schemas import sources as s
from app.schemas.commands import CommandResult
from app.services import sources
from app.services.command_service import Ctx

router = APIRouter(tags=["sources"])
W = "/workspaces/{workspace_id}"
SAFE_TYPES = {"application/pdf", "image/png", "image/jpeg"}


@router.get(W + "/sources", response_model=list[s.DocumentOut])
def list_documents(patient_id: UUID | None = None, status: str | None = None, ctx: Ctx = Depends(reader)):
    docs = ctx.all(m.SourceDocument)
    if patient_id:
        docs = [d for d in docs if d.patient_id == patient_id or (d.claimed_identity or {}).get("intended_patient_id") == str(patient_id)]
    if status:
        docs = [d for d in docs if d.association_status == status]
    return [sources.document_view(ctx, d) for d in docs]


@router.post(W + "/sources", response_model=CommandResult)
def upload_document(workspace_id: UUID, body: s.DocumentUpload, cmd: Commander = Depends(commander)):
    parsed = sources.prepare_upload(body.content_base64, body.media_type, body.doc_kind)
    return cmd.run(workspace_id, "source.receive", body, lambda ctx: sources.receive_document(ctx, body, parsed), "source.import")


@router.get(W + "/sources/{document_id}", response_model=s.DocumentBundle)
def get_document(document_id: UUID, ctx: Ctx = Depends(reader)):
    doc = ctx.get(m.SourceDocument, document_id)
    reports = [r for r in ctx.all(m.ReportVersion) if str(doc.id) in r.document_ids]
    specimen_ids = {UUID(x) for r in reports for x in r.specimen_ids}
    candidates = ctx.all(m.ExtractionCandidate, m.ExtractionCandidate.document_id == doc.id)
    # Reading order of the original: page, then position on the page.
    candidates.sort(key=lambda c: (c.source_ref.get("page") or 0, (c.source_ref.get("region") or [0, 0])[1], c.recorded_seq))
    return {"document": sources.document_view(ctx, doc), "reports": [sources.report_view(ctx, r) for r in reports],
            "specimens": [ctx.get(m.Specimen, i) for i in specimen_ids], "candidates": candidates,
            "observations": [sources.observation_view(ctx, o) for o in ctx.all(m.ObservationVersion, m.ObservationVersion.document_id == doc.id)],
            "reviews": [r for r in ctx.all(m.SourceReview) if r.candidate_id in {c.id for c in candidates}]}


@router.get(W + "/sources/{document_id}/content", responses={200: {"content": {"application/octet-stream": {}}}})
def get_content(document_id: UUID, ctx: Ctx = Depends(reader)):
    """Authenticated original bytes. Served inline with safe headers; never interpreted as markup."""
    doc = ctx.get(m.SourceDocument, document_id)
    blob = ctx.get(m.SourceBlob, doc.blob_id)
    if blob.data is None or blob.availability != "available" or blob.media_type not in SAFE_TYPES:
        raise DomainError(404, "original_unavailable", "The original file for this document is not available.",
                          target=("source_document", doc.id), next_action="Supply the exact original file (matching hash).")
    return Response(bytes(blob.data), media_type=blob.media_type, headers={
        "Content-Disposition": "inline; filename=\"original\"", "Cache-Control": "no-store, private",
        "Content-Security-Policy": "default-src 'none'; sandbox", "X-Content-Type-Options": "nosniff",
        "X-Content-SHA256": blob.sha256})


@router.post(W + "/sources/{document_id}/associate", response_model=CommandResult)
def associate(workspace_id: UUID, document_id: UUID, body: s.AssociateBody, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "source.associate", body, lambda ctx: sources.associate_document(ctx, document_id, body), "source.import")


@router.post(W + "/sources/{document_id}/reject", response_model=CommandResult)
def reject(workspace_id: UUID, document_id: UUID, body: s.RejectDocument, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "source.reject", body, lambda ctx: sources.reject_document(ctx, document_id, body), "source.import")


@router.post(W + "/sources/{document_id}/candidates", response_model=CommandResult)
def manual_candidate(workspace_id: UUID, document_id: UUID, body: s.ManualCandidate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "candidate.manual", body, lambda ctx: sources.add_manual_candidate(ctx, document_id, body), "source.review")


@router.post(W + "/candidates/{candidate_id}/review", response_model=CommandResult)
def review_candidate(workspace_id: UUID, candidate_id: UUID, body: s.CandidateReview, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "candidate.review", body, lambda ctx: sources.review_candidate(ctx, candidate_id, body), "source.review")


@router.get(W + "/observations", response_model=list[s.ObservationOut])
def list_observations(patient_id: UUID, include_history: bool = False, ctx: Ctx = Depends(reader)):
    rows = ctx.all(m.ObservationVersion, m.ObservationVersion.patient_id == patient_id)
    return [sources.observation_view(ctx, o) for o in rows if include_history or o.status == "current"]


@router.get(W + "/reports", response_model=list[s.ReportVersionOut])
def list_reports(patient_id: UUID, ctx: Ctx = Depends(reader)):
    return [sources.report_view(ctx, r) for r in ctx.all(m.ReportVersion, m.ReportVersion.patient_id == patient_id)]


@router.get(W + "/specimens", response_model=list[s.SpecimenOut])
def list_specimens(patient_id: UUID, ctx: Ctx = Depends(reader)):
    return ctx.all(m.Specimen, m.Specimen.patient_id == patient_id)
