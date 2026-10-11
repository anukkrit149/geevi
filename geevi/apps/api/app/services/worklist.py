"""Read projections for the Today worklist and the patient timeline (U12 backend support).

Projections only: nothing here creates an approval or changes a record.
"""
from uuid import UUID

from app.models import sources as m
from app.models.care import CareEvent, PlannedEvent, Task, TaskEvent
from app.models.exceptions import ExceptionDecision, ExceptionRequest
from app.models.follow_up import Concern, ConcernEvent, EncounterDecision, FollowUpObligation
from app.models.impacts import ChangeEvent, ImpactReview
from app.models.plans import PatientPlanVersion, PlanApproval, PlanDisposition
from app.models.reviews import ApplicabilityReview, ReviewAssignment, ReviewPacket, WorkItem
from app.services.command_service import Ctx
from app.services.review_dependencies import exception_state


def _entry(kind: str, title: str, *, detail=None, patient_id=None, target_kind=None, target_id=None, owner=None, next_action=None, state=None) -> dict:
    return {"kind": kind, "title": title, "detail": detail, "patient_id": patient_id, "target_kind": target_kind, "target_id": target_id,
            "owner": owner, "next_action": next_action, "state": state}


def _link(ctx: Ctx, kind: str, target_id):
    """Appraisals are opened through their research question."""
    if kind == "evidence_appraisal":
        from app.models.research import EvidenceAppraisal
        appraisal = ctx.find(EvidenceAppraisal, target_id)
        return ("research_question", appraisal.question_id) if appraisal else (kind, target_id)
    return kind, target_id


def today(ctx: Ctx) -> dict:
    me = ctx.account.id
    names = {p.id: p.display_name for p in ctx.all(m.Patient)}
    items: list[dict] = []
    for packet in ctx.all(ReviewPacket, ReviewPacket.status == "open"):
        if packet.target_kind != "patient_plan_version" and any(a.assignee_id == me for a in ctx.all(ReviewAssignment, ReviewAssignment.packet_id == packet.id)):
            kind, tid = _link(ctx, packet.target_kind, packet.target_id)
            items.append(_entry("review", f"Independent review requested: {packet.target_kind.replace('_', ' ')}", detail=f"Submitted by {packet.author_name}",
                                target_kind=kind, target_id=tid, owner=ctx.account.display_name, next_action="Approve or object with a rationale"))
    for task in ctx.all(Task):
        if task.owner_id == me and task.status in ("sent", "received", "accepted", "blocked"):
            items.append(_entry("task", task.action, detail=f"{names.get(task.patient_id)} · {task.status}", patient_id=task.patient_id, target_kind="task",
                                target_id=task.id, owner=task.owner_name, state=task.status,
                                next_action={"sent": "Receive or accept the handoff", "received": "Accept or return", "accepted": "Complete with evidence",
                                             "blocked": "Resolve the block or return"}[task.status]))
        elif ctx.can("task.assign") and task.status in ("draft", "returned"):
            items.append(_entry("task", task.action, detail=f"{names.get(task.patient_id)} · {task.status}", patient_id=task.patient_id, target_kind="task",
                                target_id=task.id, owner=task.assigned_by_name, state=task.status, next_action="Send the handoff to its owner"))
    for impact in ctx.all(ImpactReview):
        if impact.owner_id == me and impact.state != "closed":
            event = ctx.get(ChangeEvent, impact.change_event_id)
            items.append(_entry("impact", event.description, detail=names.get(impact.patient_id), patient_id=impact.patient_id, target_kind="impact_review",
                                target_id=impact.id, owner=impact.owner_name, state=impact.state,
                                next_action="Classify relevance" if impact.needs_classification else "Record a disposition"))
    for item in ctx.all(m.ExpectedInput):
        if item.owner_id == me and item.state in ("pending", "unknown", "failed"):
            items.append(_entry("expected_input", f"Expected: {item.artifact}", detail=f"{names.get(item.patient_id)} · {item.state}", patient_id=item.patient_id,
                                target_kind="expected_input", target_id=item.id, owner=item.owner_name, next_action=item.next_action, state=item.state))
    for obligation in ctx.all(FollowUpObligation):
        if obligation.owner_id == me and obligation.state not in ("fulfilled", "cancelled"):
            items.append(_entry("follow_up", obligation.purpose, detail=f"{names.get(obligation.patient_id)} · {obligation.state}", patient_id=obligation.patient_id,
                                target_kind="follow_up_obligation", target_id=obligation.id, owner=obligation.owner_name, state=obligation.state,
                                next_action="Schedule the review" if obligation.state in ("open", "missed") else "Hold the review; clinician records the decision"))
        elif ctx.can("followup.decide") and obligation.state in ("scheduled", "transferred"):
            items.append(_entry("follow_up", obligation.purpose, detail=f"{names.get(obligation.patient_id)} · {obligation.state}", patient_id=obligation.patient_id,
                                target_kind="follow_up_obligation", target_id=obligation.id, owner=obligation.owner_name, state=obligation.state,
                                next_action="Record the encounter decision after the review"))
    for concern in ctx.all(Concern):
        if concern.status != "closed" and (concern.owner_id == me or (ctx.can("concern.review") and concern.status in ("responded", "escalated"))):
            items.append(_entry("concern", concern.narrative[:90], detail=f"{names.get(concern.patient_id)} · {concern.status}", patient_id=concern.patient_id,
                                target_kind="concern", target_id=concern.id, owner=concern.owner_name, next_action=concern.unresolved_duty, state=concern.status))
    for request in ctx.all(ExceptionRequest, ExceptionRequest.status == "pending"):
        decided = {d.recorded_by for d in ctx.all(ExceptionDecision, ExceptionDecision.request_id == request.id)}
        if ctx.can(request.required_approvals["capability"]) and me not in decided and exception_state(request) == "pending":
            items.append(_entry("exception", f"{request.exception_type.title()} exception awaiting your decision: {request.requirement_id}",
                                detail=names.get(request.patient_id), patient_id=request.patient_id, target_kind="exception_request", target_id=request.id,
                                owner=request.owner_name, next_action="Approve or reject with a rationale", state="pending"))
    for work in ctx.all(WorkItem, WorkItem.status == "open"):
        if work.owner_id == me:
            kind, tid = _link(ctx, work.target_kind, work.target_id)
            items.append(_entry("work", work.reason, target_kind=kind, target_id=tid, owner=work.owner_name, next_action=work.next_action, state=work.work_kind))
    if ctx.can("plan.approve"):
        for plan in ctx.all(PatientPlanVersion):
            if plan.status in ("draft", "submitted") and plan.recorded_by == me:
                items.append(_entry("plan", f"Plan v{plan.version_no} is {plan.status}", detail=names.get(plan.patient_id), patient_id=plan.patient_id,
                                    target_kind="patient_plan_version", target_id=plan.id, owner=ctx.account.display_name, state=plan.status,
                                    next_action="Submit the exact version for signature" if plan.status == "draft" else "Review the frozen packet and sign"))
    if ctx.can("source.import"):
        for doc in ctx.all(m.SourceDocument):
            if doc.association_status in ("pending", "quarantined"):
                pid = doc.patient_id or ((doc.claimed_identity or {}).get("intended_patient_id") and UUID(doc.claimed_identity["intended_patient_id"]))
                items.append(_entry("source", f"“{doc.title}” needs identity review", detail=f"{names.get(pid, 'Unassociated')} · {doc.association_status}",
                                    patient_id=pid, target_kind="source_document", target_id=doc.id, next_action="Review identity and associate or reject",
                                    state=doc.association_status))
    if ctx.can("source.review"):
        waiting: dict[UUID, int] = {}
        for cand in ctx.all(m.ExtractionCandidate, m.ExtractionCandidate.status == "unreviewed"):
            waiting[cand.document_id] = waiting.get(cand.document_id, 0) + 1
        for doc_id, count in waiting.items():
            doc = ctx.get(m.SourceDocument, doc_id)
            if doc.association_status == "associated":
                items.append(_entry("source", f"{count} finding(s) in “{doc.title}” await source verification", detail=names.get(doc.patient_id),
                                    patient_id=doc.patient_id, target_kind="source_document", target_id=doc.id, next_action="Verify against the original", state="unreviewed"))
    return {"account": ctx.account.display_name, "items": items, "counts": {k: sum(1 for i in items if i["kind"] == k) for k in sorted({i["kind"] for i in items})}}


def timeline(ctx: Ctx, patient_id: UUID) -> list[dict]:
    """Chronological record of what was known, planned, accepted and actually done. Planned and actual stay separate lanes."""
    ctx.get(m.Patient, patient_id)
    rows: list[dict] = []

    def add(record, lane: str, title: str, *, detail=None, clinical=None, kind=None, seq=None, actor=None):
        rows.append({"seq": seq if seq is not None else record.recorded_seq, "recorded_at": record.recorded_at, "lane": lane, "kind": kind or record.kind,
                     "title": title, "detail": detail, "clinical_time": clinical, "actor": actor or record.recorded_by_name, "target_kind": record.kind,
                     "target_id": record.id})

    for doc in ctx.all(m.SourceDocument, m.SourceDocument.patient_id == patient_id):
        add(doc, "source", f"Received: {doc.title}", detail=f"{doc.issuer or 'Unknown issuer'} · {doc.association_status}", clinical=doc.received_time)
    for report in ctx.all(m.ReportVersion, m.ReportVersion.patient_id == patient_id):
        if report.relation_kind != "original":
            add(report, "source", f"Report {report.relation_kind.replace('_', ' ')} (version {report.version_no})", detail=report.scope_note, clinical=report.issued_time)
    for a in ctx.all(m.ClinicalAssessment, m.ClinicalAssessment.patient_id == patient_id):
        add(a, "decision", f"Clinical assessment v{a.version_no}", detail=a.narrative[:140])
    for d in ctx.all(m.PatientDiscussion, m.PatientDiscussion.patient_id == patient_id):
        add(d, "decision", f"Patient discussion v{d.version_no} (attributed to {d.attributed_to})", detail=d.goals[:140])
    for r in ctx.all(ApplicabilityReview, ApplicabilityReview.patient_id == patient_id):
        if r.status != "draft":
            add(r, "decision", f"Applicability review v{r.version_no} accepted")
    for e in ctx.all(ExceptionRequest, ExceptionRequest.patient_id == patient_id):
        add(e, "decision", f"{e.exception_type.title()} exception requested: {e.requirement_id}", detail=e.departure)
        for decision in ctx.all(ExceptionDecision, ExceptionDecision.request_id == e.id):
            add(decision, "decision", f"Exception {decision.decision}d: {e.requirement_id}", detail=decision.rationale)
    plans = ctx.all(PatientPlanVersion, PatientPlanVersion.patient_id == patient_id)
    for plan in plans:
        for approval in ctx.all(PlanApproval, PlanApproval.plan_version_id == plan.id):
            add(approval, "decision", f"Plan v{plan.version_no} approved (demonstration signature)", detail=plan.intent[:140])
        for disposition in ctx.all(PlanDisposition, PlanDisposition.plan_version_id == plan.id):
            if disposition.reason != "Approved":
                add(disposition, "decision", f"Plan v{plan.version_no} disposition: {disposition.disposition}", detail=disposition.reason)
    for task in ctx.all(Task, Task.patient_id == patient_id):
        for event in ctx.all(TaskEvent, TaskEvent.task_id == task.id):
            if event.event not in ("created", "updated"):
                add(event, "handoff", f"Handoff {event.event}: {task.action}", detail=event.reason or f"Owner: {task.owner_name}")
    for planned in ctx.all(PlannedEvent, PlannedEvent.patient_id == patient_id):
        add(planned, "planned", f"Scheduled: {planned.description}", detail=planned.location, clinical=planned.scheduled_time)
    for care in ctx.all(CareEvent, CareEvent.patient_id == patient_id):
        who = care.performer_name + (f" (transcribed by {care.transcriber_name})" if care.transcriber_name else "")
        add(care, "actual", f"Care {care.status.replace('_', ' ')}: {care.narrative[:100]}", detail=f"Performed by {who}", clinical=care.actual_time, actor=who)
    for concern in ctx.all(Concern, Concern.patient_id == patient_id):
        for event in ctx.all(ConcernEvent, ConcernEvent.concern_id == concern.id):
            add(event, "concern", f"Concern {event.event}", detail=(event.narrative or concern.narrative)[:140])
    for obligation in ctx.all(FollowUpObligation, FollowUpObligation.patient_id == patient_id):
        add(obligation, "planned", f"Follow-up obligation: {obligation.purpose}", detail=f"Owner {obligation.owner_name} · {obligation.state}", clinical=obligation.due)
        for decision in ctx.all(EncounterDecision, EncounterDecision.obligation_id == obligation.id):
            add(decision, "decision", f"Encounter decision: {decision.decision.replace('_', ' ')}", detail=decision.rationale[:140])
    for impact in ctx.all(ImpactReview, ImpactReview.patient_id == patient_id):
        event = ctx.get(ChangeEvent, impact.change_event_id)
        add(impact, "impact", f"Impact review opened: {event.description}", detail=f"Owner {impact.owner_name} · {impact.state}" + (f" · {impact.disposition}" if impact.disposition else ""))
    rows.sort(key=lambda r: (r["seq"], r["recorded_at"]))
    return rows
