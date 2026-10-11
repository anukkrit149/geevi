"""U3 source records: identities, originals, reports, specimens, observations and reviews.

Patient, episode, encounter, specimen and report identities stay distinct (R1). Observations are
versioned assertions tied to an exact source region (R2/R3); they are never overwritten.
"""
from sqlalchemy import BigInteger, LargeBinary, UniqueConstraint
from sqlalchemy.orm import mapped_column

from app.db.base import Record, flag, jdict, jlist, num, ref, req, txt, uid

RESULT_STATES = ("reported_value", "detected", "not_detected", "pending", "untested", "indeterminate",
                 "insufficient_sample", "unreported", "unavailable")
DIMENSIONS = ("biology", "extent", "fitness", "history", "current", "priorities")


class Patient(Record):
    __tablename__ = "patients"
    kind = "patient"
    display_name = req()
    data_label = req(default="fictional")
    summary = txt()


class ExternalIdentifier(Record):
    """Namespaced alias (issuer/system + value) for a patient, specimen or report."""

    __tablename__ = "external_identifiers"
    __table_args__ = (UniqueConstraint("container_id", "owner_kind", "system", "value"),)
    kind = "external_identifier"
    owner_kind = req()
    owner_id = uid(False)
    system = req()
    value = req()


class Episode(Record):
    __tablename__ = "episodes"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "episode"
    patient_id = uid(False)
    title = req()
    service = req()
    responsible_team = req()
    status = req(default="ongoing")  # ongoing|closed|transfer_pending|transferred
    disposition = jdict()
    time_anchor = req(default="Day 0 = referral received (fictional relative day)")


class Encounter(Record):
    __tablename__ = "encounters"
    __table_args__ = (ref("patients", "patient_id"), ref("episodes", "episode_id"))
    kind = "encounter"
    patient_id = uid(False)
    episode_id = uid(False)
    encounter_type = req()
    status = req(default="occurred")  # planned|occurred|cancelled
    planned_time = jdict(nullable=True)
    actual_time = jdict(nullable=True)
    summary = txt()


class SourceBlob(Record):
    """Immutable content-addressed original bytes. `data` is NULL only when an import lacked the original."""

    __tablename__ = "source_blobs"
    __table_args__ = (UniqueConstraint("container_id", "sha256"),)
    kind = "source_blob"
    sha256 = req()
    length = num(nullable=False)
    media_type = req()
    availability = req(default="available")  # available|missing|corrupt
    data = mapped_column(LargeBinary, nullable=True)


class SourceDocument(Record):
    __tablename__ = "source_documents"
    __table_args__ = (ref("source_blobs", "blob_id"), ref("patients", "patient_id"), ref("episodes", "episode_id"))
    kind = "source_document"
    family_id = uid(False)
    version_no = num(1, False)
    blob_id = uid(False)
    patient_id = uid()
    episode_id = uid()
    doc_kind = req()
    title = req()
    filename = req()
    issuer = txt()
    author = txt()
    external_id = txt()
    claimed_identity = jdict()
    association_status = req(default="pending")  # pending|associated|quarantined|rejected
    association_review = jdict(nullable=True)
    page_count = num(1, False)
    pages = jlist()  # text layer with line geometry: [{number,width,height,lines:[{text,bbox}]}]
    extraction_limits = jdict()
    received_time = jdict(nullable=True)
    supersedes_id = uid()
    legacy = jdict(nullable=True)


class Specimen(Record):
    __tablename__ = "specimens"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "specimen"
    patient_id = uid(False)
    label = req()
    material = txt()
    site = txt()
    collection_time = jdict(nullable=True)
    receipt_time = jdict(nullable=True)
    parent_id = uid()
    issuer = txt()


class ReportFamily(Record):
    __tablename__ = "report_families"
    __table_args__ = (UniqueConstraint("container_id", "issuer", "accession"), ref("patients", "patient_id"))
    kind = "report_family"
    patient_id = uid()
    issuer = req()
    accession = req()
    report_type = req()


class ReportVersion(Record):
    __tablename__ = "report_versions"
    __table_args__ = (ref("report_families", "family_id"), ref("patients", "patient_id"))
    kind = "report_version"
    family_id = uid(False)
    patient_id = uid()
    version_no = num(1, False)
    issued_status = req(default="final")  # as issued: preliminary|final|amended|corrected|withdrawn
    relation_kind = req(default="original")  # original|additive_addendum|correction|replacement|withdrawal|unresolved
    predecessor_id = uid()
    affected_scope = jlist()  # analyte/specimen pairs the issuer says are affected
    specimen_ids = jlist()
    document_ids = jlist()
    effective_time = jdict(nullable=True)
    issued_time = jdict(nullable=True)
    amended_time = jdict(nullable=True)
    scope_note = txt()


class AssayContext(Record):
    __tablename__ = "assay_contexts"
    __table_args__ = (ref("report_versions", "report_version_id"),)
    kind = "assay_context"
    report_version_id = uid(False)
    specimen_id = uid()
    name = req()
    panel = txt()
    method = txt()
    target_scope = txt()
    limitations = txt()


class ExtractionCandidate(Record):
    __tablename__ = "extraction_candidates"
    __table_args__ = (ref("source_documents", "document_id"),)
    kind = "extraction_candidate"
    document_id = uid(False)
    report_version_id = uid()
    patient_id = uid()
    extractor = req()
    extractor_version = req()
    manual = flag()
    assertion = jdict()  # analyte, dimension, exact_wording, value_text, value_number, units, reference_range, result_state, specimen_label
    source_ref = jdict()  # document_id, page, region [x0,y0,x1,y1] in page points (top-left origin), page_size
    status = req(default="unreviewed")  # unreviewed|verified|corrected|rejected|unresolved


class ObservationVersion(Record):
    __tablename__ = "observation_versions"
    __table_args__ = (ref("patients", "patient_id"), ref("report_versions", "report_version_id"),
                      ref("source_documents", "document_id"), ref("extraction_candidates", "candidate_id"))
    kind = "observation_version"
    key = uid(False)  # stable identity of the assertion across versions
    version_no = num(1, False)
    patient_id = uid(False)
    report_version_id = uid(False)
    specimen_id = uid()
    assay_id = uid()
    document_id = uid(False)
    candidate_id = uid()
    analyte = req()
    dimension = req()
    exact_wording = req()
    value_text = txt()
    value_number = txt()  # exact decimal string as reported; never a float
    units = txt()
    reference_range = txt()
    result_state = req()
    effective_time = jdict(nullable=True)
    source_ref = jdict()
    normalization = jdict()
    status = req(default="current")  # current|superseded|withdrawn
    supersedes_id = uid()
    superseded_seq = mapped_column(BigInteger, nullable=True)
    superseded_reason = txt()


class SourceReview(Record):
    """A reviewer's check of source wording. It is never a clinical interpretation."""

    __tablename__ = "source_reviews"
    __table_args__ = (ref("extraction_candidates", "candidate_id"),)
    kind = "source_review"
    candidate_id = uid(False)
    candidate_revision = num(nullable=False)
    disposition = req()  # verified|corrected|rejected|unresolved
    reason = txt()
    corrected = jdict(nullable=True)
    observation_id = uid()


class ExpectedInput(Record):
    """An anticipated artifact with an owner. It does not assert an order was placed or a test performed."""

    __tablename__ = "expected_inputs"
    __table_args__ = (ref("patients", "patient_id"), ref("episodes", "episode_id"))
    kind = "expected_input"
    patient_id = uid(False)
    episode_id = uid(False)
    artifact = req()
    report_type = req()
    upstream_request = txt()
    state = req(default="pending")  # pending|received|failed|cancelled|unknown
    owner_id = uid()
    owner_name = txt()
    next_action = txt()
    fulfilled_report_id = uid()
    history = jlist()


class ClinicalAssessment(Record):
    __tablename__ = "clinical_assessments"
    __table_args__ = (ref("patients", "patient_id"), ref("episodes", "episode_id"))
    kind = "clinical_assessment"
    family_id = uid(False)
    version_no = num(1, False)
    patient_id = uid(False)
    episode_id = uid(False)
    encounter_id = uid()
    narrative = req()
    dimension_notes = jdict()
    evidence = jlist()
    uncertainty = txt()
    classification_edition = txt()
    supersedes_id = uid()


class PatientDiscussion(Record):
    __tablename__ = "patient_discussions"
    __table_args__ = (ref("patients", "patient_id"), ref("episodes", "episode_id"))
    kind = "patient_discussion"
    family_id = uid(False)
    version_no = num(1, False)
    patient_id = uid(False)
    episode_id = uid(False)
    participants = jlist()
    attributed_to = req()  # patient|caregiver: the attributed source of the goals
    goals = req()
    preferences = txt()
    consent_reference = txt()
    supersedes_id = uid()


class ProfileSnapshot(Record):
    """Frozen profile at a knowledge cutoff; later-arriving facts never leak into it (R6)."""

    __tablename__ = "profile_snapshots"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "profile_snapshot"
    patient_id = uid(False)
    episode_id = uid()
    knowledge_cutoff_seq = mapped_column(BigInteger, nullable=False)
    observation_ids = jlist()
    assessment_id = uid()
    discussion_id = uid()
    unresolved = jlist()
    dimensions = jdict()
    digest = req()


class ScopeRevision(Record):
    """Watch-scope revision counter. `id` is unused; `scope_key` identifies the watched material."""

    __tablename__ = "scope_revisions"
    __table_args__ = (UniqueConstraint("container_id", "scope_key"),)
    kind = "scope_revision"
    scope_key = req()
    last_change = jdict()
