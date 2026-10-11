from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import Commander, commander, reader
from app.core.errors import DomainError
from app.models.research import EvidenceAppraisal, EvidenceSource, ResearchQuestion
from app.models.sources import SourceBlob
from app.schemas import research as s
from app.schemas.commands import CommandResult
from app.services import fixture_loader, research, reviews
from app.services.command_service import Ctx

router = APIRouter(tags=["research"])
W = "/workspaces/{workspace_id}/research"


@router.get(W + "/reference-pack", response_model=list[s.ReferenceBrief])
def reference_pack(ctx: Ctx = Depends(reader)):
    """Attributed published-evidence briefs, separate from fictional patient documents."""
    return [e["reference"] for e in fixture_loader.manifest()["research"] if e.get("reference")]


@router.post(W + "/reference-pack/{reference_id}/import", response_model=CommandResult)
def import_reference(workspace_id: UUID, reference_id: str, body: s.CommandBase, cmd: Commander = Depends(commander)):
    import base64
    entry = next((e for e in fixture_loader.manifest()["research"] if e["id"] == reference_id and e.get("reference") and e["label"] == "public_reference"), None)
    if entry is None:
        raise DomainError(404, "reference_not_found", "This reference is not in the published evidence pack.")
    source = s.SourceCreate(command_id=body.command_id, title=entry["title"], citation=entry["citation"], source_label="public_reference",
                            filename=entry["file"].split("/")[-1], media_type="application/pdf",
                            content_base64=base64.b64encode(fixture_loader.input_path(entry["file"]).read_bytes()).decode())
    parsed = research.prepare_file(source.content_base64, source.media_type)
    return cmd.run(workspace_id, "research.reference.import", source, lambda ctx: research.add_source(ctx, source, parsed), "evidence.author")


def _source_view(ctx: Ctx, source: EvidenceSource) -> dict:
    blob = ctx.find(SourceBlob, source.blob_id)
    return {**{c.name: getattr(source, c.name) for c in source.__table__.columns}, "file_available": bool(blob and blob.data is not None),
            "sha256": blob.sha256 if blob else None}


@router.get(W + "/questions", response_model=list[s.QuestionOut])
def list_questions(ctx: Ctx = Depends(reader)):
    return ctx.all(ResearchQuestion)


@router.post(W + "/questions", response_model=CommandResult)
def create_question(workspace_id: UUID, body: s.QuestionCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.question.create", body, lambda ctx: research.create_question(ctx, body), "evidence.author")


@router.get(W + "/questions/{question_id}", response_model=s.QuestionDetail)
def get_question(question_id: UUID, ctx: Ctx = Depends(reader)):
    question = ctx.get(ResearchQuestion, question_id)
    appraisals = ctx.all(EvidenceAppraisal, EvidenceAppraisal.question_id == question.id)
    return {"question": question, "appraisals": appraisals, "reviews": reviews.history(ctx, [a.id for a in appraisals])}


@router.post(W + "/questions/{question_id}/conclude", response_model=CommandResult)
def conclude(workspace_id: UUID, question_id: UUID, body: s.QuestionConclude, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.question.conclude", body, lambda ctx: research.conclude_question(ctx, question_id, body), "evidence.author")


@router.get(W + "/sources", response_model=list[s.EvidenceSourceOut])
def list_sources(ctx: Ctx = Depends(reader)):
    return [_source_view(ctx, x) for x in ctx.all(EvidenceSource)]


@router.post(W + "/sources", response_model=CommandResult)
def add_source(workspace_id: UUID, body: s.SourceCreate, cmd: Commander = Depends(commander)):
    parsed = research.prepare_file(body.content_base64, body.media_type)
    return cmd.run(workspace_id, "research.source.add", body, lambda ctx: research.add_source(ctx, body, parsed), "evidence.author")


@router.get(W + "/sources/{source_id}", response_model=s.EvidenceSourceOut)
def get_source(source_id: UUID, ctx: Ctx = Depends(reader)):
    return _source_view(ctx, ctx.get(EvidenceSource, source_id))


@router.post(W + "/sources/{source_id}/amend", response_model=CommandResult)
def amend_source(workspace_id: UUID, source_id: UUID, body: s.SourceAmend, cmd: Commander = Depends(commander)):
    parsed = research.prepare_file(body.content_base64, body.media_type)
    return cmd.run(workspace_id, "research.source.amend", body, lambda ctx: research.amend_source(ctx, source_id, body, parsed), "evidence.author")


@router.post(W + "/sources/{source_id}/withdraw", response_model=CommandResult)
def withdraw_source(workspace_id: UUID, source_id: UUID, body: s.Reasoned, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.source.withdraw", body, lambda ctx: research.withdraw_source(ctx, source_id, body), "evidence.author")


@router.get(W + "/sources/{source_id}/content", responses={200: {"content": {"application/pdf": {}}}})
def source_content(source_id: UUID, ctx: Ctx = Depends(reader)):
    source = ctx.get(EvidenceSource, source_id)
    blob = ctx.find(SourceBlob, source.blob_id)
    if blob is None or blob.data is None:
        raise DomainError(404, "original_unavailable", "No file is held for this evidence source.", target=("evidence_source", source.id))
    return Response(bytes(blob.data), media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=\"evidence\"", "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff",
        "X-Content-SHA256": blob.sha256})


@router.post(W + "/questions/{question_id}/appraisals", response_model=CommandResult)
def start_appraisal(workspace_id: UUID, question_id: UUID, body: s.AppraisalCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.appraisal.start", body, lambda ctx: research.start_appraisal(ctx, question_id, body), "evidence.author")


@router.post(W + "/appraisals/{appraisal_id}/save", response_model=CommandResult)
def save_appraisal(workspace_id: UUID, appraisal_id: UUID, body: s.AppraisalSave, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.appraisal.save", body, lambda ctx: research.save_appraisal(ctx, appraisal_id, body), "evidence.author")


@router.post(W + "/appraisals/{appraisal_id}/submit", response_model=CommandResult)
def submit_appraisal(workspace_id: UUID, appraisal_id: UUID, body: s.SubmitForReview, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.appraisal.submit", body, lambda ctx: research.submit_appraisal(ctx, appraisal_id, body), "evidence.author")


@router.post(W + "/appraisals/{appraisal_id}/revise", response_model=CommandResult)
def revise_appraisal(workspace_id: UUID, appraisal_id: UUID, body: s.CommandBase, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "research.appraisal.revise", body, lambda ctx: research.revise_appraisal(ctx, appraisal_id, body), "evidence.author")


@router.get(W + "/appraisals", response_model=list[s.AppraisalOut])
def list_appraisals(status: str | None = None, ctx: Ctx = Depends(reader)):
    return [a for a in ctx.all(EvidenceAppraisal) if not status or a.status == status]
