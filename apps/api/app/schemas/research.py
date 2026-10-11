from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import department as d
from app.models import research as r
from app.models import reviews as rv
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned


class QuestionCreate(CommandBase):
    title: str = Field(min_length=5)
    question: str = Field(min_length=10)
    scope: str = Field(min_length=5)
    intended_use: str = Field(min_length=5)
    origin: dict[str, Any] | None = None  # e.g. a case-origin note; never changes a patient decision


class SourceCreate(CommandBase):
    title: str = Field(min_length=3)
    citation: str = Field(min_length=10)
    source_label: Literal["synthetic", "public_reference"] = "synthetic"
    filename: str | None = None
    media_type: str | None = None
    content_base64: str | None = None


class ReferenceBrief(BaseModel):
    id: str
    title: str
    citation: str
    url: str
    publication_date: str
    source_type: str
    question: str
    population: str
    intervention: str
    comparator: str
    outcomes: str
    findings: str
    limitations: str
    applicability: str
    license_note: str
    search_terms: list[str]
    access_status: str


class SourceAmend(Revisioned):
    reason: str = Field(min_length=8)
    title: str | None = None
    citation: str | None = None
    media_type: str | None = None
    content_base64: str | None = None


class Reasoned(Revisioned):
    reason: str = Field(min_length=8)


class Citation(BaseModel):
    source_id: UUID
    passage_id: str


class AppraisalContent(BaseModel):
    population: str = ""
    intervention: str = ""
    comparator: str = ""
    outcome: str = ""
    timepoint: str = ""
    study_design: str = ""
    findings: str = ""
    uncertainty: str = ""
    limitations: str = ""
    citations: list[Citation] = []


class AppraisalCreate(CommandBase, AppraisalContent):
    pass


class AppraisalSave(Revisioned, AppraisalContent):
    pass


class SubmitForReview(Revisioned):
    reviewer_username: str | None = None


class ReviewDecide(Revisioned):
    decision: Literal["approve", "object"]
    rationale: str | None = None


class QuestionConclude(Revisioned):
    conclusion: Literal["evidence_accepted", "insufficient_evidence"]
    note: str


class WorkClose(Revisioned):
    resolution: str


QuestionOut = schema_for(r.ResearchQuestion)
EvidenceSourceOut = schema_for(r.EvidenceSource, file_available=(bool, False), sha256=(str | None, None))
AppraisalOut = schema_for(r.EvidenceAppraisal)
PacketOut = schema_for(rv.ReviewPacket)
AssignmentOut = schema_for(rv.ReviewAssignment)
DecisionOut = schema_for(rv.ReviewDecision)
WorkItemOut = schema_for(rv.WorkItem)


class PacketView(BaseModel):
    packet: PacketOut
    assignments: list[AssignmentOut]
    decisions: list[DecisionOut]


class QuestionDetail(BaseModel):
    question: QuestionOut
    appraisals: list[AppraisalOut]
    reviews: list[PacketView]
    recommendation_notice: str = "A research conclusion issues no patient recommendation and publishes no protocol."


# ---- department -------------------------------------------------------------------------------

class Waiver(BaseModel):
    allowed: bool = False  # default requirements are non-waivable
    exception_type: Literal["operational", "clinical"] | None = None


class Requirement(BaseModel):
    id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,40}$")
    kind: Literal["identity", "context", "discussion", "operational", "clinical_input"]
    text: str = Field(min_length=8)
    gate: str = Field(pattern=r"^(plan_approval|step:[A-Z0-9-]+)$")
    waiver: Waiver = Waiver()
    watch: list[str] = []
    branch: dict[str, str] | None = None
    note: str | None = None


class ProtocolContent(BaseModel):
    title: str = Field(min_length=5)
    scope: str = Field(min_length=5)
    summary: str | None = None
    requirements: list[Requirement] = []
    evidence: list[UUID] = []


class ProtocolCreate(CommandBase, ProtocolContent):
    pass


class ProtocolSave(Revisioned, ProtocolContent):
    pass


class SopStep(BaseModel):
    id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,40}$")
    title: str = Field(min_length=3)
    role: str = Field(min_length=2)
    expected_evidence: str = Field(min_length=3)
    depends_on: list[str] = []
    requires: list[str] = []  # protocol requirement ids gating this step


class SopContent(BaseModel):
    title: str = Field(min_length=5)
    purpose: str = Field(min_length=8)
    escalation: str = Field(min_length=3)
    steps: list[SopStep] = []
    protocol_version_id: UUID | None = None


class SopCreate(CommandBase, SopContent):
    pass


class SopSave(Revisioned, SopContent):
    pass


class ReviseBody(CommandBase):
    rationale: str
    evidence: list[UUID] = []
    origin: dict[str, Any] | None = None


class PublishBody(Revisioned):
    effective_from: datetime | None = None
    review_due: datetime | None = None
    note: str | None = None


class WithdrawBody(Revisioned):
    reason: str


_LIFE = {"lifecycle": (str, ...), "selectable": (bool, ...), "review_due_reached": (bool, False)}
ProtocolOut = schema_for(d.ProtocolVersion, **_LIFE)
SopOut = schema_for(d.SopVersion, **_LIFE)
ProposalOut = schema_for(d.ChangeProposal)
PublicationOut = schema_for(d.PublicationDecision)


class ProtocolDetail(BaseModel):
    version: ProtocolOut
    family: list[ProtocolOut]
    reviews: list[PacketView]
    publications: list[PublicationOut]
    proposal: ProposalOut | None
    validation_notice: str = "Fictional workflow protocol. Clinical content is absent and unvalidated; not for clinical use."


class SopDetail(BaseModel):
    version: SopOut
    family: list[SopOut]
    reviews: list[PacketView]
    publications: list[PublicationOut]
    proposal: ProposalOut | None


class ReviewInboxItem(BaseModel):
    packet: PacketOut
    assignments: list[AssignmentOut]
    decisions: list[DecisionOut]
    target_title: str
