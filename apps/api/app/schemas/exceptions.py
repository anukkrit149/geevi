from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.exceptions import ExceptionDecision, ExceptionRequest
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned


class ExceptionRequestBody(CommandBase):
    protocol_version_id: UUID
    requirement_id: str
    exception_type: Literal["operational", "clinical"]
    departure: str = Field(min_length=8)
    rationale: str = Field(min_length=8)
    evidence: list[UUID] = []
    expires_at: datetime | None = None
    review_trigger: str | None = None


class ExceptionRevise(Revisioned):
    protocol_version_id: UUID | None = None
    requirement_id: str | None = None
    exception_type: Literal["operational", "clinical"] | None = None
    departure: str = Field(min_length=8)
    rationale: str = Field(min_length=8)
    evidence: list[UUID] = []
    expires_at: datetime | None = None
    review_trigger: str | None = None


class ExceptionDecide(Revisioned):
    decision: Literal["approve", "reject"]
    rationale: str | None = None


class ExceptionWithdraw(Revisioned):
    reason: str | None = None


ExceptionDecisionOut = schema_for(ExceptionDecision)
ExceptionOut = schema_for(ExceptionRequest, effective_status=(str, ...), decisions=(list[ExceptionDecisionOut], []),
                          approvals_recorded=(int, 0), next_action=(str | None, None))
