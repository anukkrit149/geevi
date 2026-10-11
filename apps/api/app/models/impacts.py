from sqlalchemy import UniqueConstraint

from app.db.base import Record, flag, jdict, jlist, ref, req, txt, uid


class ChangeEvent(Record):
    """Identity of one knowledge or source change; duplicate delivery maps to the same event."""

    __tablename__ = "change_events"
    __table_args__ = (UniqueConstraint("container_id", "dedupe_key"),)
    kind = "change_event"
    event_kind = req()  # protocol_published|protocol_withdrawn|source_change|patient_record_change|exception_expired|obligation_change
    dedupe_key = req()
    source_kind = req()
    source_id = uid()
    description = req()
    detail = jdict()


class ImpactReview(Record):
    """Separately owned review of one change against one patient's exact plan version and scope (R13)."""

    __tablename__ = "impact_reviews"
    __table_args__ = (UniqueConstraint("container_id", "change_event_id", "plan_version_id", "scope_key"),
                      ref("change_events", "change_event_id"), ref("patients", "patient_id"), ref("patient_plan_versions", "plan_version_id"))
    kind = "impact_review"
    change_event_id = uid(False)
    patient_id = uid(False)
    episode_id = uid(False)
    plan_version_id = uid(False)
    scope_key = req()
    owner_id = uid()
    owner_name = txt()
    needs_classification = flag()
    state = req(default="open")  # open|more_information|closed
    disposition = txt()  # retained|adopted|not_applicable|unaffected
    rationale = txt()
    review_trigger = txt()
    linked_plan_version_id = uid()
    history = jlist()
