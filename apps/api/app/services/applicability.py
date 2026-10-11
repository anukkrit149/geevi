"""U7 criterion-level applicability of a published protocol version to one patient."""
import uuid
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import blocked, not_permitted
from app.core.security import digest
from app.models import sources as m
from app.models.reviews import ApplicabilityReview
from app.services import profile, protocols, scopes
from app.services import sources as source_service
from app.services.command_service import Ctx, target

ASSESSMENTS = ("match", "difference", "unknown", "not_applicable")


def start(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    protocol = protocols.require_selectable(ctx, body.protocol_version_id)
    existing = ctx.all(ApplicabilityReview, ApplicabilityReview.patient_id == patient.id, order=ApplicabilityReview.version_no)
    same = [a for a in existing if a.protocol_version_id == protocol.id]
    if any(a.status == "draft" for a in same):
        raise blocked("revision_in_progress", "An applicability draft for this protocol version already exists.", target=("applicability_review", same[-1].id))
    base = next((a for a in reversed(same) if a.status == "accepted"), None)
    snapshot = profile.capture(ctx, patient.id)
    criteria = list(base.criteria) if base else [{"requirement_id": r["id"], "assessment": None, "rationale": "", "supporting": []} for r in protocol.requirements]
    review = ctx.new(ApplicabilityReview, family_id=base.family_id if base else uuid.uuid4(), version_no=(same[-1].version_no + 1) if same else 1,
                     patient_id=patient.id, episode_id=source_service.episode_of(ctx, patient.id).id, protocol_version_id=protocol.id,
                     snapshot_id=snapshot.id, criteria=criteria, supersedes_id=base.id if base else None)
    ctx.audit("applicability.start", review)
    return target(review)


def _draft(ctx: Ctx, review_id: UUID, expected_revision: int) -> ApplicabilityReview:
    review = ctx.get(ApplicabilityReview, review_id)
    ctx.expect(review, expected_revision)
    if review.status != "draft":
        raise blocked("immutable_version", "An accepted applicability review is immutable; start a new draft to change it.",
                      target=("applicability_review", review.id), next_action="Start a new applicability draft.")
    if review.recorded_by != ctx.account.id:
        raise not_permitted("Only the author can edit this draft.", target=("applicability_review", review.id))
    return review


def save(ctx: Ctx, review_id: UUID, body) -> dict:
    review = _draft(ctx, review_id, body.expected_revision)
    review.criteria = [c.model_dump(mode="json") for c in body.criteria]
    ctx.touch(review)
    ctx.audit("applicability.save", review)
    return target(review)


def accept(ctx: Ctx, review_id: UUID, body) -> dict:
    review = _draft(ctx, review_id, body.expected_revision)
    protocol = protocols.require_selectable(ctx, review.protocol_version_id)
    criteria = {c["requirement_id"]: c for c in review.criteria}
    problems = []
    for requirement in protocol.requirements:
        criterion = criteria.get(requirement["id"])
        if criterion is None or criterion.get("assessment") not in ASSESSMENTS:
            problems.append({"requirement_id": requirement["id"], "message": "Record match, difference, unknown or not applicable."})
        elif criterion["assessment"] in ("difference", "not_applicable") and len((criterion.get("rationale") or "").strip()) < 8:
            problems.append({"requirement_id": requirement["id"], "message": f"'{criterion['assessment'].replace('_', ' ')}' needs an attributed rationale."})
        else:
            for support in criterion.get("supporting") or []:
                model = {"observation_version": m.ObservationVersion, "patient_discussion": m.PatientDiscussion,
                         "clinical_assessment": m.ClinicalAssessment, "source_document": m.SourceDocument}.get(support.get("kind"))
                record = ctx.find(model, UUID(support["id"])) if model else None
                if record is None or record.patient_id != review.patient_id:
                    problems.append({"requirement_id": requirement["id"], "message": "Supporting records must be this patient's exact versions."})
    if problems:
        raise blocked("applicability_incomplete", "Every protocol requirement needs a criterion-level assessment.",
                      target=("applicability_review", review.id), next_action="Complete the listed criteria.", details={"criteria": problems})
    # Pin the exact fact/assessment versions known at this decision.
    review.snapshot_id = profile.capture(ctx, review.patient_id).id
    for other in ctx.all(ApplicabilityReview, ApplicabilityReview.family_id == review.family_id):
        if other.status == "accepted":
            other.status = "superseded"
            ctx.touch(other)
    review.status, review.accepted_at = "accepted", datetime.now(UTC)
    review.content_digest = digest({"criteria": review.criteria, "protocol": review.protocol_version_id, "patient": review.patient_id,
                                    "snapshot": review.snapshot_id, "version": review.version_no})
    ctx.touch(review)
    ctx.audit("applicability.accept", review)
    scopes.bump(ctx, scopes.patient_scope(review.patient_id, "applicability"),
                {"event": "applicability.accepted", "applicability_id": str(review.id), "version_no": review.version_no})
    unknown = [c["requirement_id"] for c in review.criteria if c["assessment"] == "unknown"]
    return target(review, unknown_requirements=unknown)
