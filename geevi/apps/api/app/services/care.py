"""U9 handoff tasks and actual care (R20-R22, R26).

Tasks are instantiated from an exact SOP version; a sent handoff is not an accepted one; scheduling
is not delivery; and recording what happened never reactivates an older plan or infers an outcome.
"""
from uuid import UUID

from sqlalchemy import select

from app.core.errors import blocked, not_permitted
from app.models import sources as m
from app.models.care import CareEvent, PlannedEvent, Task, TaskEvent
from app.models.department import ProtocolVersion, SopVersion
from app.models.exceptions import ExceptionRequest
from app.models.identity import Account
from app.models.plans import PatientPlanVersion
from app.models.reviews import ApplicabilityReview
from app.services import plans, publication, review_dependencies, sops
from app.services import sources as source_service
from app.services.command_service import Ctx, target


def _account(ctx: Ctx, username: str) -> Account:
    account = ctx.db.scalar(select(Account).where(Account.username == username))
    if account is None:
        raise blocked("unknown_owner", f"No development account named '{username}'.", target=("account", None))
    return account


def _log(ctx: Ctx, task: Task, event: str, reason: str | None = None, **detail) -> None:
    ctx.new(TaskEvent, task_id=task.id, event=event, reason=reason, detail=detail)
    ctx.touch(task)
    ctx.audit(f"task.{event}", task, reason=reason, detail=detail)


def instantiate(ctx: Ctx, plan_id: UUID, body) -> dict:
    """Create task specifications from the SOP steps for the current approved plan (idempotent per step)."""
    plan = ctx.get(PatientPlanVersion, plan_id)
    plans.require_actionable(ctx, plan, "Assigning SOP work")
    sop = ctx.get(SopVersion, body.sop_version_id)
    if publication.lifecycle(ctx, sops.KIND, sop) != "effective":
        raise blocked("sop_not_effective", "Tasks can only be created from the currently effective SOP version.", target=("sop_version", sop.id))
    existing = {t.sop_step_id: t for t in ctx.all(Task, Task.plan_version_id == plan.id, Task.sop_version_id == sop.id)}
    created, by_step = [], dict(existing)
    for step in sop.steps:
        if step["id"] in existing:
            continue
        owner = _account(ctx, body.owners[step["id"]]) if step["id"] in body.owners else None
        task = ctx.new(Task, patient_id=plan.patient_id, episode_id=plan.episode_id, sop_version_id=sop.id, sop_step_id=step["id"],
                       plan_version_id=plan.id, action=step["title"], role=step["role"], expected_evidence=step["expected_evidence"],
                       requires=step.get("requires") or [], owner_id=owner.id if owner else None, owner_name=owner.display_name if owner else None,
                       assigned_by_id=ctx.account.id, assigned_by_name=ctx.account.display_name,
                       due=body.due[step["id"]].model_dump() if step["id"] in body.due else None)
        ctx.db.flush()
        by_step[step["id"]] = task
        created.append(task)
    for step in sop.steps:
        by_step[step["id"]].depends_on = [str(by_step[d].id) for d in step.get("depends_on") or []]
    for task in created:
        _log(ctx, task, "created", sop_version_id=str(sop.id), sop_step_id=task.sop_step_id)
    return {"target": {"kind": "patient_plan_version", "id": str(plan.id), "revision": plan.revision},
            "data": {"created": [str(t.id) for t in created], "sop_version_id": str(sop.id)}}


def gate_for(ctx: Ctx, task: Task) -> list[dict]:
    """Requirement gates of this task's SOP step, using the patient's current exception requests."""
    plan = ctx.get(PatientPlanVersion, task.plan_version_id)
    protocol = ctx.get(ProtocolVersion, plan.protocol_version_id)
    current = [e for e in ctx.all(ExceptionRequest, ExceptionRequest.patient_id == task.patient_id) if e.status != "superseded"]
    report = review_dependencies.gate_report(ctx, protocol, ctx.get(ApplicabilityReview, plan.applicability_id), current, f"step:{task.sop_step_id}")
    return [g for g in report if g["requirement_id"] in task.requires]


def update(ctx: Ctx, task_id: UUID, body) -> dict:
    """Administrative edit (owner, due, note). Touches no clinical scope, so no clinical review goes stale (R20)."""
    task = ctx.get(Task, task_id)
    ctx.expect(task, body.expected_revision)
    if task.status in ("completed", "cancelled"):
        raise blocked("task_closed", "A completed or cancelled task cannot be edited.", target=("task", task.id))
    changes = {}
    if body.owner_username:
        owner = _account(ctx, body.owner_username)
        if task.status in ("accepted", "received") and owner.id != task.owner_id:
            raise blocked("reassignment_needs_return", "Accepted work must be returned before it can be reassigned.", target=("task", task.id))
        changes["owner"] = {"from": task.owner_name, "to": owner.display_name}
        task.owner_id, task.owner_name = owner.id, owner.display_name
    if body.due is not None:
        changes["due"] = {"from": task.due, "to": body.due.model_dump()}
        task.due = body.due.model_dump()
    if body.note is not None:
        task.note = body.note
    _log(ctx, task, "updated", **changes)
    return target(task)


def send(ctx: Ctx, task_id: UUID, body) -> dict:
    task = ctx.get(Task, task_id)
    ctx.expect(task, body.expected_revision)
    if task.status not in ("draft", "returned"):
        raise blocked("wrong_state", f"A {task.status} task cannot be sent.", target=("task", task.id))
    if task.owner_id is None:
        raise blocked("owner_required", "Assign an owner before sending the handoff.", target=("task", task.id))
    plan = ctx.get(PatientPlanVersion, task.plan_version_id)
    plans.require_actionable(ctx, plan, "Sending this handoff")
    failed = [g for g in gate_for(ctx, task) if not g["satisfied"]]
    if failed:  # only this dependent dispatch is blocked; independent preparation continues
        raise blocked("dependent_scope_unresolved", f"This handoff depends on {failed[0]['requirement_id']}: {failed[0]['message']}",
                      target=("task", task.id), next_action="Resolve the requirement or its exception; other tasks are unaffected.",
                      details={"gates": failed})
    task.status = "sent"
    _log(ctx, task, "sent", to=task.owner_name)
    return target(task)


def _mine(ctx: Ctx, task_id: UUID, expected_revision: int, allowed: tuple[str, ...]) -> Task:
    task = ctx.get(Task, task_id)
    ctx.expect(task, expected_revision)
    if task.owner_id != ctx.account.id:
        raise not_permitted("Only the task's current owner can act on this handoff.", target=("task", task.id))
    if task.status not in allowed:
        raise blocked("wrong_state", f"A {task.status} task does not allow this action.", target=("task", task.id))
    return task


def receive(ctx: Ctx, task_id: UUID, body) -> dict:
    task = _mine(ctx, task_id, body.expected_revision, ("sent",))
    task.status = "received"
    _log(ctx, task, "received")
    return target(task)


def accept(ctx: Ctx, task_id: UUID, body) -> dict:
    task = _mine(ctx, task_id, body.expected_revision, ("sent", "received", "blocked"))
    task.status = "accepted"
    _log(ctx, task, "accepted")
    return target(task)


def give_back(ctx: Ctx, task_id: UUID, body, status: str) -> dict:
    task = _mine(ctx, task_id, body.expected_revision, ("sent", "received", "accepted", "blocked"))
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record why this work is returned or blocked.", target=("task", task.id))
    task.status = status  # the owner and the reason stay on the record
    _log(ctx, task, status, body.reason.strip(), owner=task.owner_name)
    return target(task)


def complete(ctx: Ctx, task_id: UUID, body) -> dict:
    task = _mine(ctx, task_id, body.expected_revision, ("accepted",))
    pending = [d for d in task.depends_on if ctx.get(Task, UUID(d)).status != "completed"]
    if pending:
        raise blocked("dependency_incomplete", "A task this work depends on is not completed.", target=("task", task.id), details={"depends_on": pending})
    if len(body.evidence.strip()) < 8:
        raise blocked("evidence_required", f"Completion needs evidence: {task.expected_evidence}.", target=("task", task.id))
    if body.care_event_id and ctx.get(CareEvent, body.care_event_id).patient_id != task.patient_id:
        raise blocked("invalid_association", "The care record belongs to a different patient.", target=("task", task.id))
    task.status = "completed"
    task.completion_evidence = {"text": body.evidence.strip(), "care_event_id": str(body.care_event_id) if body.care_event_id else None,
                                "by": ctx.account.display_name, "sequence": ctx.seq}
    _log(ctx, task, "completed", evidence=body.evidence.strip())
    return target(task)  # completing a task infers nothing about treatment outcome or discharge (R26)


def cancel(ctx: Ctx, task_id: UUID, body) -> dict:
    task = ctx.get(Task, task_id)
    ctx.expect(task, body.expected_revision)
    if task.status in ("completed", "cancelled") or len(body.reason.strip()) < 8:
        raise blocked("wrong_state", "Only open work can be cancelled, with a reason.", target=("task", task.id))
    task.status = "cancelled"
    _log(ctx, task, "cancelled", body.reason.strip())
    return target(task)


def schedule_event(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    if not (ctx.can("task.act") or ctx.can("followup.manage") or ctx.can("task.assign")):
        raise not_permitted("This account cannot schedule events.", target=("patient", patient.id))
    if body.plan_version_id and ctx.get(PatientPlanVersion, body.plan_version_id).patient_id != patient.id:
        raise blocked("invalid_association", "The plan belongs to a different patient.", target=("patient", patient.id))
    event = ctx.new(PlannedEvent, patient_id=patient.id, episode_id=source_service.episode_of(ctx, patient.id).id, event_type=body.event_type,
                    description=body.description.strip(), scheduled_time=body.scheduled_time.model_dump(), location=body.location,
                    plan_version_id=body.plan_version_id, task_id=body.task_id,
                    history=[{"event": "scheduled", "by": ctx.account.display_name, "sequence": ctx.seq}])
    ctx.audit("planned_event.schedule", event)
    return target(event)  # a schedule entry only: no care event is created


def record_care(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    plan = ctx.get(PatientPlanVersion, body.plan_version_id)
    if plan.patient_id != patient.id or plan.status not in ("approved", "superseded"):
        raise blocked("invalid_association", "Care must reference a signed plan version of this patient (current or historical).",
                      target=("patient_plan_version", plan.id))
    if body.planned_event_id and ctx.get(PlannedEvent, body.planned_event_id).patient_id != patient.id:
        raise blocked("invalid_association", "The planned event belongs to a different patient.", target=("patient", patient.id))
    if body.status != "unknown" and body.actual_time is None and body.status in ("performed", "partial"):
        raise blocked("actual_time_required", "Performed or partial care needs the time it actually happened.", target=("patient", patient.id))
    external = body.source == "external_report"
    if external and len((body.performer_name or "").strip()) < 2:
        raise blocked("performer_required", "An external report must name who performed the care; you are recorded as the transcriber.",
                      target=("patient", patient.id))
    event = ctx.new(CareEvent, patient_id=patient.id, episode_id=source_service.episode_of(ctx, patient.id).id, planned_event_id=body.planned_event_id,
                    task_id=body.task_id, status=body.status, actual_time=body.actual_time.model_dump() if body.actual_time else None,
                    narrative=body.narrative.strip(), source=body.source,
                    performer_name=body.performer_name.strip() if external else ctx.account.display_name,
                    performer_account_id=None if external else ctx.account.id,
                    transcriber_name=ctx.account.display_name if external else None, source_document_id=body.source_document_id,
                    plan_version_id=plan.id)
    ctx.audit("care.record", event, detail={"status": body.status, "source": body.source, "plan_version_no": plan.version_no})
    return target(event)  # the referenced plan's status and disposition are not touched


def request_transfer(ctx: Ctx, episode_id: UUID, body) -> dict:
    episode = ctx.get(m.Episode, episode_id)
    ctx.expect(episode, body.expected_revision)
    if episode.status != "ongoing" or len(body.reason.strip()) < 8:
        raise blocked("wrong_state", "Only an ongoing episode can be offered for transfer, with a reason.", target=("episode", episode.id))
    episode.status = "transfer_pending"
    episode.disposition = {"transfer": {"to_service": body.to_service, "reason": body.reason.strip(), "requested_by": ctx.account.display_name,
                                        "sequence": ctx.seq, "received": None}}
    ctx.touch(episode)
    ctx.audit("episode.transfer_request", episode, reason=body.reason.strip())
    return target(episode, responsible_team=episode.responsible_team)  # responsibility is unchanged until explicit receipt


def receive_transfer(ctx: Ctx, episode_id: UUID, body) -> dict:
    episode = ctx.get(m.Episode, episode_id)
    ctx.expect(episode, body.expected_revision)
    if episode.status != "transfer_pending" or len(body.receipt_note.strip()) < 8:
        raise blocked("wrong_state", "Only a pending transfer can be explicitly received, with a receipt note.", target=("episode", episode.id))
    transfer = dict(episode.disposition["transfer"])
    transfer["received"] = {"by": ctx.account.display_name, "note": body.receipt_note.strip(), "sequence": ctx.seq,
                            "previous_team": episode.responsible_team}
    episode.disposition = {"transfer": transfer}
    episode.status, episode.responsible_team = "transferred", transfer["to_service"]
    ctx.touch(episode)
    ctx.audit("episode.transfer_receive", episode, reason=body.receipt_note.strip())
    return target(episode, responsible_team=episode.responsible_team)


def task_view(ctx: Ctx, task: Task) -> dict:
    sop = ctx.get(SopVersion, task.sop_version_id)
    data = {c.name: getattr(task, c.name) for c in task.__table__.columns}
    return {**data, "sop_title": sop.title, "sop_version_no": sop.version_no, "gates": gate_for(ctx, task),
            "events": ctx.all(TaskEvent, TaskEvent.task_id == task.id)}
