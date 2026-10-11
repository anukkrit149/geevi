"""U11 knowledge/source change -> separately owned patient impact reviews (R13/R19).

Impact identity is change event + patient/episode + plan version + scope. Duplicate delivery returns
the same impact; a later change keeps its own reason. Nothing here ever changes a plan: adoption
closes only with a linked, newly approved successor plan.
"""
from uuid import UUID

from app.core.errors import blocked
from app.models.impacts import ChangeEvent, ImpactReview
from app.models.plans import PatientPlanVersion, PlanApproval
from app.services.command_service import Ctx, target


def _event(ctx: Ctx, event_kind: str, dedupe_key: str, source_kind: str, source_id, description: str, detail: dict) -> ChangeEvent:
    from sqlalchemy import select
    event = ctx.db.scalar(select(ChangeEvent).where(ChangeEvent.container_id == ctx.container_id, ChangeEvent.dedupe_key == dedupe_key))
    if event is None:
        event = ctx.new(ChangeEvent, event_kind=event_kind, dedupe_key=dedupe_key, source_kind=source_kind, source_id=source_id,
                        description=description, detail={"events": [detail]})
        ctx.db.flush()
    elif detail not in event.detail.get("events", []):
        event.detail = {"events": [*event.detail.get("events", []), detail]}
    return event


def _open(ctx: Ctx, event: ChangeEvent, plan: PatientPlanVersion, scope_key: str, *, needs_classification: bool) -> tuple[ImpactReview, bool]:
    from sqlalchemy import select
    existing = ctx.db.scalar(select(ImpactReview).where(
        ImpactReview.container_id == ctx.container_id, ImpactReview.change_event_id == event.id, ImpactReview.plan_version_id == plan.id,
        ImpactReview.scope_key == scope_key))
    if existing is not None:
        if existing.state != "closed" and existing.needs_classification and not needs_classification:
            existing.needs_classification = False  # a pinned fact was corrected: relevance is now certain
            ctx.touch(existing)
        return existing, False
    approvals = ctx.all(PlanApproval, PlanApproval.plan_version_id == plan.id)
    owner = approvals[-1] if approvals else plan
    impact = ctx.new(ImpactReview, change_event_id=event.id, patient_id=plan.patient_id, episode_id=plan.episode_id, plan_version_id=plan.id,
                     scope_key=scope_key, owner_id=owner.recorded_by, owner_name=owner.recorded_by_name, needs_classification=needs_classification,
                     history=[{"event": "opened", "sequence": ctx.seq, "reason": event.description}])
    ctx.db.flush()
    ctx.audit("impact.open", impact, reason=event.description)
    return impact, True


def _live_plans(ctx: Ctx, **where) -> list[PatientPlanVersion]:
    """Approved plan versions still in force (one per patient): the exact dependants to review."""
    from app.services import plans
    result = []
    for plan in ctx.all(PatientPlanVersion, PatientPlanVersion.status == "approved"):
        if plans.disposition_of(ctx, plan) in ("active", "held") and all(getattr(plan, k) == v for k, v in where.items()):
            result.append(plan)
    return result


def nominate_for_protocol_change(ctx: Ctx, record, event_kind: str) -> dict:
    """Runs inside the publication/withdrawal transaction: version and impact set commit or fail together."""
    from app.models.department import ProtocolVersion
    from app.services import review_dependencies, scopes
    scope_key = review_dependencies.protocol_scope(record.family_id)
    scopes.bump(ctx, scope_key, {"event": event_kind, "protocol_version_id": str(record.id), "version_no": record.version_no})
    verb = "published" if event_kind == "protocol_published" else "withdrawn"
    event = _event(ctx, event_kind, f"{event_kind}:{record.id}", "protocol_version", record.id,
                   f"Protocol “{record.title}” version {record.version_no} was {verb}.", {"version_no": record.version_no})
    family = {v.id for v in ctx.all(ProtocolVersion, ProtocolVersion.family_id == record.family_id)}
    created = 0
    for plan in _live_plans(ctx):
        affected = plan.protocol_version_id == record.id if event_kind == "protocol_withdrawn" else (
            plan.protocol_version_id in family and plan.protocol_version_id != record.id)
        if affected:
            created += _open(ctx, event, plan, scope_key, needs_classification=False)[1]
    return {"change_event_id": str(event.id), "impacts_created": created}


def nominate_for_material_change(ctx: Ctx, patient_id: UUID, scope_key: str, change: dict) -> None:
    """Patient material changed. Only plans whose signed packet watched this scope are nominated."""
    wildcard = scope_key.rsplit("/", 1)[0] + "/*" if "/reports/" in scope_key else None
    document_id = change.get("document_id")
    superseded = set(change.get("supersedes") or [])
    for plan in _live_plans(ctx, patient_id=patient_id):
        approvals = ctx.all(PlanApproval, PlanApproval.plan_version_id == plan.id)
        watched = set(approvals[-1].watch_set) if approvals else set()
        if not ({scope_key, wildcard} & watched):
            continue
        pinned = {item["id"] for item in approvals[-1].read_set if item["kind"] == "observation_version"}
        corrected = bool(pinned & superseded)
        if document_id:
            event = _event(ctx, "source_change", f"source:{document_id}", "source_document", UUID(document_id),
                           f"New or changed source material: “{change.get('title') or change.get('analyte') or 'document'}”.", change)
        else:
            key = change.get("assessment_id") or change.get("discussion_id") or str(ctx.seq)
            event = _event(ctx, "patient_record_change", f"{change.get('event')}:{key}", "patient", patient_id,
                           f"Patient record changed: {change.get('event')}.", change)
        impact, new = _open(ctx, event, plan, scope_key if scope_key in watched else wildcard, needs_classification=not corrected)
        if not new and corrected:
            impact.history = [*impact.history, {"event": "pinned_fact_corrected", "sequence": ctx.seq, "analyte": change.get("analyte")}]


def nominate_for_exception_expiry(ctx: Ctx, request) -> dict:
    from app.services import scopes
    event = _event(ctx, "exception_expired", f"exception_expired:{request.id}", "exception_request", request.id,
                   f"The {request.exception_type} exception for {request.requirement_id} expired.", {"requirement_id": request.requirement_id})
    created = 0
    for plan in _live_plans(ctx, patient_id=request.patient_id):
        if str(request.id) in plan.exception_ids:
            created += _open(ctx, event, plan, scopes.patient_scope(request.patient_id, "exceptions"), needs_classification=False)[1]
    return {"change_event_id": str(event.id), "impacts_created": created}


def nominate_for_obligation_change(ctx: Ctx, obligation, change: dict) -> dict:
    from app.services import scopes
    plan = ctx.get(PatientPlanVersion, obligation.plan_version_id)
    scope_key = scopes.patient_scope(obligation.patient_id, "obligations")
    scopes.bump(ctx, scope_key, change)
    event = _event(ctx, "obligation_change", f"obligation_change:{obligation.id}:{ctx.seq}", "follow_up_obligation", obligation.id,
                   f"A change to the authored clinical obligation “{obligation.purpose}” was requested.", change)
    live = [p for p in _live_plans(ctx, patient_id=obligation.patient_id) if p.family_id == plan.family_id]
    impact, _ = _open(ctx, event, live[0] if live else plan, scope_key, needs_classification=False)
    return {"impact_id": str(impact.id)}


def classify(ctx: Ctx, impact_id: UUID, body) -> dict:
    """Classify unclassified incoming material: not relevant closes it; relevant keeps it open for disposition."""
    impact = ctx.get(ImpactReview, impact_id)
    ctx.expect(impact, body.expected_revision)
    if impact.state == "closed" or not impact.needs_classification:
        raise blocked("already_classified", "This impact item is already classified.", target=("impact_review", impact.id))
    if len(body.rationale.strip()) < 8:
        raise blocked("reason_required", "Record the rationale for this classification.", target=("impact_review", impact.id))
    impact.needs_classification = False
    entry = {"event": "classified", "relevant": body.relevant, "by": ctx.account.display_name, "sequence": ctx.seq, "rationale": body.rationale.strip()}
    if not body.relevant:
        impact.state, impact.disposition, impact.rationale = "closed", "unaffected", body.rationale.strip()
    impact.history = [*impact.history, entry]
    ctx.touch(impact)
    ctx.audit("impact.classify", impact, reason=body.rationale.strip(), detail={"relevant": body.relevant})
    return target(impact, state=impact.state)


def resolve(ctx: Ctx, impact_id: UUID, body) -> dict:
    impact = ctx.get(ImpactReview, impact_id)
    ctx.expect(impact, body.expected_revision)
    if impact.state == "closed":
        raise blocked("impact_closed", "This impact review is already closed.", target=("impact_review", impact.id))
    if impact.needs_classification:
        raise blocked("classification_required", "Classify this incoming material before recording a disposition.", target=("impact_review", impact.id))
    rationale = (body.rationale or "").strip()
    if len(rationale) < 8:
        raise blocked("reason_required", "Every disposition needs a rationale.", target=("impact_review", impact.id))
    event = ctx.get(ChangeEvent, impact.change_event_id)
    plan = ctx.get(PatientPlanVersion, impact.plan_version_id)
    linked = None
    if body.disposition == "adopted":
        linked = ctx.find(PatientPlanVersion, body.linked_plan_version_id)
        ok = (linked is not None and linked.patient_id == impact.patient_id and linked.family_id == plan.family_id
              and linked.status == "approved" and linked.version_no > plan.version_no and linked.recorded_seq >= 0)
        approvals = ctx.all(PlanApproval, PlanApproval.plan_version_id == linked.id) if ok else []
        if ok and event.event_kind == "protocol_published":
            ok = linked.protocol_version_id == event.source_id
        if ok and approvals:
            ok = approvals[-1].recorded_seq > impact.recorded_seq  # the successor was approved after the change
        if not ok or not approvals:
            raise blocked("adoption_requires_approved_plan", "Adoption closes only with a linked, newly approved successor plan for this patient.",
                          target=("impact_review", impact.id),
                          next_action="Assess applicability against the new version, approve a successor plan, then link it here.")
    elif body.disposition == "retained":
        if len((body.review_trigger or "").strip()) < 5:
            raise blocked("review_trigger_required", "Retaining the current plan needs a review trigger.", target=("impact_review", impact.id))
    entry = {"event": body.disposition, "by": ctx.account.display_name, "sequence": ctx.seq, "rationale": rationale}
    impact.rationale, impact.history = rationale, [*impact.history, entry]
    if body.disposition == "more_information":
        impact.state = "more_information"  # stays open and owned
    else:
        impact.state, impact.disposition = "closed", body.disposition
        impact.review_trigger = (body.review_trigger or "").strip() or None
        impact.linked_plan_version_id = linked.id if linked else None
    ctx.touch(impact)
    ctx.audit("impact.resolve", impact, reason=rationale, detail={"disposition": body.disposition})
    return target(impact, state=impact.state, disposition=impact.disposition)


def view(ctx: Ctx, impact: ImpactReview) -> dict:
    """Everything needed to reconstruct the change, the patient basis and the authorised disposition."""
    event = ctx.get(ChangeEvent, impact.change_event_id)
    plan = ctx.get(PatientPlanVersion, impact.plan_version_id)
    data = {c.name: getattr(impact, c.name) for c in impact.__table__.columns}
    return {**data, "change": event, "plan_version_no": plan.version_no, "plan_protocol_version_id": plan.protocol_version_id,
            "next_action": None if impact.state == "closed" else ("Classify relevance" if impact.needs_classification else
                                                                  "Record more information or a disposition" if impact.state == "more_information" else "Record a disposition")}
