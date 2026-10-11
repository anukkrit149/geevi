"""U10 concerns and routine follow-up (R23-R26).

A concern and a routine review obligation are separate duties. Acknowledging a concern is not a
response. A justified unchanged follow-up records a new encounter decision and the next obligation
while the same signed plan stays in force. Nothing here infers triage, outcome or discharge.
"""
from uuid import UUID

from sqlalchemy import select

from app.core.errors import blocked
from app.models import sources as m
from app.models.care import PlannedEvent
from app.models.exceptions import ExceptionRequest
from app.models.follow_up import Concern, ConcernEvent, EncounterDecision, FollowUpObligation
from app.models.identity import Account
from app.models.plans import PatientPlanVersion
from app.services import impacts, plans, profile, review_dependencies
from app.services import sources as source_service
from app.services.command_service import Ctx, target


def _account(ctx: Ctx, username: str) -> Account:
    account = ctx.db.scalar(select(Account).where(Account.username == username))
    if account is None:
        raise blocked("unknown_owner", f"No development account named '{username}'.", target=("account", None))
    return account


def _concern_event(ctx: Ctx, concern: Concern, event: str, narrative: str | None = None, **detail) -> None:
    ctx.new(ConcernEvent, concern_id=concern.id, event=event, narrative=narrative, detail=detail)
    ctx.touch(concern)
    ctx.audit(f"concern.{event}", concern, reason=narrative)


def report_concern(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    owner = _account(ctx, body.owner_username)
    concern = ctx.new(Concern, patient_id=patient.id, episode_id=source_service.episode_of(ctx, patient.id).id, narrative=body.narrative.strip(),
                      attributed_to=body.attributed_to, responsible_service=body.responsible_service, owner_id=owner.id, owner_name=owner.display_name,
                      unresolved_duty="Acknowledge and respond")
    ctx.db.flush()
    _concern_event(ctx, concern, "reported", body.narrative.strip(), attributed_to=body.attributed_to)
    return target(concern)


def _concern(ctx: Ctx, concern_id: UUID, expected_revision: int) -> Concern:
    concern = ctx.get(Concern, concern_id)
    ctx.expect(concern, expected_revision)
    if concern.status == "closed":
        raise blocked("concern_closed", "This concern is closed.", target=("concern", concern.id))
    return concern


def acknowledge(ctx: Ctx, concern_id: UUID, body) -> dict:
    concern = _concern(ctx, concern_id, body.expected_revision)
    if concern.status != "open":
        raise blocked("wrong_state", "Only a newly reported concern can be acknowledged.", target=("concern", concern.id))
    concern.status, concern.unresolved_duty = "acknowledged", "Respond to the concern (an acknowledgement is not a response)"
    _concern_event(ctx, concern, "acknowledged")
    return target(concern)


def respond(ctx: Ctx, concern_id: UUID, body) -> dict:
    concern = _concern(ctx, concern_id, body.expected_revision)
    if len(body.narrative.strip()) < 8:
        raise blocked("reason_required", "Record what was actually said or done in response.", target=("concern", concern.id))
    concern.status, concern.unresolved_duty = "responded", "Clinician review of the concern and response"
    _concern_event(ctx, concern, "responded", body.narrative.strip())
    return target(concern)


def escalate(ctx: Ctx, concern_id: UUID, body) -> dict:
    concern = _concern(ctx, concern_id, body.expected_revision)
    if len(body.narrative.strip()) < 8:
        raise blocked("reason_required", "Record why this concern is escalated.", target=("concern", concern.id))
    owner = _account(ctx, body.owner_username)
    concern.status, concern.responsible_service = "escalated", body.to_service
    concern.owner_id, concern.owner_name = owner.id, owner.display_name
    concern.unresolved_duty = f"Escalated to {body.to_service}: review and respond"
    _concern_event(ctx, concern, "escalated", body.narrative.strip(), to_service=body.to_service, owner=owner.display_name)
    return target(concern)


def review(ctx: Ctx, concern_id: UUID, body) -> dict:
    concern = _concern(ctx, concern_id, body.expected_revision)
    if len(body.narrative.strip()) < 8:
        raise blocked("reason_required", "Record the clinician's review.", target=("concern", concern.id))
    events = [e.event for e in ctx.all(ConcernEvent, ConcernEvent.concern_id == concern.id)]
    if body.close and "responded" not in events:
        raise blocked("response_required", "A concern cannot be closed before a response is recorded; a notification is not a response.",
                      target=("concern", concern.id), next_action=f"{concern.owner_name} records the response.")
    concern.status = "closed" if body.close else "reviewed"
    concern.unresolved_duty = None if body.close else ("Respond to the patient" if "responded" not in events else "Close when no duty remains")
    _concern_event(ctx, concern, "closed" if body.close else "reviewed", body.narrative.strip())
    return target(concern)


def _note(ctx: Ctx, obligation: FollowUpObligation, event: str, reason: str | None = None, **detail) -> None:
    obligation.history = [*obligation.history, {"event": event, "by": ctx.account.display_name, "sequence": ctx.seq, "reason": reason, **detail}]
    ctx.touch(obligation)
    ctx.audit(f"follow_up.{event}", obligation, reason=reason, detail=detail)


def _open(ctx: Ctx, obligation_id: UUID, expected_revision: int) -> FollowUpObligation:
    obligation = ctx.get(FollowUpObligation, obligation_id)
    ctx.expect(obligation, expected_revision)
    if obligation.state in ("fulfilled", "cancelled"):
        raise blocked("obligation_closed", f"This follow-up obligation is {obligation.state}.", target=("follow_up_obligation", obligation.id))
    return obligation


def schedule(ctx: Ctx, obligation_id: UUID, body) -> dict:
    """Administrative scheduling/rescheduling of the appointment. The authored clinical timing is untouched."""
    obligation = _open(ctx, obligation_id, body.expected_revision)
    rescheduling = obligation.scheduled_time is not None
    if rescheduling and len((body.reason or "").strip()) < 8:
        raise blocked("reason_required", "Record why the follow-up is rescheduled.", target=("follow_up_obligation", obligation.id))
    previous = obligation.scheduled_time
    obligation.scheduled_time, obligation.state = body.scheduled_time.model_dump(), "scheduled"
    planned = next(iter(ctx.all(PlannedEvent, PlannedEvent.obligation_id == obligation.id)), None)
    if planned is None:
        ctx.new(PlannedEvent, patient_id=obligation.patient_id, episode_id=obligation.episode_id, event_type="follow_up_review",
                description=obligation.purpose, scheduled_time=obligation.scheduled_time, plan_version_id=obligation.plan_version_id,
                obligation_id=obligation.id, history=[{"event": "scheduled", "by": ctx.account.display_name, "sequence": ctx.seq}])
    else:
        planned.scheduled_time, planned.status = obligation.scheduled_time, "rescheduled"
        planned.history = [*planned.history, {"event": "rescheduled", "by": ctx.account.display_name, "sequence": ctx.seq, "from": previous}]
        ctx.touch(planned)
    _note(ctx, obligation, "rescheduled" if rescheduling else "scheduled", body.reason, scheduled_time=obligation.scheduled_time, previous=previous)
    return target(obligation)


def mark(ctx: Ctx, obligation_id: UUID, body, state: str) -> dict:
    obligation = _open(ctx, obligation_id, body.expected_revision)
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record the reason.", target=("follow_up_obligation", obligation.id))
    obligation.state = state
    _note(ctx, obligation, state, body.reason.strip(), outcome="unknown" if state == "missed" else None)
    return target(obligation)  # a missed review records an unknown outcome; the duty stays owned


def transfer(ctx: Ctx, obligation_id: UUID, body) -> dict:
    obligation = _open(ctx, obligation_id, body.expected_revision)
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record why this duty is transferred.", target=("follow_up_obligation", obligation.id))
    owner = _account(ctx, body.owner_username)
    previous = obligation.owner_name
    obligation.owner_id, obligation.owner_name, obligation.state = owner.id, owner.display_name, "transferred"
    _note(ctx, obligation, "transferred", body.reason.strip(), previous_owner=previous, owner=owner.display_name)
    return target(obligation)


def propose_due_change(ctx: Ctx, obligation_id: UUID, body) -> dict:
    """A change to AUTHORED clinical timing is not an administrative edit: it opens scoped clinical review (R20)."""
    obligation = _open(ctx, obligation_id, body.expected_revision)
    if not obligation.authored:
        raise blocked("not_authored", "This is an administrative obligation; reschedule it instead.", target=("follow_up_obligation", obligation.id))
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record why the clinical timing should change.", target=("follow_up_obligation", obligation.id))
    obligation.pending_change = {"due": body.due.model_dump(), "reason": body.reason.strip(), "requested_by": ctx.account.display_name, "sequence": ctx.seq}
    _note(ctx, obligation, "clinical_change_requested", body.reason.strip(), proposed_due=body.due.model_dump())
    created = impacts.nominate_for_obligation_change(ctx, obligation, {"event": "obligation.change_requested", "obligation_id": str(obligation.id),
                                                                    "proposed_due": body.due.model_dump()})
    return target(obligation, **created)


def create(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    plan = plans.current_approved(ctx, patient.id)
    if plan is None:
        raise blocked("plan_not_active", "A follow-up obligation references the patient's approved plan.", target=("patient", patient.id))
    owner = _account(ctx, body.owner_username)
    obligation = ctx.new(FollowUpObligation, patient_id=patient.id, episode_id=plan.episode_id, plan_version_id=plan.id, purpose=body.purpose.strip(),
                         authored=False, due=body.due.model_dump(), owner_id=owner.id, owner_name=owner.display_name,
                         history=[{"event": "created", "by": ctx.account.display_name, "sequence": ctx.seq}])
    ctx.audit("follow_up.create", obligation)
    return target(obligation)


def decide(ctx: Ctx, obligation_id: UUID, body) -> dict:
    obligation = _open(ctx, obligation_id, body.expected_revision)
    plan = ctx.get(PatientPlanVersion, obligation.plan_version_id)
    current = plans.current_approved(ctx, obligation.patient_id)
    if len(body.rationale.strip()) < 8:
        raise blocked("reason_required", "Record the rationale for this encounter decision.", target=("follow_up_obligation", obligation.id))
    packet: dict = {}
    if body.decision == "continue_unchanged":
        # Guarded review: the same signed plan must still be supportable.
        if current is None or current.family_id != plan.family_id:
            raise blocked("plan_not_active", "There is no approved plan to continue.", target=("follow_up_obligation", obligation.id))
        plans.require_actionable(ctx, current, "Continuing unchanged")
        for exception_id in current.exception_ids:
            request = ctx.get(ExceptionRequest, UUID(exception_id))
            state = review_dependencies.exception_state(request)
            if state != "approved":
                raise blocked("exception_not_approved", f"The {request.exception_type} exception this plan relies on is {state}.",
                              target=("exception_request", request.id), next_action="Review the exception before continuing the plan.")
        failed = [g for g in plans.gates(ctx, current) if not g["satisfied"]]
        if failed:
            raise blocked(failed[0]["code"], failed[0]["message"], target=("patient_plan_version", current.id), details={"gates": failed})
        if obligation.pending_change:
            raise blocked("plan_review_needed", "A requested change to this obligation's clinical timing is unresolved.", target=("follow_up_obligation", obligation.id))
        if body.next is None:
            raise blocked("next_obligation_required", "An unchanged continuation records the next follow-up obligation.", target=("follow_up_obligation", obligation.id))
        snapshot = profile.capture(ctx, obligation.patient_id)
        packet = {"plan_version_id": str(current.id), "plan_digest": current.content_digest, "profile_snapshot_id": str(snapshot.id),
                  "profile_digest": snapshot.digest, "knowledge_cutoff_seq": snapshot.knowledge_cutoff_seq}
        plan = current
    encounter = ctx.new(m.Encounter, patient_id=obligation.patient_id, episode_id=obligation.episode_id, encounter_type="routine_follow_up",
                        status="occurred", actual_time=body.actual_time.model_dump() if body.actual_time else None, summary=body.rationale.strip())
    ctx.db.flush()
    next_obligation = None
    if body.next is not None and body.decision in ("continue_unchanged", "more_information"):
        owner = _account(ctx, body.next.owner_username)
        next_obligation = ctx.new(FollowUpObligation, patient_id=obligation.patient_id, episode_id=obligation.episode_id, plan_version_id=plan.id,
                                  purpose=body.next.purpose.strip(), authored=True, due=body.next.due.model_dump(), owner_id=owner.id,
                                  owner_name=owner.display_name, previous_obligation_id=obligation.id,
                                  history=[{"event": "created", "by": ctx.account.display_name, "sequence": ctx.seq, "note": "Next obligation from encounter decision"}])
        ctx.db.flush()
    decision = ctx.new(EncounterDecision, obligation_id=obligation.id, encounter_id=encounter.id, patient_id=obligation.patient_id,
                       plan_version_id=plan.id, decision=body.decision, rationale=body.rationale.strip(), input_packet=packet,
                       next_obligation_id=next_obligation.id if next_obligation else None)
    if body.decision in ("continue_unchanged", "revise"):
        obligation.state = "fulfilled"
    _note(ctx, obligation, f"decision:{body.decision}", body.rationale.strip(), encounter_id=str(encounter.id))
    # The plan id is retained for an unchanged continuation; a revision goes through plan approval (U8).
    return target(obligation, decision_id=str(decision.id), plan_version_id=str(plan.id),
                  next_obligation_id=str(next_obligation.id) if next_obligation else None, encounter_id=str(encounter.id))
