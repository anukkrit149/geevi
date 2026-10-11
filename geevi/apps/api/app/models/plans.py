from app.db.base import Record, jdict, jlist, num, ref, req, txt, uid


class PatientPlanVersion(Record):
    """Individual plan version: documented intent pinned to exact shared and patient-specific versions (R16)."""

    __tablename__ = "patient_plan_versions"
    __table_args__ = (ref("patients", "patient_id"), ref("protocol_versions", "protocol_version_id"),
                      ref("applicability_reviews", "applicability_id"), ref("patient_discussions", "discussion_id"))
    kind = "patient_plan_version"
    family_id = uid(False)
    version_no = num(1, False)
    patient_id = uid(False)
    episode_id = uid(False)
    protocol_version_id = uid(False)
    applicability_id = uid(False)
    discussion_id = uid()
    exception_ids = jlist()
    intent = req()
    alternatives = txt()
    rationale = txt()
    obligations = jlist()  # authored clinical obligations, e.g. routine follow-up review
    status = req(default="draft")  # draft|submitted|approved|superseded
    packet_id = uid()
    content_digest = txt()
    previous_version_id = uid()


class PlanApproval(Record):
    """Immutable demonstration signature over one exact plan packet. Not an institutional signature."""

    __tablename__ = "plan_approvals"
    __table_args__ = (ref("patient_plan_versions", "plan_version_id"),)
    kind = "plan_approval"
    plan_version_id = uid(False)
    packet_id = uid(False)
    target_digest = req()
    read_set = jlist()
    watch_set = jdict()
    statement = req()


class PlanDisposition(Record):
    """Disposition is recorded separately from signed content and from review currency (KTD7)."""

    __tablename__ = "plan_dispositions"
    __table_args__ = (ref("patient_plan_versions", "plan_version_id"),)
    kind = "plan_disposition"
    plan_family_id = uid(False)
    plan_version_id = uid(False)
    disposition = req()  # active|held|completed|superseded
    reason = txt()
