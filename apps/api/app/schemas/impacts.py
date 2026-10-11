from typing import Literal
from uuid import UUID

from app.models.impacts import ChangeEvent, ImpactReview
from app.schemas.auto import schema_for
from app.schemas.commands import Revisioned


class ImpactClassify(Revisioned):
    relevant: bool
    rationale: str


class ImpactResolve(Revisioned):
    disposition: Literal["retained", "adopted", "not_applicable", "unaffected", "more_information"]
    rationale: str | None = None
    review_trigger: str | None = None
    linked_plan_version_id: UUID | None = None


ChangeEventOut = schema_for(ChangeEvent)
ImpactOut = schema_for(ImpactReview, change=(ChangeEventOut, ...), plan_version_no=(int, ...), plan_protocol_version_id=(UUID, ...),
                       next_action=(str | None, None))
