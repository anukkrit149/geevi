"""U5 research questions and evidence appraisal.

Accepting an appraisal into the evidence library is its own decision (R9): it publishes no protocol,
approves no patient plan and issues no patient recommendation.
"""
import base64
import binascii
import uuid
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import DomainError, blocked, not_permitted
from app.core.security import digest, sha256_bytes
from app.models.research import EvidenceAppraisal, EvidenceSource, ResearchQuestion
from app.models.sources import SourceBlob
from app.services import extraction, reviews
from app.services.command_service import Ctx, target

APPRAISAL_FIELDS = ("population", "intervention", "comparator", "outcome", "timepoint", "study_design", "findings", "uncertainty", "limitations")


def prepare_file(content_base64: str | None, media_type: str | None) -> dict | None:
    if not content_base64:
        return None
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DomainError(422, "invalid_upload", "The uploaded content is not valid base64.") from exc
    if len(data) > get_settings().max_upload_bytes:
        raise DomainError(413, "upload_too_large", "The file exceeds the configured upload size limit.")
    if media_type != "application/pdf" or extraction.sniff_media_type(data, media_type) is None:
        raise DomainError(415, "unsupported_media", "Evidence files must be PDF documents.")
    try:
        pages = extraction.parse_pdf(data)
    except Exception:
        pages = []
    passages = []
    for page in pages:
        paragraphs = []
        for line in page["lines"]:
            box = line["bbox"]
            if paragraphs and abs(box[0] - paragraphs[-1]["bbox"][0]) < 0.5 and 0 <= box[1] - paragraphs[-1]["bbox"][3] < 8:
                paragraphs[-1]["text"] += " " + line["text"]
                paragraphs[-1]["bbox"][2] = max(box[2], paragraphs[-1]["bbox"][2])
                paragraphs[-1]["bbox"][3] = box[3]
            else:
                paragraphs.append({"text": line["text"], "bbox": list(box)})
        passages.extend({"id": f"p{page['number']}-{index}", "page": page["number"], "text": line["text"], "region": line["bbox"],
                         "page_size": [page["width"], page["height"]]} for index, line in enumerate(paragraphs, start=1))
    return {"data": data, "sha256": sha256_bytes(data), "passages": passages,
            "limits": {"text_layer": bool(passages), "note": "Passages group adjacent text-layer lines with the same indentation; keyword search only, no semantic retrieval."}}


def create_question(ctx: Ctx, body) -> dict:
    if body.origin and body.origin.get("patient_id"):
        from app.models.sources import Patient
        try:
            patient_id = UUID(str(body.origin["patient_id"]))
        except ValueError as exc:
            raise DomainError(422, "invalid_case_origin", "The research question must reference a patient in this workspace.") from exc
        ctx.get(Patient, patient_id)
    question = ctx.new(ResearchQuestion, title=body.title.strip(), question=body.question.strip(), scope=body.scope.strip(),
                       intended_use=body.intended_use.strip(), owner_id=ctx.account.id, owner_name=ctx.account.display_name,
                       origin=body.origin or {})
    ctx.audit("research.question.create", question)
    return target(question)


def _blob(ctx: Ctx, parsed: dict | None) -> SourceBlob | None:
    if parsed is None:
        return None
    blob = ctx.db.scalar(select(SourceBlob).where(SourceBlob.container_id == ctx.container_id, SourceBlob.sha256 == parsed["sha256"]))
    if blob is None:
        blob = ctx.new(SourceBlob, sha256=parsed["sha256"], length=len(parsed["data"]), media_type="application/pdf", data=parsed["data"])
        ctx.db.flush()
    return blob


def add_source(ctx: Ctx, body, parsed: dict | None) -> dict:
    blob = _blob(ctx, parsed)
    source = ctx.new(EvidenceSource, family_id=uuid.uuid4(), title=body.title.strip(), citation=body.citation.strip(),
                     source_label=body.source_label, blob_id=blob.id if blob else None, passages=parsed["passages"] if parsed else [],
                     extraction_limits=parsed["limits"] if parsed else {"text_layer": False, "note": "Citation only; no file held."})
    ctx.audit("research.source.add", source, detail={"sha256": parsed["sha256"] if parsed else None})
    return target(source)


def _flag_dependants(ctx: Ctx, source: EvidenceSource, reason: str, change: dict) -> int:
    family = {str(s.id) for s in ctx.all(EvidenceSource, EvidenceSource.family_id == source.family_id)}
    flagged = 0
    for appraisal in ctx.all(EvidenceAppraisal):
        if appraisal.status in ("accepted", "in_review") and any(c["source_id"] in family for c in appraisal.citations):
            appraisal.review_needed, appraisal.review_needed_reason = True, reason
            reviews.open_work(ctx, "dependent_review", appraisal, appraisal.recorded_by, appraisal.recorded_by_name, reason,
                              "Re-appraise against the changed source and submit a successor revision if needed.", change)
            flagged += 1
            from app.models.department import ProtocolVersion
            for protocol in ctx.all(ProtocolVersion):
                if str(appraisal.id) in protocol.evidence and protocol.status in ("approved", "published", "in_review"):
                    reviews.open_work(ctx, "dependent_review", protocol, protocol.owner_id, protocol.owner_name,
                                      f"Supporting evidence changed: {reason}", "Review whether the protocol needs a change proposal.", change)
    return flagged


def amend_source(ctx: Ctx, source_id: UUID, body, parsed: dict | None) -> dict:
    old = ctx.get(EvidenceSource, source_id)
    ctx.expect(old, body.expected_revision)
    if old.status != "active":
        raise blocked("source_not_current", "Only the current active source version can be amended.", target=("evidence_source", old.id))
    blob = _blob(ctx, parsed)
    old.status, old.status_reason = "amended", body.reason.strip()
    ctx.touch(old)
    new = ctx.new(EvidenceSource, family_id=old.family_id, version_no=old.version_no + 1, title=body.title or old.title,
                  citation=(body.citation or old.citation).strip(), source_label=old.source_label,
                  blob_id=blob.id if blob else old.blob_id, passages=parsed["passages"] if parsed else old.passages,
                  extraction_limits=parsed["limits"] if parsed else old.extraction_limits, supersedes_id=old.id)
    ctx.db.flush()
    flagged = _flag_dependants(ctx, old, f"Evidence source amended: {body.reason.strip()}", {"event": "source.amended", "source_id": str(new.id)})
    ctx.audit("research.source.amend", new, reason=body.reason.strip(), detail={"dependants": flagged})
    return target(new, dependants_flagged=flagged)


def withdraw_source(ctx: Ctx, source_id: UUID, body) -> dict:
    source = ctx.get(EvidenceSource, source_id)
    ctx.expect(source, body.expected_revision)
    if source.status == "withdrawn":
        raise blocked("source_not_current", "This source version is already withdrawn.", target=("evidence_source", source.id))
    source.status, source.status_reason = "withdrawn", body.reason.strip()
    ctx.touch(source)
    flagged = _flag_dependants(ctx, source, f"Evidence source withdrawn: {body.reason.strip()}", {"event": "source.withdrawn", "source_id": str(source.id)})
    ctx.audit("research.source.withdraw", source, reason=body.reason.strip(), detail={"dependants": flagged})
    return target(source, dependants_flagged=flagged)


def _content(body) -> dict:
    return {k: (getattr(body, k) or "").strip() for k in APPRAISAL_FIELDS}


def start_appraisal(ctx: Ctx, question_id: UUID, body) -> dict:
    question = ctx.get(ResearchQuestion, question_id)
    if question.status != "open":
        raise blocked("question_concluded", "This research question is concluded; open a new question for new evidence.", target=("research_question", question.id))
    appraisal = ctx.new(EvidenceAppraisal, question_id=question.id, family_id=uuid.uuid4(), content=_content(body),
                        citations=[c.model_dump(mode="json") for c in body.citations])
    ctx.audit("research.appraisal.start", appraisal)
    return target(appraisal)


def revise_appraisal(ctx: Ctx, appraisal_id: UUID, body) -> dict:
    """Reopen as a successor draft. The earlier accepted version stays accepted until a successor is."""
    base = ctx.get(EvidenceAppraisal, appraisal_id)
    if base.recorded_by != ctx.account.id:
        raise not_permitted("Only the appraisal author can open a successor revision.", target=("evidence_appraisal", base.id))
    family = ctx.all(EvidenceAppraisal, EvidenceAppraisal.family_id == base.family_id, order=EvidenceAppraisal.version_no)
    if any(a.status in ("draft", "in_review") for a in family):
        raise blocked("revision_in_progress", "A revision of this appraisal is already in progress.", target=("evidence_appraisal", base.id))
    if base.status not in ("accepted", "changes_requested"):
        raise blocked("not_revisable", "Only an accepted or changes-requested version can be revised.", target=("evidence_appraisal", base.id))
    draft = ctx.new(EvidenceAppraisal, question_id=base.question_id, family_id=base.family_id, version_no=family[-1].version_no + 1,
                    content=dict(base.content), citations=list(base.citations), supersedes_id=base.id)
    ctx.audit("research.appraisal.revise", draft, detail={"base": str(base.id)})
    return target(draft)


def _editable(ctx: Ctx, appraisal_id: UUID, expected_revision: int) -> EvidenceAppraisal:
    appraisal = ctx.get(EvidenceAppraisal, appraisal_id)
    ctx.expect(appraisal, expected_revision)
    if appraisal.status != "draft":
        raise blocked("immutable_version", "A submitted appraisal is immutable; open a successor revision to change it.",
                      target=("evidence_appraisal", appraisal.id), next_action="Use 'Revise' to create a successor draft.")
    if appraisal.recorded_by != ctx.account.id:
        raise not_permitted("Only the author can edit this draft.", target=("evidence_appraisal", appraisal.id))
    return appraisal


def save_appraisal(ctx: Ctx, appraisal_id: UUID, body) -> dict:
    appraisal = _editable(ctx, appraisal_id, body.expected_revision)
    appraisal.content, appraisal.citations = _content(body), [c.model_dump(mode="json") for c in body.citations]
    ctx.touch(appraisal)
    ctx.audit("research.appraisal.save", appraisal)
    return target(appraisal)


def submit_appraisal(ctx: Ctx, appraisal_id: UUID, body) -> dict:
    appraisal = _editable(ctx, appraisal_id, body.expected_revision)
    missing = [k for k in ("findings", "limitations", "study_design") if len(appraisal.content.get(k, "")) < 3]
    if missing or not appraisal.citations:
        raise blocked("appraisal_incomplete", "Cite at least one source passage and record study design, findings and limitations.",
                      target=("evidence_appraisal", appraisal.id), details={"missing": missing, "citations": len(appraisal.citations)})
    read_set = []
    for citation in appraisal.citations:
        source = ctx.find(EvidenceSource, UUID(citation["source_id"]))
        if source is None or source.status != "active" or not any(p["id"] == citation["passage_id"] for p in source.passages):
            raise blocked("source_support_not_current", "A cited passage is missing, amended or withdrawn.",
                          target=("evidence_source", citation["source_id"]), next_action="Cite a passage from the current source version.")
        read_set.append({"kind": "evidence_source", "id": str(source.id), "revision": source.revision, "passage_id": citation["passage_id"]})
    appraisal.content_digest = digest({"content": appraisal.content, "citations": appraisal.citations, "family": appraisal.family_id,
                                       "version": appraisal.version_no})
    packet = reviews.open_packet(ctx, appraisal, appraisal.content_digest, body.reviewer_username, read_set=read_set)
    appraisal.status, appraisal.packet_id = "in_review", packet.id
    ctx.touch(appraisal)
    return target(appraisal, packet_id=str(packet.id))


def _finalize(ctx: Ctx, packet, approved: bool) -> None:
    appraisal = ctx.get(EvidenceAppraisal, packet.target_id)
    if approved:
        for citation in appraisal.citations:  # source support must still be current at the commit
            source = ctx.find(EvidenceSource, UUID(citation["source_id"]))
            if source is None or source.status != "active":
                raise blocked("source_support_not_current", "A cited source changed while this appraisal was in review.",
                              target=("evidence_appraisal", appraisal.id), next_action="Ask the author for a successor revision.")
        for other in ctx.all(EvidenceAppraisal, EvidenceAppraisal.family_id == appraisal.family_id):
            if other.status == "accepted":
                other.status = "superseded"
                ctx.touch(other)
        appraisal.status, appraisal.review_needed, appraisal.review_needed_reason = "accepted", False, None
    else:
        appraisal.status = "changes_requested"
    ctx.touch(appraisal)


reviews.FINALIZERS["evidence_appraisal"] = _finalize


def conclude_question(ctx: Ctx, question_id: UUID, body) -> dict:
    question = ctx.get(ResearchQuestion, question_id)
    ctx.expect(question, body.expected_revision)
    if question.owner_id != ctx.account.id:
        raise not_permitted("Only the question owner can conclude it.", target=("research_question", question.id))
    accepted = [a for a in ctx.all(EvidenceAppraisal, EvidenceAppraisal.question_id == question.id) if a.status == "accepted"]
    if body.conclusion == "evidence_accepted" and not accepted:
        raise blocked("no_accepted_evidence", "No accepted appraisal supports this conclusion.", target=("research_question", question.id),
                      next_action="Have an appraisal independently reviewed, or conclude insufficient evidence.")
    if len((body.note or "").strip()) < 8:
        raise blocked("reason_required", "Record the reasoning for this conclusion.", target=("research_question", question.id))
    question.status, question.conclusion, question.conclusion_note = "concluded", body.conclusion, body.note.strip()
    ctx.touch(question)
    ctx.audit("research.question.conclude", question, reason=body.note.strip(), detail={"conclusion": body.conclusion})
    # Deliberately nothing else: no protocol is drafted or published and no patient record is touched.
    return target(question, conclusion=body.conclusion)
