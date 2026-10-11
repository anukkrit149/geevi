from typing import Literal

from pydantic import BaseModel, Field

from app.models.follow_up import Concern, ConcernEvent, EncounterDecision, FollowUpObligation
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned
from app.schemas.sources import RelTime


class ConcernCreate(CommandBase):
    narrative: str = Field(min_length=8)
    attributed_to: Literal["patient", "caregiver", "staff"]
    responsible_service: str = "Fictional AML care team"
    owner_username: str


class ConcernAction(Revisioned):
    pass


class ConcernNarrative(Revisioned):
    narrative: str


class ConcernEscalate(Revisioned):
    narrative: str
    to_service: str = Field(min_length=3)
    owner_username: str


class ConcernReview(Revisioned):
    narrative: str
    close: bool = False


class FollowUpCreate(CommandBase):
    purpose: str = Field(min_length=5)
    due: RelTime
    owner_username: str


class FollowUpSchedule(Revisioned):
    scheduled_time: RelTime
    reason: str | None = None


class FollowUpReason(Revisioned):
    reason: str


class FollowUpTransfer(Revisioned):
    owner_username: str
    reason: str


class DueChange(Revisioned):
    due: RelTime
    reason: str


class NextObligation(BaseModel):
    purpose: str = Field(min_length=5)
    due: RelTime
    owner_username: str


class EncounterDecide(Revisioned):
    decision: Literal["continue_unchanged", "revise", "more_information", "unresolved"]
    rationale: str
    actual_time: RelTime | None = None
    next: NextObligation | None = None


ConcernEventOut = schema_for(ConcernEvent)
ConcernOut = schema_for(Concern, events=(list[ConcernEventOut], []))
EncounterDecisionOut = schema_for(EncounterDecision)
FollowUpOut = schema_for(FollowUpObligation, decisions=(list[EncounterDecisionOut], []))
