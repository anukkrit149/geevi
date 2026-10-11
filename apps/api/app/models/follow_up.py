from app.db.base import Record, flag, jdict, jlist, ref, req, txt, uid


class Concern(Record):
    """A reported symptom or question as attributed narrative. No triage is inferred."""

    __tablename__ = "concerns"
    __table_args__ = (ref("patients", "patient_id"),)
    kind = "concern"
    patient_id = uid(False)
    episode_id = uid(False)
    narrative = req()
    attributed_to = req()  # patient|caregiver|staff
    responsible_service = req()
    owner_id = uid()
    owner_name = txt()
    status = req(default="open")  # open|acknowledged|responded|escalated|reviewed|closed
    unresolved_duty = txt()


class ConcernEvent(Record):
    __tablename__ = "concern_events"
    __table_args__ = (ref("concerns", "concern_id"),)
    kind = "concern_event"
    concern_id = uid(False)
    event = req()  # reported|acknowledged|responded|escalated|reviewed|closed
    narrative = txt()
    detail = jdict()


class FollowUpObligation(Record):
    """A routine review duty, separate from any concern, with its own owner and dispositions (R24)."""

    __tablename__ = "follow_up_obligations"
    __table_args__ = (ref("patients", "patient_id"), ref("patient_plan_versions", "plan_version_id"))
    kind = "follow_up_obligation"
    patient_id = uid(False)
    episode_id = uid(False)
    plan_version_id = uid(False)
    purpose = req()
    authored = flag()  # authored clinical obligation (from the signed plan) vs administrative
    plan_obligation_id = txt()
    due = jdict()  # authored clinical timing
    scheduled_time = jdict(nullable=True)  # administrative appointment logistics
    owner_id = uid()
    owner_name = txt()
    state = req(default="open")  # open|scheduled|fulfilled|missed|cancelled|transferred
    pending_change = jdict(nullable=True)
    previous_obligation_id = uid()
    history = jlist()


class EncounterDecision(Record):
    """Clinician's decision at a follow-up encounter; an unchanged continuation keeps the same plan (R25)."""

    __tablename__ = "encounter_decisions"
    __table_args__ = (ref("follow_up_obligations", "obligation_id"), ref("patient_plan_versions", "plan_version_id"),
                      ref("encounters", "encounter_id"))
    kind = "encounter_decision"
    obligation_id = uid(False)
    encounter_id = uid(False)
    patient_id = uid(False)
    plan_version_id = uid(False)
    decision = req()  # continue_unchanged|revise|more_information|unresolved
    rationale = req()
    input_packet = jdict()
    next_obligation_id = uid()
