from app.db.base import Record, jdict, jlist, num, ref, req, ts, txt, uid


class ExceptionRequest(Record):
    """Typed, scoped departure from one protocol requirement for one patient. Never changes the protocol (R17)."""

    __tablename__ = "exception_requests"
    __table_args__ = (ref("patients", "patient_id"), ref("protocol_versions", "protocol_version_id"))
    kind = "exception_request"
    family_id = uid(False)
    version_no = num(1, False)
    exception_type = req()  # operational|clinical
    requirement_id = req()
    protocol_version_id = uid(False)
    patient_id = uid(False)
    episode_id = uid(False)
    discussion_id = uid()
    departure = req()
    rationale = req()
    evidence = jlist()
    required_approvals = jdict()
    expires_at = ts()
    review_trigger = txt()
    status = req(default="pending")  # pending|approved|rejected|expired|withdrawn|superseded
    content_digest = req()
    supersedes_id = uid()
    owner_id = uid()
    owner_name = txt()


class ExceptionDecision(Record):
    __tablename__ = "exception_decisions"
    __table_args__ = (ref("exception_requests", "request_id"),)
    kind = "exception_decision"
    request_id = uid(False)
    request_digest = req()
    decision = req()  # approve|reject
    rationale = txt()
