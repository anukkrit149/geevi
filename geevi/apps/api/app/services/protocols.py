"""U6 shared departmental protocol versions."""
import re
from uuid import UUID

from app.core.errors import blocked
from app.models.department import ProtocolVersion
from app.models.research import EvidenceAppraisal
from app.services import publication, reviews
from app.services.command_service import Ctx


def _validate(ctx: Ctx, record: ProtocolVersion) -> None:
    ids = [r.get("id") for r in record.requirements]
    if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Z][A-Z0-9-]{2,40}", i or "") for i in ids):
        raise blocked("invalid_requirements", "Requirements need unique stable identifiers.", target=("protocol_version", record.id))
    for requirement in record.requirements:
        waiver = requirement.get("waiver") or {}
        if waiver.get("allowed") and waiver.get("exception_type") not in ("operational", "clinical"):
            raise blocked("invalid_requirements", f"{requirement['id']}: a waivable requirement must name the permitted exception type.",
                          target=("protocol_version", record.id))
    if not record.evidence:
        raise blocked("evidence_required", "Link at least one accepted evidence appraisal.", target=("protocol_version", record.id),
                      next_action="Have the supporting appraisal independently accepted first.")
    for appraisal_id in record.evidence:
        appraisal = ctx.find(EvidenceAppraisal, UUID(appraisal_id))
        if appraisal is None or appraisal.status != "accepted" or appraisal.review_needed:
            raise blocked("evidence_not_accepted", "Supporting evidence must be an accepted appraisal with no open review work.",
                          target=("evidence_appraisal", appraisal_id), next_action="Resolve the evidence review before submitting the protocol.")


def _on_publish(ctx: Ctx, record: ProtocolVersion) -> dict:
    from app.services import impacts
    return impacts.nominate_for_protocol_change(ctx, record, "protocol_published") if record.predecessor_id else {}


def _on_withdraw(ctx: Ctx, record: ProtocolVersion) -> dict:
    from app.services import impacts
    return impacts.nominate_for_protocol_change(ctx, record, "protocol_withdrawn")


KIND = publication.DocKind(ProtocolVersion, ("scope", "summary", "requirements", "evidence"), _validate, _on_publish, _on_withdraw)
reviews.FINALIZERS["protocol_version"] = publication.finalizer(KIND)


def values(body) -> dict:
    return {"title": body.title.strip(), "scope": body.scope.strip(), "summary": body.summary,
            "requirements": [r.model_dump(mode="json", exclude_none=True) for r in body.requirements], "evidence": [str(e) for e in body.evidence]}


def require_selectable(ctx: Ctx, version_id: UUID) -> ProtocolVersion:
    """Only an effective, non-withdrawn, non-superseded version can support a NEW plan selection."""
    record = ctx.get(ProtocolVersion, version_id)
    state = publication.lifecycle(ctx, KIND, record)
    if state != "effective":
        raise blocked("protocol_not_selectable", f"This protocol version is {state.replace('_', ' ')} and cannot support a new selection.",
                      target=("protocol_version", record.id), next_action="Select the currently effective version.", details={"lifecycle": state})
    return record
