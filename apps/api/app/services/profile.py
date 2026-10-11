"""Longitudinal six-dimensional profile: a projection over source records at a knowledge cutoff.

The dimensions organise attributed records as review prompts. They are not eligibility rules and
nothing here selects between differing values or assumes missing items are normal.
"""
from uuid import UUID

from app.core.security import digest
from app.models import sources as m
from app.services import sources as source_service
from app.services.command_service import Ctx

DIMENSIONS = [
    ("biology", "Disease biology", "Reported diagnosis and disease characterisation, per specimen and assay."),
    ("extent", "Disease extent", "Disease-specific extent assessment and supporting reports."),
    ("fitness", "Patient fitness", "Function, organ assessment and relevant comorbidities."),
    ("history", "Treatment history", "Prior therapies, responses and treatment-related problems."),
    ("current", "Current condition", "Current observations, symptoms and investigations."),
    ("priorities", "Patient priorities and access", "Documented preferences, practical constraints and support."),
]
_NON_RESULT = {"pending": "result pending", "untested": "not tested", "indeterminate": "indeterminate result",
               "insufficient_sample": "insufficient sample", "unreported": "not reported by the source", "unavailable": "unavailable"}


def _day(obs) -> int:
    return (obs.effective_time or {}).get("value", 10**6)


def project(ctx: Ctx, patient_id: UUID, as_of_seq: int | None = None) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    now = ctx.workspace.sequence
    cutoff = min(as_of_seq, now) if as_of_seq is not None else now
    known = lambda r: r.recorded_seq <= cutoff  # noqa: E731
    observations = [o for o in ctx.all(m.ObservationVersion, m.ObservationVersion.patient_id == patient.id)
                    if known(o) and (o.superseded_seq is None or o.superseded_seq > cutoff)]
    observations.sort(key=lambda o: (_day(o), o.recorded_seq))
    assessments = [a for a in ctx.all(m.ClinicalAssessment, m.ClinicalAssessment.patient_id == patient.id) if known(a)]
    discussions = [d for d in ctx.all(m.PatientDiscussion, m.PatientDiscussion.patient_id == patient.id) if known(d)]
    assessment = assessments[-1] if assessments else None
    discussion = discussions[-1] if discussions else None
    unresolved: list[dict] = []

    documents = [d for d in ctx.all(m.SourceDocument) if known(d)]
    for doc in documents:
        intended = (doc.claimed_identity or {}).get("intended_patient_id")
        reviewed_at = (doc.association_review or {}).get("sequence")
        still_open = doc.association_status in ("pending", "quarantined") or (reviewed_at is not None and reviewed_at > cutoff)
        if still_open and (doc.patient_id == patient.id or intended == str(patient.id)):
            label = "is quarantined: the identity it names does not match" if doc.association_status == "quarantined" else "awaits identity and association review"
            unresolved.append({"kind": "association", "text": f"“{doc.title}” {label}.", "target_kind": "source_document", "target_id": doc.id,
                               "next_action": "Review document identity"})
    reviews = [r for r in ctx.all(m.SourceReview) if known(r)]
    settled = {r.candidate_id for r in reviews if r.disposition in ("verified", "corrected", "rejected")}
    for cand in ctx.all(m.ExtractionCandidate, m.ExtractionCandidate.patient_id == patient.id):
        if known(cand) and cand.id not in settled:
            unresolved.append({"kind": "source_review", "text": f"{cand.assertion.get('analyte')}: candidate awaits source verification.",
                               "target_kind": "source_document", "target_id": cand.document_id, "next_action": "Verify against the original"})
    for report in ctx.all(m.ReportVersion, m.ReportVersion.patient_id == patient.id):
        if known(report) and report.relation_kind == "unresolved":
            unresolved.append({"kind": "report_relation", "text": "A report's relationship to earlier versions is unresolved; nothing was superseded.",
                               "target_kind": "report_version", "target_id": report.id, "next_action": "Classify the report relationship"})
    for item in ctx.all(m.ExpectedInput, m.ExpectedInput.patient_id == patient.id):
        state = item.state
        if known(item):
            past = [h for h in item.history if h.get("sequence", 0) <= cutoff]
            state = past[-1]["state"] if past else "pending"
            if state != "received" and state != "cancelled":
                unresolved.append({"kind": "expected_input", "text": f"Expected input “{item.artifact}” is {state}.", "target_kind": "expected_input",
                                   "target_id": item.id, "owner": item.owner_name, "next_action": item.next_action})

    dimensions = []
    for dim_id, title, description in DIMENSIONS:
        facts = [o for o in observations if o.dimension == dim_id]
        notes: list[str] = []
        for o in facts:
            if o.result_state in _NON_RESULT:
                notes.append(f"{o.analyte}: {_NON_RESULT[o.result_state]} — “{o.value_text or o.exact_wording}”.")
        by_key: dict[tuple, set] = {}
        for o in facts:
            by_key.setdefault((o.analyte, o.specimen_id, _day(o)), set()).add((o.value_text or "").lower())
        for (analyte, _, _), values in by_key.items():
            if len(values) > 1:
                notes.append(f"{analyte}: differing source values for the same specimen and time need review; no value was selected automatically.")
        if not facts and not (assessment and assessment.dimension_notes.get(dim_id)) and not (dim_id == "priorities" and discussion):
            notes.append("No source-verified record in this dimension. Missing items are not assumed normal.")
        dimensions.append({"id": dim_id, "title": title, "description": description,
                           "observations": [source_service.observation_view(ctx, o) for o in facts],
                           "clinician_note": assessment.dimension_notes.get(dim_id) if assessment else None, "unresolved": notes})

    trends = []
    groups: dict[str, list] = {}
    for o in observations:
        groups.setdefault(o.analyte, []).append(o)
    for analyte, points in groups.items():
        if len({(p.specimen_id, _day(p), p.report_version_id) for p in points}) > 1:
            trends.append({"analyte": analyte, "points": [
                {"observation_id": p.id, "value_text": p.value_text, "units": p.units, "result_state": p.result_state,
                 "effective_time": p.effective_time, "specimen_label": source_service.observation_view(ctx, p)["specimen_label"],
                 "recorded_seq": p.recorded_seq} for p in points]})
    return {"patient_id": patient.id, "knowledge_cutoff_seq": cutoff, "historical": cutoff < now, "dimensions": dimensions,
            "trends": trends, "unresolved": unresolved, "assessment": assessment, "discussion": discussion,
            "_observation_ids": [str(o.id) for o in observations]}


def capture(ctx: Ctx, patient_id: UUID) -> m.ProfileSnapshot:
    """Freeze the profile at the current knowledge cutoff for a review packet."""
    view = project(ctx, patient_id)
    dims = {d["id"]: {"observation_ids": [str(o["id"]) for o in d["observations"]], "clinician_note": d["clinician_note"],
                      "unresolved": d["unresolved"]} for d in view["dimensions"]}
    unresolved = [{**u, "target_id": str(u["target_id"]) if u.get("target_id") else None} for u in view["unresolved"]]
    content = {"observations": view["_observation_ids"], "assessment": str(view["assessment"].id) if view["assessment"] else None,
               "discussion": str(view["discussion"].id) if view["discussion"] else None, "dimensions": dims, "unresolved": unresolved}
    snapshot = ctx.new(m.ProfileSnapshot, patient_id=patient_id, episode_id=source_service.episode_of(ctx, patient_id).id,
                       knowledge_cutoff_seq=ctx.seq, observation_ids=view["_observation_ids"],
                       assessment_id=view["assessment"].id if view["assessment"] else None,
                       discussion_id=view["discussion"].id if view["discussion"] else None, unresolved=unresolved,
                       dimensions=dims, digest=digest(content))
    ctx.db.flush()
    return snapshot
