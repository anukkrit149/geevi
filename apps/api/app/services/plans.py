"""U8 exact patient-plan approval (R16/R18/R19).

Save, submit and sign are three separate server actions. The signature covers one frozen packet:
exact plan content, applicability, protocol, discussion and exception versions. Currency is
re-checked at the durable commit; a stale or partial signature is impossible.
"""
import uuid
from uuid import UUID

from sqlalchemy import select

from app.core.errors import DomainError, blocked
from app.core.security import digest
from app.models import sources as m
from app.models.department import ProtocolVersion
from app.models.exceptions import ExceptionRequest
from app.models.follow_up import FollowUpObligation
from app.models.identity import Account
from app.models.impacts import ImpactReview
from app.models.plans import PatientPlanVersion, PlanApproval, PlanDisposition
from app.models.reviews import ApplicabilityReview, ReviewPacket
from app.services import protocols, publication, review_dependencies, scopes
from app.services import sources as source_service
from app.services.command_service import Ctx, target

STATEMENT = ("Demonstration signature by a fictional development identity over this exact packet. "
             "It is not a verified institutional signature and not a clinical order.")
CONTENT = ("protocol_version_id", "applicability_id", "discussion_id", "exception_ids", "intent", "alternatives", "rationale", "obligations")


def _digest(plan: PatientPlanVersion) -> str:
    return digest({"family": plan.family_id, "version": plan.version_no, "patient": plan.patient_id, **{f: getattr(plan, f) for f in CONTENT}})


def _values(ctx: Ctx, patient_id: UUID, body) -> dict:
    applicability = ctx.get(ApplicabilityReview, body.applicability_id)
    if applicability.patient_id != patient_id:
        raise blocked("invalid_association", "The applicability review belongs to a different patient.", target=("applicability_review", applicability.id))
    for exception_id in body.exception_ids:
        request = ctx.get(ExceptionRequest, exception_id)
        if request.patient_id != patient_id or request.protocol_version_id != applicability.protocol_version_id:
            raise blocked("invalid_association", "An exception must cover this patient and this protocol version.", target=("exception_request", request.id))
    for obligation in body.obligations:
        if ctx.db.scalar(select(Account).where(Account.username == obligation.owner_username)) is None:
            raise blocked("unknown_owner", f"No development account named '{obligation.owner_username}'.", target=("patient", patient_id))
    if body.discussion_id and ctx.get(m.PatientDiscussion, body.discussion_id).patient_id != patient_id:
        raise blocked("invalid_association", "The discussion belongs to a different patient.", target=("patient_discussion", body.discussion_id))
    return {"protocol_version_id": applicability.protocol_version_id, "applicability_id": applicability.id, "discussion_id": body.discussion_id,
            "exception_ids": [str(e) for e in body.exception_ids], "intent": body.intent.strip(), "alternatives": body.alternatives,
            "rationale": body.rationale, "obligations": [o.model_dump(mode="json") for o in body.obligations]}


def family_versions(ctx: Ctx, patient_id: UUID) -> list[PatientPlanVersion]:
    return ctx.all(PatientPlanVersion, PatientPlanVersion.patient_id == patient_id, order=PatientPlanVersion.version_no)


def current_approved(ctx: Ctx, patient_id: UUID) -> PatientPlanVersion | None:
    return next((p for p in reversed(family_versions(ctx, patient_id)) if p.status == "approved"), None)


def start(ctx: Ctx, patient_id: UUID, body) -> dict:
    """New draft. An existing signed plan stays in force, untouched, while its successor is drafted."""
    patient = ctx.get(m.Patient, patient_id)
    versions = family_versions(ctx, patient.id)
    if any(p.status in ("draft", "submitted") for p in versions):
        raise blocked("revision_in_progress", "A plan draft for this patient is already in progress.", target=("patient", patient.id),
                      next_action="Continue the existing draft.")
    previous = current_approved(ctx, patient.id)
    values = _values(ctx, patient.id, body)
    protocols.require_selectable(ctx, values["protocol_version_id"])
    plan = ctx.new(PatientPlanVersion, family_id=versions[0].family_id if versions else uuid.uuid4(), version_no=(versions[-1].version_no + 1) if versions else 1,
                   patient_id=patient.id, episode_id=source_service.episode_of(ctx, patient.id).id, previous_version_id=previous.id if previous else None, **values)
    ctx.audit("plan.start", plan)
    return target(plan)


def _own(ctx: Ctx, plan_id: UUID, expected_revision: int, status: str) -> PatientPlanVersion:
    plan = ctx.get(PatientPlanVersion, plan_id)
    ctx.expect(plan, expected_revision)
    if plan.status != status:
        raise blocked("immutable_version" if plan.status in ("approved", "superseded") else "wrong_state",
                      f"This plan version is {plan.status}; this action needs a {status} version.", target=("patient_plan_version", plan.id),
                      next_action="Signed versions are immutable: draft a successor to change the plan." if plan.status in ("approved", "superseded") else None)
    return plan


def save(ctx: Ctx, plan_id: UUID, body) -> dict:
    plan = _own(ctx, plan_id, body.expected_revision, "draft")
    for key, value in _values(ctx, plan.patient_id, body).items():
        setattr(plan, key, value)
    ctx.touch(plan)
    ctx.audit("plan.save", plan)
    return target(plan)


def submit(ctx: Ctx, plan_id: UUID, body) -> dict:
    """Freeze the exact decision set into a packet with its read set and watched scope revisions."""
    plan = _own(ctx, plan_id, body.expected_revision, "draft")
    applicability = ctx.get(ApplicabilityReview, plan.applicability_id)
    if applicability.status != "accepted":
        raise blocked("required_review_absent", "The plan must pin the currently accepted applicability review.",
                      target=("applicability_review", applicability.id), next_action="Accept the applicability review, then pin it to the plan.")
    discussions = ctx.all(m.PatientDiscussion, m.PatientDiscussion.patient_id == plan.patient_id)
    if not discussions or plan.discussion_id != discussions[-1].id:
        raise blocked("discussion_not_current", "The plan must pin the latest documented patient discussion.",
                      target=("patient", plan.patient_id), next_action="Record the discussion or pin its latest version.")
    if len(plan.intent) < 12:
        raise blocked("plan_incomplete", "Document the individual intent of this plan.", target=("patient_plan_version", plan.id))
    plan.content_digest = _digest(plan)
    read_set, watch_set = review_dependencies.freeze(ctx, plan)
    packet = ctx.new(ReviewPacket, target_kind="patient_plan_version", target_id=plan.id, target_digest=plan.content_digest,
                     policy={"rule": {"approve_capability": "plan.approve"}, "note": "Fictional demonstration policy."},
                     read_set=read_set, watch_set=watch_set, author_id=ctx.account.id, author_name=ctx.account.display_name)
    ctx.db.flush()
    plan.status, plan.packet_id = "submitted", packet.id
    ctx.touch(plan)
    ctx.audit("plan.submit", plan, detail={"packet_id": str(packet.id), "digest": plan.content_digest})
    return target(plan, packet_id=str(packet.id), digest=plan.content_digest)


def reopen(ctx: Ctx, plan_id: UUID, body) -> dict:
    plan = _own(ctx, plan_id, body.expected_revision, "submitted")
    plan.status, plan.packet_id = "draft", None
    ctx.touch(plan)
    ctx.audit("plan.reopen", plan)
    return target(plan)


def gates(ctx: Ctx, plan: PatientPlanVersion) -> list[dict]:
    protocol = ctx.get(ProtocolVersion, plan.protocol_version_id)
    pinned = [ctx.get(ExceptionRequest, UUID(e)) for e in plan.exception_ids]
    return review_dependencies.gate_report(ctx, protocol, ctx.get(ApplicabilityReview, plan.applicability_id), pinned, "plan_approval")


def approve(ctx: Ctx, plan_id: UUID, body) -> dict:
    plan = _own(ctx, plan_id, body.expected_revision, "submitted")
    packet = ctx.get(ReviewPacket, plan.packet_id)
    # 1. The signature names the exact packet and digest the signer reviewed.
    if body.packet_id != packet.id or body.digest != packet.target_digest or _digest(plan) != packet.target_digest:
        raise DomainError(409, "stale_target", "The signature does not match the exact plan version frozen for review.",
                          target=("patient_plan_version", plan.id), next_action="Reload the frozen packet and review it again.",
                          details={"frozen_digest": packet.target_digest})
    # 2. Read set and watched scopes are re-checked under the workspace lock.
    review_dependencies.check_current(ctx, ("patient_plan_version", plan.id), packet.read_set, packet.watch_set)
    protocol = ctx.get(ProtocolVersion, plan.protocol_version_id)
    state = publication.lifecycle(ctx, protocols.KIND, protocol)
    if state != "effective":
        raise blocked("protocol_not_selectable", f"The pinned protocol version is {state}; it cannot support a new approval.",
                      target=("protocol_version", protocol.id), next_action="Assess applicability against the effective version.")
    # 3. Unclassified incoming clinical material must be classified before a new approval.
    unclassified = [i for i in ctx.all(ImpactReview, ImpactReview.patient_id == plan.patient_id) if i.needs_classification and i.state != "closed"]
    if unclassified:
        raise blocked("classification_required", "New clinical material for this patient has not been classified for impact.",
                      target=("impact_review", unclassified[0].id), next_action=f"{unclassified[0].owner_name} classifies the open impact item(s).",
                      details={"impact_ids": [str(i.id) for i in unclassified]})
    # 4. Requirement gates: missing inputs and pending/rejected/expired exceptions cannot satisfy the guard.
    failed = [g for g in gates(ctx, plan) if not g["satisfied"]]
    if failed:
        raise blocked(failed[0]["code"], failed[0]["message"], target=("patient_plan_version", plan.id),
                      next_action="Resolve the listed requirement(s); approval of the affected plan stays pending.", details={"gates": failed})
    approval = ctx.new(PlanApproval, plan_version_id=plan.id, packet_id=packet.id, target_digest=packet.target_digest, read_set=packet.read_set,
                       watch_set=packet.watch_set, statement=STATEMENT)
    packet.status = "approved"
    previous = ctx.find(PatientPlanVersion, plan.previous_version_id)
    if previous is not None and previous.status == "approved":
        previous.status = "superseded"  # signed history is retained; only its disposition changes
        ctx.touch(previous)
        ctx.new(PlanDisposition, plan_family_id=plan.family_id, plan_version_id=previous.id, disposition="superseded",
                reason=f"Superseded by approved version {plan.version_no}")
    plan.status = "approved"
    ctx.touch(plan)
    ctx.new(PlanDisposition, plan_family_id=plan.family_id, plan_version_id=plan.id, disposition="active", reason="Approved")
    existing = {o.plan_obligation_id for o in ctx.all(FollowUpObligation, FollowUpObligation.patient_id == plan.patient_id)
                if o.state not in ("fulfilled", "cancelled")}
    for obligation in plan.obligations:
        if obligation["id"] in existing:
            continue
        owner = ctx.db.scalar(select(Account).where(Account.username == obligation["owner_username"]))
        ctx.new(FollowUpObligation, patient_id=plan.patient_id, episode_id=plan.episode_id, plan_version_id=plan.id, purpose=obligation["purpose"],
                authored=True, plan_obligation_id=obligation["id"], due=obligation["due"], owner_id=owner.id, owner_name=owner.display_name,
                history=[{"event": "created", "by": ctx.account.display_name, "sequence": ctx.seq, "note": "Authored by the signed plan"}])
    ctx.audit("plan.approve", plan, detail={"packet_id": str(packet.id), "digest": packet.target_digest, "approval_id": str(approval.id)})
    scopes.bump(ctx, scopes.patient_scope(plan.patient_id, "plan"), {"event": "plan.approved", "plan_version_id": str(plan.id)})
    return target(plan, approval_id=str(approval.id), digest=packet.target_digest)


def set_disposition(ctx: Ctx, plan_id: UUID, body) -> dict:
    plan = ctx.get(PatientPlanVersion, plan_id)
    ctx.expect(plan, body.expected_revision)
    if plan.status != "approved":
        raise blocked("wrong_state", "Only the current approved plan has a changeable disposition.", target=("patient_plan_version", plan.id))
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record the reason for this disposition.", target=("patient_plan_version", plan.id))
    record = ctx.new(PlanDisposition, plan_family_id=plan.family_id, plan_version_id=plan.id, disposition=body.disposition, reason=body.reason.strip())
    ctx.audit("plan.disposition", plan, reason=body.reason.strip(), detail={"disposition": body.disposition})
    return target(plan, disposition=record.disposition)  # the signed content and its revision are untouched


def disposition_of(ctx: Ctx, plan: PatientPlanVersion) -> str | None:
    rows = ctx.all(PlanDisposition, PlanDisposition.plan_version_id == plan.id)
    return rows[-1].disposition if rows else None


def currency(ctx: Ctx, plan: PatientPlanVersion) -> dict:
    """Review currency is separate from disposition: a signed plan can be active AND review-needed."""
    open_impacts = [i for i in ctx.all(ImpactReview, ImpactReview.plan_version_id == plan.id) if i.state != "closed"]
    reasons = [{"impact_id": str(i.id), "scope": i.scope_key, "owner": i.owner_name, "state": i.state,
                "needs_classification": i.needs_classification} for i in open_impacts]
    return {"status": "review_needed" if reasons else "current", "reasons": reasons}


def view(ctx: Ctx, plan: PatientPlanVersion) -> dict:
    packet = ctx.find(ReviewPacket, plan.packet_id)
    approvals = ctx.all(PlanApproval, PlanApproval.plan_version_id == plan.id)
    pending_changes = review_dependencies.changes_since(ctx, packet.read_set, packet.watch_set) if packet is not None and plan.status == "submitted" else []
    return {"plan": plan, "packet": packet, "approval": approvals[-1] if approvals else None, "disposition": disposition_of(ctx, plan),
            "dispositions": ctx.all(PlanDisposition, PlanDisposition.plan_version_id == plan.id), "currency": currency(ctx, plan),
            "gates": gates(ctx, plan), "packet_changes": pending_changes, "decision_context": decision_context(ctx, plan)}


def decision_context(ctx: Ctx, plan: PatientPlanVersion) -> dict:
    """Readable clinical context from the exact versions pinned to this plan, never the latest profile."""
    applicability = ctx.get(ApplicabilityReview, plan.applicability_id)
    snapshot = ctx.get(m.ProfileSnapshot, applicability.snapshot_id)
    protocol = ctx.get(ProtocolVersion, plan.protocol_version_id)
    assessment = ctx.find(m.ClinicalAssessment, snapshot.assessment_id)
    discussion = ctx.find(m.PatientDiscussion, plan.discussion_id)
    findings = [ctx.get(m.ObservationVersion, UUID(x)) for x in snapshot.observation_ids]
    requirements = {r["id"]: r["text"] for r in protocol.requirements}
    requests = [ctx.get(ExceptionRequest, UUID(x)) for x in plan.exception_ids]
    return {"protocol_title": protocol.title, "protocol_version": protocol.version_no, "protocol_scope": protocol.scope,
            "assessment": assessment.narrative if assessment else None, "uncertainty": assessment.uncertainty if assessment else None,
            "patient_goals": discussion.goals if discussion else None, "preferences": discussion.preferences if discussion else None,
            "knowledge_cutoff_seq": snapshot.knowledge_cutoff_seq,
            "findings": [{"analyte": o.analyte, "value_text": o.value_text, "units": o.units, "result_state": o.result_state,
                          "specimen_label": source_service.observation_view(ctx, o)["specimen_label"], "document_id": str(o.document_id)} for o in findings],
            "unresolved": snapshot.unresolved,
            "criteria": [{**c, "requirement_text": requirements.get(c["requirement_id"], c["requirement_id"])} for c in applicability.criteria],
            "exceptions": [{"requirement_id": e.requirement_id, "departure": e.departure, "rationale": e.rationale,
                            "exception_type": e.exception_type, "effective_status": review_dependencies.exception_state(e)} for e in requests]}


def require_actionable(ctx: Ctx, plan: PatientPlanVersion, action: str) -> None:
    """Targeted impacts block dependent NEW handoffs/continuations; historical care stays recordable."""
    if plan.status != "approved" or disposition_of(ctx, plan) != "active":
        raise blocked("plan_not_active", f"{action} needs the current approved, active plan.", target=("patient_plan_version", plan.id))
    state = currency(ctx, plan)
    if state["status"] != "current":
        owners = sorted({r["owner"] for r in state["reasons"] if r["owner"]})
        raise blocked("plan_review_needed", f"{action} is blocked while impact review of this plan is open.",
                      target=("patient_plan_version", plan.id), next_action=f"{', '.join(owners) or 'The plan owner'} resolves the open impact review(s).",
                      details={"reasons": state["reasons"]})

