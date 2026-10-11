from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.plans import PatientPlanVersion, PlanApproval, PlanDisposition
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned
from app.schemas.research import PacketOut
from app.schemas.sources import RelTime


class Obligation(BaseModel):
    """Authored clinical obligation carried by the signed plan (e.g. a routine follow-up review)."""

    id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,40}$")
    purpose: str = Field(min_length=5)
    due: RelTime
    owner_username: str


class PlanContent(BaseModel):
    applicability_id: UUID
    discussion_id: UUID | None = None
    exception_ids: list[UUID] = []
    intent: str = Field(min_length=3)
    alternatives: str | None = None
    rationale: str | None = None
    obligations: list[Obligation] = []


class PlanStart(CommandBase, PlanContent):
    pass


class PlanSave(Revisioned, PlanContent):
    pass


class PlanApprove(Revisioned):
    """The signer names the exact frozen packet and digest they reviewed."""

    packet_id: UUID
    digest: str


class DispositionBody(Revisioned):
    disposition: Literal["active", "held", "completed"]
    reason: str


PlanOut = schema_for(PatientPlanVersion)
PlanApprovalOut = schema_for(PlanApproval)
PlanDispositionOut = schema_for(PlanDisposition)


class GateResult(BaseModel):
    requirement_id: str
    assessment: str | None
    satisfied: bool
    code: str | None
    message: str | None
    exception_id: str | None
    exception_state: str | None


class Currency(BaseModel):
    status: Literal["current", "review_needed"]
    reasons: list[dict[str, Any]]


class PlanView(BaseModel):
    plan: PlanOut
    packet: PacketOut | None
    approval: PlanApprovalOut | None
    disposition: str | None
    dispositions: list[PlanDispositionOut]
    currency: Currency
    gates: list[GateResult]
    packet_changes: list[dict[str, Any]]
    signature_notice: str = "Signatures are demonstration records by fictional development identities, not verified institutional signatures."
