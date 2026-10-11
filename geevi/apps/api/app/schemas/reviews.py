from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.reviews import ApplicabilityReview
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned


class ApplicabilityStart(CommandBase):
    protocol_version_id: UUID


class Supporting(BaseModel):
    kind: Literal["observation_version", "patient_discussion", "clinical_assessment", "source_document"]
    id: UUID


class Criterion(BaseModel):
    requirement_id: str
    assessment: Literal["match", "difference", "unknown", "not_applicable"] | None = None
    rationale: str = ""
    supporting: list[Supporting] = []


class ApplicabilitySave(Revisioned):
    criteria: list[Criterion]


class RevisionOnly(Revisioned):
    pass


ApplicabilityOut = schema_for(ApplicabilityReview)
