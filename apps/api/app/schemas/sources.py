from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import sources as m
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned

ResultState = Literal["reported_value", "detected", "not_detected", "pending", "untested", "indeterminate",
                      "insufficient_sample", "unreported", "unavailable"]
Dimension = Literal["biology", "extent", "fitness", "history", "current", "priorities"]


class RelTime(BaseModel):
    """Relative demonstration time. Unrelated anchors are never merged into one calendar."""

    value: int
    unit: Literal["day"] = "day"
    anchor: str = "episode-day-0"
    precision: Literal["day", "week", "unknown"] = "day"
    basis: str = "fictional relative demonstration day"


class Identifier(BaseModel):
    system: str = Field(min_length=2)
    value: str = Field(min_length=1)


class PatientCreate(CommandBase):
    display_name: str = Field(min_length=1)
    identifiers: list[Identifier] = Field(min_length=1)
    summary: str | None = None
    episode_title: str = Field(min_length=3)
    service: str = "Fictional haematology-oncology service"
    responsible_team: str = "Fictional AML team"


class DocumentUpload(CommandBase):
    patient_id: UUID
    filename: str = Field(min_length=1, max_length=200)
    media_type: str
    content_base64: str
    doc_kind: str = Field(min_length=2)  # report type, e.g. referral|blood_panel|marrow|flow|cytogenetics|molecular|other
    title: str | None = None
    issuer: str | None = None
    accession: str | None = None
    author: str | None = None
    relation: Literal["original", "additive_addendum", "correction", "replacement", "withdrawal"] | None = None
    received_time: RelTime | None = None


class AssociateBody(Revisioned):
    patient_id: UUID
    checked: bool
    note: str


class RejectDocument(Revisioned):
    reason: str


class ManualCandidate(CommandBase):
    page: int = Field(ge=1)
    region: list[float] = Field(min_length=4, max_length=4)
    analyte: str = Field(min_length=2)
    dimension: Dimension
    exact_wording: str = Field(min_length=2)
    value_text: str | None = None
    value_number: str | None = None
    units: str | None = None
    result_state: ResultState
    specimen_label: str | None = None


class CorrectedAssertion(BaseModel):
    value_text: str | None = None
    value_number: str | None = None
    units: str | None = None
    result_state: ResultState | None = None


class CandidateReview(Revisioned):
    disposition: Literal["verified", "corrected", "rejected", "unresolved"]
    reason: str | None = None
    corrected: CorrectedAssertion | None = None
    source_inspected: bool = False


class ExpectedInputCreate(CommandBase):
    patient_id: UUID
    artifact: str = Field(min_length=3)
    report_type: str
    upstream_request: str | None = None  # only when actually known; never implied
    owner_username: str
    next_action: str = Field(min_length=3)


class ExpectedInputUpdate(Revisioned):
    state: Literal["pending", "failed", "cancelled", "unknown"] | None = None
    owner_username: str | None = None
    next_action: str | None = None
    reason: str | None = None


class ExpectedInputLink(Revisioned):
    report_version_id: UUID


class AssessmentCreate(CommandBase):
    narrative: str = Field(min_length=8)
    dimension_notes: dict[Dimension, str] = {}
    evidence: list[UUID] = []
    uncertainty: str | None = None
    classification_edition: str | None = None
    expected_family_revision: int | None = None


class DiscussionCreate(CommandBase):
    participants: list[str] = Field(min_length=1)
    attributed_to: Literal["patient", "caregiver"]
    goals: str = Field(min_length=8)
    preferences: str | None = None
    consent_reference: str | None = None


PatientOut = schema_for(m.Patient)
IdentifierOut = schema_for(m.ExternalIdentifier)
EpisodeOut = schema_for(m.Episode)
EncounterOut = schema_for(m.Encounter)
DocumentOut = schema_for(m.SourceDocument, exclude={"pages"}, original_available=(bool, False), sha256=(str | None, None),
                         media_type=(str | None, None), length=(int | None, None))
DocumentDetailOut = schema_for(m.SourceDocument, "DocumentDetailOut", original_available=(bool, False), sha256=(str | None, None),
                               media_type=(str | None, None), length=(int | None, None))
SpecimenOut = schema_for(m.Specimen)
ReportFamilyOut = schema_for(m.ReportFamily)
ReportVersionOut = schema_for(m.ReportVersion, issuer=(str | None, None), accession=(str | None, None), report_type=(str | None, None))
CandidateOut = schema_for(m.ExtractionCandidate)
ObservationOut = schema_for(m.ObservationVersion, specimen_label=(str | None, None))
SourceReviewOut = schema_for(m.SourceReview)
ExpectedInputOut = schema_for(m.ExpectedInput)
AssessmentOut = schema_for(m.ClinicalAssessment)
DiscussionOut = schema_for(m.PatientDiscussion)
SnapshotOut = schema_for(m.ProfileSnapshot)


class PatientDetail(BaseModel):
    patient: PatientOut
    identifiers: list[IdentifierOut]
    episodes: list[EpisodeOut]


class UnresolvedItem(BaseModel):
    kind: str
    text: str
    target_kind: str | None = None
    target_id: UUID | None = None
    owner: str | None = None
    next_action: str | None = None


class DimensionView(BaseModel):
    id: str
    title: str
    description: str
    observations: list[ObservationOut]
    clinician_note: str | None = None
    unresolved: list[str]


class TrendPoint(BaseModel):
    observation_id: UUID
    value_text: str | None
    units: str | None
    result_state: str
    effective_time: dict[str, Any] | None
    specimen_label: str | None
    recorded_seq: int


class Trend(BaseModel):
    analyte: str
    points: list[TrendPoint]


class ProfileOut(BaseModel):
    patient_id: UUID
    knowledge_cutoff_seq: int
    historical: bool
    dimensions: list[DimensionView]
    trends: list[Trend]
    unresolved: list[UnresolvedItem]
    assessment: AssessmentOut | None
    discussion: DiscussionOut | None
    validation_notice: str = ("Fictional data. Profile groupings are review prompts, not clinical eligibility rules; "
                              "extraction and clinical content are unvalidated.")


class DocumentBundle(BaseModel):
    document: DocumentDetailOut
    reports: list[ReportVersionOut]
    specimens: list[SpecimenOut]
    candidates: list[CandidateOut]
    observations: list[ObservationOut]
    reviews: list[SourceReviewOut]
