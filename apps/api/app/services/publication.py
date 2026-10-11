"""Shared review -> approval -> publication lifecycle for protocol and SOP versions (R10/R11).

Draft -> InReview -> (ChangesRequested -> successor draft) -> Approved -> Published -> Effective ->
Superseded | Withdrawn. Effective/superseded are projections over recorded dates; reading a page
never creates an approval. Content is frozen at submission and can only change through a successor.
"""
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.errors import blocked, not_permitted
from app.core.security import digest
from app.models.department import ChangeProposal, PublicationDecision
from app.models.reviews import ReviewDecision, ReviewPacket
from app.services import reviews
from app.services.command_service import Ctx, target


@dataclass
class DocKind:
    model: Any
    fields: tuple[str, ...]
    validate: Callable[[Ctx, Any], None]
    on_publish: Callable[[Ctx, Any], dict] = lambda ctx, record: {}
    on_withdraw: Callable[[Ctx, Any], dict] = lambda ctx, record: {}


def content_digest(kind: DocKind, record) -> str:
    return digest({"family": record.family_id, "version": record.version_no, "title": record.title,
                   **{f: getattr(record, f) for f in kind.fields}})


def family(ctx: Ctx, kind: DocKind, family_id: UUID) -> list:
    return ctx.all(kind.model, kind.model.family_id == family_id, order=kind.model.version_no)


def lifecycle(ctx: Ctx, kind: DocKind, record, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if record.status != "published":
        return record.status
    if record.effective_from and record.effective_from > now:
        return "published"  # published, not yet effective
    for other in family(ctx, kind, record.family_id):
        if other.version_no > record.version_no and other.status == "published" and other.effective_from and other.effective_from <= now:
            return "superseded"
    return "effective"


def view(ctx: Ctx, kind: DocKind, record) -> dict:
    state = lifecycle(ctx, kind, record)
    data = {c.name: getattr(record, c.name) for c in record.__table__.columns}
    return {**data, "lifecycle": state, "selectable": state == "effective",
            "review_due_reached": bool(record.review_due and record.review_due <= datetime.now(UTC) and state in ("effective", "published"))}


def create(ctx: Ctx, kind: DocKind, values: dict) -> dict:
    record = ctx.new(kind.model, family_id=uuid.uuid4(), owner_id=ctx.account.id, owner_name=ctx.account.display_name, **values)
    ctx.audit(f"{record.kind}.create", record)
    return target(record)


def revise(ctx: Ctx, kind: DocKind, version_id: UUID, body) -> dict:
    """Successor draft from a change proposal; the base version and its signatures stay untouched."""
    base = ctx.get(kind.model, version_id)
    versions = family(ctx, kind, base.family_id)
    if any(v.status in ("draft", "in_review", "approved") for v in versions):
        raise blocked("revision_in_progress", "A successor revision of this document is already in progress.", target=(base.kind, base.id))
    if base.status not in ("published", "changes_requested", "withdrawn"):
        raise blocked("not_revisable", "Only a published, withdrawn or changes-requested version can be revised.", target=(base.kind, base.id))
    if len(body.rationale.strip()) < 8:
        raise blocked("reason_required", "A change proposal needs a rationale.", target=(base.kind, base.id))
    proposal = ctx.new(ChangeProposal, target_kind=base.kind, family_id=base.family_id, base_version_id=base.id, rationale=body.rationale.strip(),
                       evidence=[str(e) for e in body.evidence], origin=body.origin or {})
    ctx.db.flush()
    draft = ctx.new(kind.model, family_id=base.family_id, version_no=versions[-1].version_no + 1, title=base.title, owner_id=ctx.account.id,
                    owner_name=ctx.account.display_name, predecessor_id=base.id, proposal_id=proposal.id,
                    **{f: getattr(base, f) for f in kind.fields})
    ctx.db.flush()
    proposal.resulting_version_id = draft.id
    ctx.audit(f"{base.kind}.revise", draft, reason=proposal.rationale, detail={"base": str(base.id), "proposal": str(proposal.id)})
    return target(draft, proposal_id=str(proposal.id))


def _draft(ctx: Ctx, kind: DocKind, version_id: UUID, expected_revision: int):
    record = ctx.get(kind.model, version_id)
    ctx.expect(record, expected_revision)
    if record.status != "draft":
        raise blocked("immutable_version", "This version is frozen; its content can only change through a successor revision.",
                      target=(record.kind, record.id), next_action="Open a change proposal to draft a successor.")
    if record.recorded_by != ctx.account.id:
        raise not_permitted("Only the author can edit this draft.", target=(record.kind, record.id))
    return record


def save(ctx: Ctx, kind: DocKind, version_id: UUID, expected_revision: int, values: dict) -> dict:
    record = _draft(ctx, kind, version_id, expected_revision)
    for key, value in values.items():
        setattr(record, key, value)
    ctx.touch(record)
    if record.proposal_id:
        base = ctx.get(kind.model, record.predecessor_id)
        ctx.get(ChangeProposal, record.proposal_id).diff = {f: {"before": getattr(base, f), "after": getattr(record, f)}
                                                           for f in ("title", *kind.fields) if getattr(base, f) != getattr(record, f)}
    ctx.audit(f"{record.kind}.save", record)
    return target(record)


def submit(ctx: Ctx, kind: DocKind, version_id: UUID, body) -> dict:
    record = _draft(ctx, kind, version_id, body.expected_revision)
    kind.validate(ctx, record)
    record.content_digest = content_digest(kind, record)
    packet = reviews.open_packet(ctx, record, record.content_digest, body.reviewer_username)
    record.status, record.packet_id = "in_review", packet.id
    ctx.touch(record)
    return target(record, packet_id=str(packet.id))


def finalizer(kind: DocKind) -> Callable:
    def finalize(ctx: Ctx, packet: ReviewPacket, approved: bool) -> None:
        record = ctx.get(kind.model, packet.target_id)
        if approved:
            if content_digest(kind, record) != packet.target_digest:
                raise blocked("stale_target", "The version under review changed after submission.", target=(record.kind, record.id))
            record.status, record.approved_at = "approved", datetime.now(UTC)
        else:
            record.status = "changes_requested"
        ctx.touch(record)
    return finalize


def publish(ctx: Ctx, kind: DocKind, version_id: UUID, body) -> dict:
    """The publisher's separate decision against the approved, frozen version."""
    record = ctx.get(kind.model, version_id)
    ctx.expect(record, body.expected_revision)
    packet = ctx.find(ReviewPacket, record.packet_id)
    if record.status != "approved" or packet is None or packet.status != "approved":
        raise blocked("required_review_absent", "Publication requires the independent reviewer's approval of this exact version.",
                      target=(record.kind, record.id), next_action="Submit the version for independent review and wait for approval.",
                      details={"status": record.status})
    if content_digest(kind, record) != packet.target_digest or record.content_digest != packet.target_digest:
        raise blocked("stale_target", "The approved content no longer matches this version.", target=(record.kind, record.id))
    approvals = [d for d in ctx.all(ReviewDecision, ReviewDecision.packet_id == packet.id) if d.decision == "approve"]
    if not approvals or any(d.recorded_by == record.recorded_by for d in approvals):
        raise blocked("independent_reviewer_required", "The approval must come from an account other than the author.", target=(record.kind, record.id))
    now = datetime.now(UTC)
    effective = body.effective_from or now
    if effective < now - timedelta(minutes=5):
        raise blocked("invalid_effective_date", "A version cannot become effective before it is published.", target=(record.kind, record.id))
    record.status, record.published_at, record.effective_from, record.review_due = "published", now, effective, body.review_due
    ctx.touch(record)
    ctx.new(PublicationDecision, target_kind=record.kind, target_id=record.id, target_digest=record.content_digest, decision="publish",
            effective_from=effective, policy=packet.policy, note=body.note)
    if record.proposal_id:
        ctx.get(ChangeProposal, record.proposal_id).status = "accepted"
    if body.review_due:
        reviews.open_work(ctx, "review_due", record, record.owner_id, record.owner_name, "Scheduled review of this published version.",
                          "Review the version; it stays effective until an authorised decision changes it.", due_at=body.review_due)
    extra = kind.on_publish(ctx, record)  # successor publication nominates patient impacts in this same transaction
    ctx.audit(f"{record.kind}.publish", record, detail={"effective_from": effective.isoformat(), **extra})
    return target(record, **extra)


def withdraw(ctx: Ctx, kind: DocKind, version_id: UUID, body) -> dict:
    record = ctx.get(kind.model, version_id)
    ctx.expect(record, body.expected_revision)
    if record.status != "published":
        raise blocked("not_published", "Only a published version can be withdrawn.", target=(record.kind, record.id))
    if len(body.reason.strip()) < 8:
        raise blocked("reason_required", "Record why this version is withdrawn.", target=(record.kind, record.id))
    record.status, record.withdrawn_at, record.withdrawn_reason = "withdrawn", datetime.now(UTC), body.reason.strip()
    ctx.touch(record)
    ctx.new(PublicationDecision, target_kind=record.kind, target_id=record.id, target_digest=record.content_digest or "", decision="withdraw",
            note=body.reason.strip())
    extra = kind.on_withdraw(ctx, record)  # nominates review for dependants; never an automatic stop instruction
    ctx.audit(f"{record.kind}.withdraw", record, reason=body.reason.strip(), detail=extra)
    return target(record, **extra)


def detail(ctx: Ctx, kind: DocKind, version_id: UUID) -> dict:
    record = ctx.get(kind.model, version_id)
    versions = family(ctx, kind, record.family_id)
    return {"version": view(ctx, kind, record), "family": [view(ctx, kind, v) for v in versions],
            "reviews": reviews.history(ctx, [v.id for v in versions]),
            "publications": [p for p in ctx.all(PublicationDecision) if p.target_id in {v.id for v in versions}],
            "proposal": ctx.find(ChangeProposal, record.proposal_id)}
