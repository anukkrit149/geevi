from app.db.base import Record, jdict, jlist, num, req, ts, txt, uid


class _Published:
    family_id = uid(False)
    version_no = num(1, False)
    title = req()
    owner_id = uid()
    owner_name = txt()
    status = req(default="draft")  # draft|in_review|changes_requested|approved|published|withdrawn
    packet_id = uid()
    content_digest = txt()
    approved_at = ts()
    published_at = ts()
    effective_from = ts()
    review_due = ts()
    withdrawn_at = ts()
    withdrawn_reason = txt()
    predecessor_id = uid()
    proposal_id = uid()


class ProtocolVersion(_Published, Record):
    """Shared departmental protocol template version. Fictional workflow content only."""

    __tablename__ = "protocol_versions"
    kind = "protocol_version"
    scope = req()
    summary = txt()
    requirements = jlist()  # stable ids, waiver policy, gate and watch scopes
    evidence = jlist()  # accepted appraisal version ids


class SopVersion(_Published, Record):
    """Departmental SOP version: role-owned operational steps that create task specifications."""

    __tablename__ = "sop_versions"
    kind = "sop_version"
    purpose = req()
    steps = jlist()
    escalation = req()
    protocol_version_id = uid()


class ChangeProposal(Record):
    __tablename__ = "change_proposals"
    kind = "change_proposal"
    target_kind = req()
    family_id = uid(False)
    base_version_id = uid(False)
    rationale = req()
    evidence = jlist()
    diff = jdict()
    status = req(default="drafted")  # drafted|accepted|rejected
    resulting_version_id = uid()
    origin = jdict()


class PublicationDecision(Record):
    """The separate publication decision against an approved, frozen version."""

    __tablename__ = "publication_decisions"
    kind = "publication_decision"
    target_kind = req()
    target_id = uid(False)
    target_digest = req()
    decision = req(default="publish")  # publish|withdraw
    effective_from = ts()
    policy = jdict()
    note = txt()
