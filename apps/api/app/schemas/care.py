from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.care import CareEvent, PlannedEvent, Task, TaskEvent
from app.schemas.auto import schema_for
from app.schemas.commands import CommandBase, Revisioned
from app.schemas.plans import GateResult
from app.schemas.sources import RelTime


class TaskInstantiate(CommandBase):
    sop_version_id: UUID
    owners: dict[str, str] = {}
    due: dict[str, RelTime] = {}


class TaskUpdate(Revisioned):
    owner_username: str | None = None
    due: RelTime | None = None
    note: str | None = None


class TaskAction(Revisioned):
    pass


class TaskReason(Revisioned):
    reason: str


class TaskComplete(Revisioned):
    evidence: str
    care_event_id: UUID | None = None


class PlannedEventCreate(CommandBase):
    event_type: str = Field(min_length=3)
    description: str = Field(min_length=3)
    scheduled_time: RelTime
    location: str | None = None
    plan_version_id: UUID | None = None
    task_id: UUID | None = None


class CareEventCreate(CommandBase):
    status: Literal["performed", "partial", "deferred", "not_performed", "unknown"]
    actual_time: RelTime | None = None
    narrative: str = Field(min_length=8)
    source: Literal["direct", "external_report"] = "direct"
    performer_name: str | None = None
    plan_version_id: UUID
    planned_event_id: UUID | None = None
    task_id: UUID | None = None
    source_document_id: UUID | None = None


class TransferRequest(Revisioned):
    to_service: str = Field(min_length=3)
    reason: str


class TransferReceive(Revisioned):
    receipt_note: str


TaskEventOut = schema_for(TaskEvent)
TaskOut = schema_for(Task, sop_title=(str, ...), sop_version_no=(int, ...), gates=(list[GateResult], []), events=(list[TaskEventOut], []))
PlannedEventOut = schema_for(PlannedEvent)
CareEventOut = schema_for(CareEvent)
