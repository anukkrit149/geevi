"""U8 typed, scoped exception requests and decisions (R17/R18).

An exception covers one requirement of one protocol version for one patient. Default requirements
are non-waivable. Approving an exception never approves a plan and never changes the protocol.
"""
import uuid
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import blocked, not_permitted
from app.core.policy import REVIEW_POLICY
from app.core.security import digest
from app.models import sources as m
from app.models.department import ProtocolVersion
from app.models.exceptions import ExceptionDecision, ExceptionRequest
from app.services import impacts, scopes
from app.services import sources as source_service
from app.services.command_service import Ctx, target
from app.services.review_dependencies import exception_state


def _digest(values: dict) -> str:
    return digest({k: values[k] for k in ("exception_type", "requirement_id", "protocol_version_id", "patient_id", "departure", "rationale",
                                           "evidence", "expires_at", "review_trigger", "version_no")})


def _create(ctx: Ctx, patient_id: UUID, body, base: ExceptionRequest | None) -> ExceptionRequest:
    patient = ctx.get(m.Patient, patient_id)
    protocol = ctx.get(ProtocolVersion, body.protocol_version_id)
    requirement = next((r for r in protocol.requirements if r["id"] == body.requirement_id), None)
    if requirement is None:
        raise blocked("unknown_requirement", "The protocol version has no such requirement.", target=("protocol_version", protocol.id))
    waiver = requirement.get("waiver") or {}
    if not waiver.get("allowed"):
        raise blocked("non_waivable", f"{requirement['id']} is non-waivable; no exception can be requested for it.",
                      target=("protocol_version", protocol.id), next_action="Resolve the requirement itself; it cannot be bypassed.")
    if waiver["exception_type"] != body.exception_type:
        raise blocked("exception_type_not_permitted", f"{requirement['id']} only permits a {waiver['exception_type']} exception.",
                      target=("protocol_version", protocol.id))
    if not body.expires_at and not (body.review_trigger or "").strip():
        raise blocked("expiry_or_trigger_required", "An exception needs an expiry time or a review trigger.", target=("patient", patient.id))
    if body.expires_at and body.expires_at <= datetime.now(UTC):
        raise blocked("expiry_or_trigger_required", "The expiry time must be in the future.", target=("patient", patient.id))
    discussions = ctx.all(m.PatientDiscussion, m.PatientDiscussion.patient_id == patient.id)
    if body.exception_type == "operational" and not discussions:
        raise blocked("discussion_required", "An operational exception needs a documented patient discussion first.",
                      target=("patient", patient.id), next_action="Record the patient discussion, then request the exception.")
    values = {"exception_type": body.exception_type, "requirement_id": body.requirement_id, "protocol_version_id": protocol.id,
              "patient_id": patient.id, "departure": body.departure.strip(), "rationale": body.rationale.strip(),
              "evidence": [str(e) for e in body.evidence], "expires_at": body.expires_at, "review_trigger": body.review_trigger,
              "version_no": (base.version_no + 1) if base else 1}
    rule = REVIEW_POLICY["exceptions"][body.exception_type]
    request = ctx.new(ExceptionRequest, family_id=base.family_id if base else uuid.uuid4(), episode_id=source_service.episode_of(ctx, patient.id).id,
                      discussion_id=discussions[-1].id if discussions else None, required_approvals=dict(rule), content_digest=_digest(values),
                      supersedes_id=base.id if base else None, owner_id=ctx.account.id, owner_name=ctx.account.display_name, **values)
    ctx.db.flush()
    scopes.bump(ctx, scopes.patient_scope(patient.id, "exceptions"), {"event": "exception.requested", "exception_id": str(request.id),
                                                                    "requirement_id": request.requirement_id})
    return request


def request(ctx: Ctx, patient_id: UUID, body) -> dict:
    record = _create(ctx, patient_id, body, None)
    ctx.audit("exception.request", record)
    return target(record)


def revise(ctx: Ctx, request_id: UUID, body) -> dict:
    """An edited request is a new version: earlier decisions do not carry over."""
    base = ctx.get(ExceptionRequest, request_id)
    ctx.expect(base, body.expected_revision)
    if base.status in ("superseded", "withdrawn"):
        raise blocked("not_revisable", "This exception request version is no longer current.", target=("exception_request", base.id))
    if base.recorded_by != ctx.account.id:
        raise not_permitted("Only the requester can revise this exception request.", target=("exception_request", base.id))
    body.protocol_version_id, body.requirement_id, body.exception_type = base.protocol_version_id, base.requirement_id, base.exception_type
    record = _create(ctx, base.patient_id, body, base)
    base.status = "superseded"
    ctx.touch(base)
    ctx.audit("exception.revise", record, detail={"supersedes": str(base.id)})
    return target(record)


def decide(ctx: Ctx, request_id: UUID, body) -> dict:
    record = ctx.get(ExceptionRequest, request_id)
    ctx.expect(record, body.expected_revision)
    rule = record.required_approvals
    ctx.require(rule["capability"], ("exception_request", record.id))  # server grant for this exception type; client fields are ignored
    if record.status != "pending":
        raise blocked("exception_not_pending", f"This exception request is {exception_state(record)}; decisions apply only to a pending request.",
                      target=("exception_request", record.id))
    decisions = ctx.all(ExceptionDecision, ExceptionDecision.request_id == record.id)
    if any(d.recorded_by == ctx.account.id for d in decisions):
        raise blocked("already_decided", "This account already recorded its decision on this exact request version.", target=("exception_request", record.id))
    rationale = (body.rationale or "").strip()
    if len(rationale) < 8:
        raise blocked("reason_required", "Record the rationale for this exception decision.", target=("exception_request", record.id))
    ctx.new(ExceptionDecision, request_id=record.id, request_digest=record.content_digest, decision=body.decision, rationale=rationale)
    approvals = len({d.recorded_by for d in decisions if d.decision == "approve"}) + (1 if body.decision == "approve" else 0)
    if body.decision == "reject":
        record.status = "rejected"
    elif approvals >= rule["approvals"]:
        record.status = "approved"
    ctx.touch(record)
    ctx.audit("exception.decide", record, reason=rationale, detail={"decision": body.decision, "status": record.status})
    scopes.bump(ctx, scopes.patient_scope(record.patient_id, "exceptions"), {"event": f"exception.{body.decision}", "exception_id": str(record.id),
                                                                           "requirement_id": record.requirement_id, "status": record.status})
    # Deliberately no side effect on any plan: plan approval is a separate, exact decision.
    return target(record, status=record.status, approvals=approvals, approvals_required=rule["approvals"])


def record_expiry(ctx: Ctx, request_id: UUID, body) -> dict:
    """Record that an approved exception has passed its expiry. Future actions in its scope are blocked and
    impact review is nominated; completed historical care is untouched."""
    record = ctx.get(ExceptionRequest, request_id)
    ctx.expect(record, body.expected_revision)
    if exception_state(record) != "expired" or record.status == "expired":
        raise blocked("not_expired", "This exception has not reached its expiry time, or its expiry is already recorded.", target=("exception_request", record.id))
    record.status = "expired"
    ctx.touch(record)
    ctx.audit("exception.expire", record)
    scopes.bump(ctx, scopes.patient_scope(record.patient_id, "exceptions"), {"event": "exception.expired", "exception_id": str(record.id),
                                                                           "requirement_id": record.requirement_id})
    created = impacts.nominate_for_exception_expiry(ctx, record)
    return target(record, **created)


def withdraw(ctx: Ctx, request_id: UUID, body) -> dict:
    record = ctx.get(ExceptionRequest, request_id)
    ctx.expect(record, body.expected_revision)
    if record.recorded_by != ctx.account.id or record.status != "pending":
        raise blocked("not_withdrawable", "Only the requester can withdraw a pending exception request.", target=("exception_request", record.id))
    record.status = "withdrawn"
    ctx.touch(record)
    ctx.audit("exception.withdraw", record, reason=body.reason)
    scopes.bump(ctx, scopes.patient_scope(record.patient_id, "exceptions"), {"event": "exception.withdrawn", "exception_id": str(record.id)})
    return target(record)


def view(ctx: Ctx, record: ExceptionRequest) -> dict:
    decisions = ctx.all(ExceptionDecision, ExceptionDecision.request_id == record.id)
    data = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    state = exception_state(record)
    decided = {d.recorded_by for d in decisions}
    return {**data, "effective_status": state, "decisions": decisions,
            "approvals_recorded": len({d.recorded_by for d in decisions if d.decision == "approve"}),
            "next_action": (f"Awaiting {record.required_approvals['approvals'] - len(decided)} more decision(s) from accounts holding "
                            f"{record.required_approvals['capability']}") if state == "pending" else None}
