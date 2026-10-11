"""Review packets, assignments and decisions shared by evidence, protocol and SOP review (R8/R10)."""
from app.db.base import Record, flag, jdict, jlist, num, ref, req, ts, txt, uid


class ReviewPacket(Record):
    """Immutable review target: exact version digest, policy version, read set and watched scopes."""

    __tablename__ = "review_packets"
    kind = "review_packet"
    target_kind = req()
    target_id = uid(False)
    target_digest = req()
    policy = jdict()
    read_set = jlist()
    watch_set = jdict()
    status = req(default="open")  # open|approved|changes_requested
    author_id = uid()
    author_name = txt()


class ReviewAssignment(Record):
    __tablename__ = "review_assignments"
    __table_args__ = (ref("review_packets", "packet_id"),)
    kind = "review_assignment"
    packet_id = uid(False)
    scope = req()
    assignee_id = uid(False)
    assignee_name = req()
    required = flag(True)


class ReviewDecision(Record):
    """Append-only decision by the authenticated assignee against the exact packet."""

    __tablename__ = "review_decisions"
    __table_args__ = (ref("review_packets", "packet_id"), ref("review_assignments", "assignment_id"))
    kind = "review_decision"
    packet_id = uid(False)
    assignment_id = uid(False)
    scope = req()
    decision = req()  # approve|object
    rationale = txt()
    target_digest = req()


class WorkItem(Record):
    """Owned follow-up work on departmental knowledge (dependent review, review due, classification)."""

    __tablename__ = "work_items"
    kind = "work_item"
    work_kind = req()
    target_kind = req()
    target_id = uid(False)
    owner_id = uid()
    owner_name = txt()
    reason = req()
    next_action = txt()
    due_at = ts()
    status = req(default="open")  # open|closed
    resolution = txt()
    change = jdict()


class ApplicabilityReview(Record):
    """Criterion-level applicability of one protocol version to one patient (R15)."""

    __tablename__ = "applicability_reviews"
    __table_args__ = (ref("patients", "patient_id"), ref("protocol_versions", "protocol_version_id"), ref("profile_snapshots", "snapshot_id"))
    kind = "applicability_review"
    family_id = uid(False)
    version_no = num(1, False)
    patient_id = uid(False)
    episode_id = uid(False)
    protocol_version_id = uid(False)
    snapshot_id = uid(False)
    criteria = jlist()  # [{requirement_id, assessment: match|difference|unknown|not_applicable, rationale, supporting:[{kind,id}]}]
    status = req(default="draft")  # draft|accepted|superseded
    accepted_at = ts()
    content_digest = txt()
    supersedes_id = uid()
