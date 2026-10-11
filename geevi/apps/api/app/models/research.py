from app.db.base import Record, flag, jdict, jlist, num, ref, req, txt, uid


class ResearchQuestion(Record):
    __tablename__ = "research_questions"
    kind = "research_question"
    title = req()
    question = req()
    scope = req()
    intended_use = req()
    owner_id = uid()
    owner_name = txt()
    status = req(default="open")  # open|concluded
    conclusion = txt()  # evidence_accepted|insufficient_evidence
    conclusion_note = txt()
    origin = jdict()


class EvidenceSource(Record):
    """A cited evidence source version (citation and, when held, the file and its passages)."""

    __tablename__ = "evidence_sources"
    __table_args__ = (ref("source_blobs", "blob_id"),)
    kind = "evidence_source"
    family_id = uid(False)
    version_no = num(1, False)
    title = req()
    citation = req()
    source_label = req(default="synthetic")  # synthetic|public_reference
    blob_id = uid()
    passages = jlist()
    extraction_limits = jdict()
    status = req(default="active")  # active|amended|withdrawn
    status_reason = txt()
    supersedes_id = uid()


class EvidenceAppraisal(Record):
    __tablename__ = "evidence_appraisals"
    __table_args__ = (ref("research_questions", "question_id"),)
    kind = "evidence_appraisal"
    question_id = uid(False)
    family_id = uid(False)
    version_no = num(1, False)
    content = jdict()  # population/intervention/comparator/outcome/timepoint/study_design/findings/uncertainty/limitations as reported
    citations = jlist()  # [{source_id, passage_id}]
    status = req(default="draft")  # draft|in_review|changes_requested|accepted|superseded
    packet_id = uid()
    content_digest = txt()
    supersedes_id = uid()
    review_needed = flag()
    review_needed_reason = txt()
