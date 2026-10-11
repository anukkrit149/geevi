from app.db.base import Record, jdict, jlist, ref, req, txt, uid


class Task(Record):
    """SOP-derived work item. A task specification is never a clinical order."""

    __tablename__ = "tasks"
    __table_args__ = (ref("patients", "patient_id"), ref("sop_versions", "sop_version_id"), ref("patient_plan_versions", "plan_version_id"))
    kind = "task"
    patient_id = uid(False)
    episode_id = uid(False)
    sop_version_id = uid(False)
    sop_step_id = req()
    plan_version_id = uid(False)
    action = req()
    role = txt()
    expected_evidence = txt()
    requires = jlist()  # protocol requirement ids gating dispatch of this task
    depends_on = jlist()  # task ids
    owner_id = uid()
    owner_name = txt()
    assigned_by_id = uid()
    assigned_by_name = txt()
    due = jdict(nullable=True)
    note = txt()
    status = req(default="draft")  # draft|sent|received|accepted|returned|blocked|completed|cancelled
    completion_evidence = jdict(nullable=True)


class TaskEvent(Record):
    __tablename__ = "task_events"
    __table_args__ = (ref("tasks", "task_id"),)
    kind = "task_event"
    task_id = uid(False)
    event = req()
    reason = txt()
    detail = jdict()


class PlannedEvent(Record):
    """A planned appointment/request. Scheduling asserts nothing about delivery (R22)."""

    __tablename__ = "planned_events"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "planned_event"
    patient_id = uid(False)
    episode_id = uid(False)
    event_type = req()
    description = req()
    scheduled_time = jdict()
    location = txt()
    plan_version_id = uid()
    task_id = uid()
    obligation_id = uid()
    status = req(default="scheduled")  # scheduled|rescheduled|cancelled
    history = jlist()


class CareEvent(Record):
    """What actually happened, as attributed. Distinct from the plan and from scheduling."""

    __tablename__ = "care_events"
    __table_args__ = (ref("patients", "patient_id"), ref("patient_plan_versions", "plan_version_id"))
    kind = "care_event"
    patient_id = uid(False)
    episode_id = uid(False)
    planned_event_id = uid()
    task_id = uid()
    status = req()  # performed|partial|deferred|not_performed|unknown
    actual_time = jdict(nullable=True)
    narrative = req()
    source = req()  # direct|external_report
    performer_name = req()
    performer_account_id = uid()
    transcriber_name = txt()
    source_document_id = uid()
    plan_version_id = uid(False)  # historical reference only; never reactivates the plan
