"""U3 source services: registration, original preservation, association, candidate review.

Source review checks wording against the original region. It never interprets findings.
"""
import base64
import binascii
import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import DomainError, blocked, not_found
from app.core.security import sha256_bytes
from app.models import sources as m
from app.models.identity import Account
from app.services import extraction, scopes
from app.services.command_service import Ctx, target


@dataclass
class ParsedUpload:
    data: bytes
    sha256: str
    media_type: str
    pages: list[dict] = field(default_factory=list)
    header: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict] = field(default_factory=list)
    limits: dict[str, Any] = field(default_factory=dict)


def prepare_upload(content_base64: str, media_type: str, doc_kind: str) -> ParsedUpload:
    """Decode, bound, sniff, hash and parse BEFORE the short write transaction (KTD3)."""
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DomainError(422, "invalid_upload", "The uploaded content is not valid base64.") from exc
    if not data or len(data) > get_settings().max_upload_bytes:
        raise DomainError(413, "upload_too_large", "The file is empty or exceeds the configured upload size limit.",
                          details={"max_bytes": get_settings().max_upload_bytes})
    if extraction.sniff_media_type(data, media_type) is None:
        raise DomainError(415, "unsupported_media", "Only PDF, PNG and JPEG originals are accepted; active HTML/SVG content is rejected.",
                          next_action="Supply the original report as a PDF or image file.")
    parsed = ParsedUpload(data=data, sha256=sha256_bytes(data), media_type=media_type)
    if media_type == "application/pdf":
        try:
            parsed.pages = extraction.parse_pdf(data)
        except Exception:  # malformed PDF: keep the original, no text layer
            parsed.pages = []
        parsed.header = extraction.read_header(parsed.pages)
        has_text = any(p["lines"] for p in parsed.pages)
        parsed.candidates = extraction.extract_candidates(doc_kind, parsed.pages) if has_text else []
        supported = doc_kind in extraction.VOCAB or doc_kind in extraction.TABLE_TYPES
        parsed.limits = {"text_layer": has_text, "layout_supported": supported,
                         "note": None if has_text and supported else "No supported text layout: enter source-linked findings manually."}
    else:
        parsed.limits = {"text_layer": False, "layout_supported": False,
                         "note": "Image-only original: no machine findings were extracted. Use manual source-linked entry."}
    return parsed


def _account(ctx: Ctx, username: str) -> Account:
    account = ctx.db.scalar(select(Account).where(Account.username == username))
    if account is None:
        raise blocked("unknown_owner", f"No development account named '{username}' exists.", target=("account", None))
    return account


def identifiers_of(ctx: Ctx, owner_kind: str, owner_id: UUID) -> list[m.ExternalIdentifier]:
    return ctx.all(m.ExternalIdentifier, m.ExternalIdentifier.owner_kind == owner_kind, m.ExternalIdentifier.owner_id == owner_id)


def episode_of(ctx: Ctx, patient_id: UUID) -> m.Episode:
    episodes = ctx.all(m.Episode, m.Episode.patient_id == patient_id)
    if not episodes:
        raise not_found("episode", patient_id)
    return episodes[-1]


def register_patient(ctx: Ctx, body) -> dict:
    for ident in body.identifiers:
        clash = ctx.all(m.ExternalIdentifier, m.ExternalIdentifier.owner_kind == "patient",
                        m.ExternalIdentifier.system == ident.system, m.ExternalIdentifier.value == ident.value)
        if clash:
            raise DomainError(409, "identifier_in_use", "This namespaced identifier already belongs to a patient.",
                              target=("patient", clash[0].owner_id), next_action="Open the existing patient or correct the identifier.")
    patient = ctx.new(m.Patient, display_name=body.display_name.strip(), summary=body.summary)
    ctx.db.flush()
    for ident in body.identifiers:
        ctx.new(m.ExternalIdentifier, owner_kind="patient", owner_id=patient.id, system=ident.system, value=ident.value)
    episode = ctx.new(m.Episode, patient_id=patient.id, title=body.episode_title, service=body.service,
                      responsible_team=body.responsible_team)
    ctx.audit("patient.register", patient)
    return target(patient, episode_id=str(episode.id))


_RELATIONS = [("withdraw", "withdrawal"), ("replac", "replacement"), ("correct", "correction"), ("addend", "additive_addendum")]


def _relation(body_relation: str | None, header: dict) -> str:
    if body_relation:
        return body_relation
    text = (header.get("relation") or "").lower()
    return next((kind for needle, kind in _RELATIONS if needle in text), "original")


def _ensure_specimens(ctx: Ctx, report: m.ReportVersion, family: m.ReportFamily, patient_id: UUID, header: dict) -> None:
    ids = []
    for spec in header.get("specimens", []):
        alias = f"{family.accession}/{spec['label']}"
        known = ctx.all(m.ExternalIdentifier, m.ExternalIdentifier.owner_kind == "specimen",
                        m.ExternalIdentifier.system == family.issuer, m.ExternalIdentifier.value == alias)
        if known:
            ids.append(str(known[0].owner_id))
            continue
        specimen = ctx.new(m.Specimen, patient_id=patient_id, label=spec["label"], material=spec.get("description"),
                           collection_time=spec.get("collection_time"), issuer=family.issuer)
        ctx.db.flush()
        ctx.new(m.ExternalIdentifier, owner_kind="specimen", owner_id=specimen.id, system=family.issuer, value=alias)
        ids.append(str(specimen.id))
    if not ids and report.predecessor_id:
        ids = list(ctx.get(m.ReportVersion, report.predecessor_id).specimen_ids)
    report.specimen_ids = ids


def receive_document(ctx: Ctx, body, parsed: ParsedUpload) -> dict:
    """Commit the original bytes and their metadata together; unresolved identity stays quarantined."""
    patient = ctx.get(m.Patient, body.patient_id)
    existing = ctx.db.scalar(select(m.SourceBlob).where(m.SourceBlob.container_id == ctx.container_id, m.SourceBlob.sha256 == parsed.sha256))
    if existing is not None:
        docs = ctx.all(m.SourceDocument, m.SourceDocument.blob_id == existing.id)
        raise DomainError(409, "duplicate_source", "These exact bytes are already stored; the existing original is kept.",
                          target=("source_document", docs[0].id if docs else None),
                          next_action="Open the existing document instead of uploading it again.",
                          details={"sha256": parsed.sha256})
    header = parsed.header
    claimed = header.get("patient_identifier")
    own_values = {i.value for i in identifiers_of(ctx, "patient", patient.id)}
    claimed_value = next((v for v in own_values if claimed and v in claimed), None)
    names_other = bool(claimed) and claimed_value is None
    blob = ctx.new(m.SourceBlob, sha256=parsed.sha256, length=len(parsed.data), media_type=parsed.media_type, data=parsed.data)
    ctx.db.flush()
    episode = episode_of(ctx, patient.id)
    issuer = (body.issuer or header.get("issuer") or "").strip() or None
    accession = (body.accession or header.get("accession") or "").strip() or None
    doc = ctx.new(
        m.SourceDocument, family_id=uuid.uuid4(), blob_id=blob.id, patient_id=None if names_other else patient.id,
        episode_id=None if names_other else episode.id, doc_kind=body.doc_kind, title=body.title or header.get("report_type") or body.filename,
        filename=body.filename, issuer=issuer, author=body.author or header.get("author"), external_id=accession,
        claimed_identity={"value": claimed, "name": header.get("patient_name"), "matches_intended_patient": bool(claimed_value),
                          "intended_patient_id": str(patient.id)},
        association_status="quarantined" if names_other else "pending", page_count=max(1, len(parsed.pages)), pages=parsed.pages,
        extraction_limits=parsed.limits, received_time=body.received_time.model_dump() if body.received_time else None)
    ctx.db.flush()
    report = None
    if issuer and accession:
        family = ctx.db.scalar(select(m.ReportFamily).where(m.ReportFamily.container_id == ctx.container_id,
                                                           m.ReportFamily.issuer == issuer, m.ReportFamily.accession == accession))
        relation = _relation(body.relation, header)
        versions = ctx.all(m.ReportVersion, m.ReportVersion.family_id == family.id, order=m.ReportVersion.version_no) if family else []
        if family is None:
            family = ctx.new(m.ReportFamily, patient_id=doc.patient_id, issuer=issuer, accession=accession, report_type=body.doc_kind)
            ctx.db.flush()
            if relation != "original":
                relation = "unresolved"  # an amendment whose predecessor we do not hold stays unresolved
        elif relation == "original" or (family.patient_id and doc.patient_id and family.patient_id != doc.patient_id):
            relation = "unresolved"  # same issuer+accession re-sent without a stated relation: never guess supersession
        affects = [a.strip() for a in re.split(r"[;,]", header.get("affects", "")) if a.strip()]
        report = ctx.new(
            m.ReportVersion, family_id=family.id, patient_id=doc.patient_id, version_no=len(versions) + 1,
            issued_status=(header.get("issued_status") or "final").lower(), relation_kind=relation,
            predecessor_id=versions[-1].id if versions and relation != "unresolved" else None, affected_scope=affects,
            document_ids=[str(doc.id)], effective_time=extraction.rel_day(header.get("collected")),
            issued_time=extraction.rel_day(header.get("issued")),
            amended_time=extraction.rel_day(header.get("issued")) if relation != "original" else None,
            scope_note=header.get("relation"))
        ctx.db.flush()
        if doc.patient_id:
            _ensure_specimens(ctx, report, family, doc.patient_id, header)
        if header.get("method") or header.get("panel") or header.get("limitations"):
            ctx.new(m.AssayContext, report_version_id=report.id, name=header.get("report_type") or body.doc_kind,
                    panel=header.get("panel"), method=header.get("method"), limitations=header.get("limitations"))
    for cand in parsed.candidates:
        ctx.new(m.ExtractionCandidate, document_id=doc.id, report_version_id=report.id if report else None,
                patient_id=doc.patient_id, extractor=extraction.EXTRACTOR, extractor_version=extraction.EXTRACTOR_VERSION,
                assertion=cand["assertion"], source_ref={**cand["source_ref"], "document_id": str(doc.id)})
    ctx.audit("source.receive", doc, detail={"sha256": parsed.sha256, "association_status": doc.association_status,
                                             "candidates": len(parsed.candidates)})
    return target(doc, association_status=doc.association_status, report_version_id=str(report.id) if report else None,
                  candidate_count=len(parsed.candidates), sha256=parsed.sha256)


def _reports_of(ctx: Ctx, doc: m.SourceDocument) -> list[m.ReportVersion]:
    return [r for r in ctx.all(m.ReportVersion) if str(doc.id) in r.document_ids]


def associate_document(ctx: Ctx, document_id: UUID, body) -> dict:
    doc = ctx.get(m.SourceDocument, document_id)
    ctx.expect(doc, body.expected_revision)
    patient = ctx.get(m.Patient, body.patient_id)
    if doc.association_status == "associated":
        raise blocked("already_associated", "This document is already associated with a patient.", target=("source_document", doc.id))
    if not body.checked or len(body.note.strip()) < 8:
        raise blocked("identity_review_required", "Check patient, specimen and report context and record how identity was verified.",
                      target=("source_document", doc.id), next_action="Tick the identity check and add a short verification note.")
    claimed = (doc.claimed_identity or {}).get("value")
    own = {i.value for i in identifiers_of(ctx, "patient", patient.id)}
    if claimed and not any(v in claimed for v in own):
        raise blocked("invalid_association", "The document names a different patient identifier than the selected patient.",
                      target=("source_document", doc.id), next_action="Associate it with the patient it names, or reject it.",
                      details={"claimed_identifier": claimed})
    doc.patient_id, doc.episode_id, doc.association_status = patient.id, episode_of(ctx, patient.id).id, "associated"
    doc.association_review = {"by": ctx.account.display_name, "by_id": str(ctx.account.id), "note": body.note.strip(), "sequence": ctx.seq}
    ctx.touch(doc)
    for cand in ctx.all(m.ExtractionCandidate, m.ExtractionCandidate.document_id == doc.id):
        cand.patient_id = patient.id
    change = {"event": "source.associated", "document_id": str(doc.id), "title": doc.title, "doc_kind": doc.doc_kind}
    for report in _reports_of(ctx, doc):
        family = ctx.get(m.ReportFamily, report.family_id)
        if family.patient_id and family.patient_id != patient.id:
            raise blocked("invalid_association", "This accession already belongs to a different patient for the same issuer.",
                          target=("report_family", family.id), next_action="Reject the document or resolve the identity conflict.")
        family.patient_id = report.patient_id = patient.id
        if not report.specimen_ids:
            _ensure_specimens(ctx, report, family, patient.id, extraction.read_header(doc.pages))
        change.update(report_version_id=str(report.id), relation_kind=report.relation_kind)
        if report.relation_kind == "withdrawal" and report.predecessor_id:
            for obs in ctx.all(m.ObservationVersion, m.ObservationVersion.status == "current"):
                if ctx.get(m.ReportVersion, obs.report_version_id).family_id == report.family_id:
                    obs.status, obs.superseded_seq, obs.superseded_reason = "withdrawn", ctx.seq, "Report withdrawn by issuer"
    ctx.audit("source.associate", doc, reason=body.note.strip())
    # New clinical material for this patient: bump its watch scope and nominate scoped impact review.
    scopes.material_changed(ctx, patient.id, f"reports/{doc.doc_kind}", change)
    return target(doc)


def reject_document(ctx: Ctx, document_id: UUID, body) -> dict:
    doc = ctx.get(m.SourceDocument, document_id)
    ctx.expect(doc, body.expected_revision)
    if doc.association_status == "associated":
        raise blocked("already_associated", "An associated document cannot be rejected; record a correction instead.", target=("source_document", doc.id))
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record why this document is rejected.", target=("source_document", doc.id))
    doc.association_status = "rejected"
    doc.association_review = {"by": ctx.account.display_name, "note": body.reason.strip(), "sequence": ctx.seq, "rejected": True}
    ctx.touch(doc)
    ctx.audit("source.reject", doc, reason=body.reason.strip())
    return target(doc)


def _require_reviewable(ctx: Ctx, doc: m.SourceDocument) -> None:
    if doc.association_status != "associated":
        raise blocked("identity_review_required", "Confirm document identity and association before reviewing findings.",
                      target=("source_document", doc.id), next_action="Complete the association review for this document.")
    blob = ctx.get(m.SourceBlob, doc.blob_id)
    if blob.data is None or blob.availability != "available":
        raise blocked("original_unavailable", "The original file is not available, so findings cannot be verified against it.",
                      target=("source_document", doc.id), next_action="Supply the exact original file (matching hash) first.")


def add_manual_candidate(ctx: Ctx, document_id: UUID, body) -> dict:
    doc = ctx.get(m.SourceDocument, document_id)
    _require_reviewable(ctx, doc)
    x0, y0, x1, y1 = body.region
    if body.page > doc.page_count or x1 <= x0 or y1 <= y0 or min(body.region) < 0:
        raise blocked("invalid_region", "Select a region on an existing page of the original.", target=("source_document", doc.id))
    reports = _reports_of(ctx, doc)
    page = next((p for p in doc.pages if p["number"] == body.page), None)
    cand = ctx.new(
        m.ExtractionCandidate, document_id=doc.id, report_version_id=reports[0].id if reports else None, patient_id=doc.patient_id,
        extractor="manual-entry", extractor_version="1", manual=True,
        assertion={"analyte": body.analyte.strip(), "dimension": body.dimension, "exact_wording": body.exact_wording.strip(),
                   "value_text": body.value_text, "value_number": body.value_number, "units": body.units, "reference_range": None,
                   "result_state": body.result_state, "specimen_label": body.specimen_label,
                   "normalization": {"rule": "manual-transcription", "by": ctx.account.display_name}},
        source_ref={"document_id": str(doc.id), "page": body.page, "region": body.region,
                    "page_size": [page["width"], page["height"]] if page else None, "units": "page-points" if page else "fraction"})
    ctx.audit("candidate.manual", cand)
    return target(cand)


def _specimen_for(ctx: Ctx, report: m.ReportVersion | None, label: str | None) -> m.Specimen | None:
    if report is None:
        return None
    specimens = [ctx.get(m.Specimen, UUID(s)) for s in report.specimen_ids]
    match = [s for s in specimens if label and s.label == label]
    return match[0] if match else (specimens[0] if len(specimens) == 1 else None)


def review_candidate(ctx: Ctx, candidate_id: UUID, body) -> dict:
    cand = ctx.get(m.ExtractionCandidate, candidate_id)
    ctx.expect(cand, body.expected_revision)
    doc = ctx.get(m.SourceDocument, cand.document_id)
    _require_reviewable(ctx, doc)
    if not cand.source_ref.get("region"):
        raise blocked("source_not_cited", "This candidate has no cited source region.", target=("extraction_candidate", cand.id))
    if not body.source_inspected:
        raise blocked("source_inspection_required", "Open the original region and confirm the wording before recording a review.",
                      target=("extraction_candidate", cand.id), next_action="Inspect the highlighted source region, then confirm.")
    reason = (body.reason or "").strip()
    if body.disposition in ("corrected", "rejected", "unresolved") and len(reason) < 8:
        raise blocked("reason_required", "Record why this finding was corrected, rejected or left unresolved.", target=("extraction_candidate", cand.id))
    assertion = dict(cand.assertion)
    corrected = body.corrected.model_dump(exclude_none=True) if body.corrected else None
    if body.disposition == "corrected":
        if not corrected:
            raise blocked("correction_required", "Provide the corrected transcription.", target=("extraction_candidate", cand.id))
        assertion.update(corrected)
        assertion["normalization"] = {"rule": "local-transcription-correction", "by": ctx.account.display_name,
                                      "original_value_text": cand.assertion.get("value_text"),
                                      "note": "Local correction of the app transcription; the laboratory report is unchanged."}
    cand.status = body.disposition
    ctx.touch(cand)
    review = ctx.new(m.SourceReview, candidate_id=cand.id, candidate_revision=cand.revision, disposition=body.disposition,
                     reason=reason or None, corrected=corrected)
    previous = [o for o in ctx.all(m.ObservationVersion, m.ObservationVersion.candidate_id == cand.id) if o.status == "current"]
    observation = None
    if body.disposition in ("verified", "corrected"):
        report = ctx.find(m.ReportVersion, cand.report_version_id)
        if report is None:
            raise blocked("report_context_required", "This document has no report identity (issuer and accession), so findings cannot be recorded.",
                          target=("source_document", doc.id))
        specimen = _specimen_for(ctx, report, assertion.get("specimen_label"))
        superseded = list(previous)
        if not superseded and report.relation_kind in ("correction", "replacement") and report.predecessor_id:
            # An issuer correction supersedes only the matching earlier assertion; others stay current.
            family_versions = {v.id for v in ctx.all(m.ReportVersion, m.ReportVersion.family_id == report.family_id)} - {report.id}
            for old in ctx.all(m.ObservationVersion, m.ObservationVersion.status == "current", m.ObservationVersion.analyte == assertion["analyte"]):
                if old.report_version_id in family_versions and (old.specimen_id == (specimen.id if specimen else None)):
                    superseded.append(old)
        base = superseded[0] if superseded else None
        for old in superseded:
            old.status, old.superseded_seq = "superseded", ctx.seq
            old.superseded_reason = ("Re-reviewed locally" if old in previous else f"Corrected by issuer report version {report.version_no}")
        observation = ctx.new(
            m.ObservationVersion, key=base.key if base else uuid.uuid4(), version_no=(base.version_no + 1) if base else 1,
            patient_id=doc.patient_id, report_version_id=report.id, specimen_id=specimen.id if specimen else None,
            document_id=doc.id, candidate_id=cand.id, analyte=assertion["analyte"], dimension=assertion["dimension"],
            exact_wording=assertion["exact_wording"], value_text=assertion.get("value_text"), value_number=assertion.get("value_number"),
            units=assertion.get("units"), reference_range=assertion.get("reference_range"), result_state=assertion["result_state"],
            effective_time=(specimen.collection_time if specimen and specimen.collection_time else report.effective_time),
            source_ref=cand.source_ref, normalization=assertion.get("normalization") or {}, supersedes_id=base.id if base else None)
        ctx.db.flush()
        review.observation_id = observation.id
    else:
        for old in previous:
            old.status, old.superseded_seq, old.superseded_reason = "withdrawn", ctx.seq, f"Source review changed to {body.disposition}"
    ctx.audit("candidate.review", cand, reason=reason or None, detail={"disposition": body.disposition})
    if observation is not None or previous:
        scopes.material_changed(ctx, doc.patient_id, f"reports/{doc.doc_kind}",
                                {"event": "observation.reviewed", "analyte": assertion["analyte"], "document_id": str(doc.id),
                                 "disposition": body.disposition, "observation_id": str(observation.id) if observation else None,
                                 "supersedes": [str(o.id) for o in previous] or ([str(observation.supersedes_id)] if observation is not None and observation.supersedes_id else [])})
    return target(cand, observation_id=str(observation.id) if observation else None, review_id=str(review.id))


def create_expected_input(ctx: Ctx, body) -> dict:
    patient = ctx.get(m.Patient, body.patient_id)
    owner = _account(ctx, body.owner_username)
    item = ctx.new(m.ExpectedInput, patient_id=patient.id, episode_id=episode_of(ctx, patient.id).id, artifact=body.artifact.strip(),
                   report_type=body.report_type, upstream_request=body.upstream_request, owner_id=owner.id, owner_name=owner.display_name,
                   next_action=body.next_action.strip(), history=[{"state": "pending", "by": ctx.account.display_name, "sequence": ctx.seq}])
    ctx.audit("expected_input.create", item)
    return target(item)


def update_expected_input(ctx: Ctx, item_id: UUID, body) -> dict:
    item = ctx.get(m.ExpectedInput, item_id)
    ctx.expect(item, body.expected_revision)
    if item.state == "received":
        raise blocked("already_fulfilled", "This expected input was fulfilled by a linked report.", target=("expected_input", item.id))
    if body.owner_username:
        owner = _account(ctx, body.owner_username)
        item.owner_id, item.owner_name = owner.id, owner.display_name
    if body.next_action:
        item.next_action = body.next_action.strip()
    if body.state:
        item.state = body.state
    item.history = [*item.history, {"state": item.state, "owner": item.owner_name, "by": ctx.account.display_name,
                                    "reason": body.reason, "sequence": ctx.seq}]
    ctx.touch(item)
    ctx.audit("expected_input.update", item, reason=body.reason)
    return target(item)


def link_expected_input(ctx: Ctx, item_id: UUID, body) -> dict:
    """Only an explicitly linked, associated report of the same patient and type fulfils an expected input."""
    item = ctx.get(m.ExpectedInput, item_id)
    ctx.expect(item, body.expected_revision)
    report = ctx.get(m.ReportVersion, body.report_version_id)
    family = ctx.get(m.ReportFamily, report.family_id)
    if report.patient_id != item.patient_id or family.report_type != item.report_type:
        raise blocked("invalid_association", "Only an associated report of the same patient and report type can fulfil this input.",
                      target=("expected_input", item.id), next_action="Link the matching report once it has been associated.")
    item.state, item.fulfilled_report_id = "received", report.id
    item.history = [*item.history, {"state": "received", "report_version_id": str(report.id), "by": ctx.account.display_name, "sequence": ctx.seq}]
    ctx.touch(item)
    ctx.audit("expected_input.link", item)
    return target(item)


def _next_version(ctx: Ctx, cls, patient_id: UUID):
    versions = ctx.all(cls, cls.patient_id == patient_id, order=cls.version_no)
    return versions[-1] if versions else None


def record_assessment(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    prior = _next_version(ctx, m.ClinicalAssessment, patient.id)
    for obs_id in body.evidence:
        if ctx.get(m.ObservationVersion, obs_id).patient_id != patient.id:
            raise blocked("invalid_association", "Evidence must belong to this patient.", target=("observation_version", obs_id))
    item = ctx.new(m.ClinicalAssessment, family_id=prior.family_id if prior else uuid.uuid4(), version_no=(prior.version_no + 1) if prior else 1,
                   patient_id=patient.id, episode_id=episode_of(ctx, patient.id).id, narrative=body.narrative.strip(),
                   dimension_notes={k: v for k, v in body.dimension_notes.items() if v.strip()}, evidence=[str(e) for e in body.evidence],
                   uncertainty=body.uncertainty, classification_edition=body.classification_edition, supersedes_id=prior.id if prior else None)
    ctx.audit("assessment.record", item)
    scopes.material_changed(ctx, patient.id, "assessment", {"event": "assessment.recorded", "assessment_id": str(item.id), "version_no": item.version_no})
    return target(item)


def record_discussion(ctx: Ctx, patient_id: UUID, body) -> dict:
    patient = ctx.get(m.Patient, patient_id)
    prior = _next_version(ctx, m.PatientDiscussion, patient.id)
    item = ctx.new(m.PatientDiscussion, family_id=prior.family_id if prior else uuid.uuid4(), version_no=(prior.version_no + 1) if prior else 1,
                   patient_id=patient.id, episode_id=episode_of(ctx, patient.id).id, participants=body.participants,
                   attributed_to=body.attributed_to, goals=body.goals.strip(), preferences=body.preferences,
                   consent_reference=body.consent_reference, supersedes_id=prior.id if prior else None)
    ctx.audit("discussion.record", item)
    scopes.material_changed(ctx, patient.id, "discussion", {"event": "discussion.recorded", "discussion_id": str(item.id), "version_no": item.version_no})
    return target(item)


def document_view(ctx: Ctx, doc: m.SourceDocument) -> dict:
    blob = ctx.get(m.SourceBlob, doc.blob_id)
    data = {c.name: getattr(doc, c.name) for c in doc.__table__.columns}
    return {**data, "original_available": blob.data is not None and blob.availability == "available", "sha256": blob.sha256,
            "media_type": blob.media_type, "length": blob.length}


def report_view(ctx: Ctx, report: m.ReportVersion) -> dict:
    family = ctx.get(m.ReportFamily, report.family_id)
    data = {c.name: getattr(report, c.name) for c in report.__table__.columns}
    return {**data, "issuer": family.issuer, "accession": family.accession, "report_type": family.report_type}


def observation_view(ctx: Ctx, obs: m.ObservationVersion) -> dict:
    specimen = ctx.find(m.Specimen, obs.specimen_id)
    data = {c.name: getattr(obs, c.name) for c in obs.__table__.columns}
    return {**data, "specimen_label": specimen.label if specimen else None}
