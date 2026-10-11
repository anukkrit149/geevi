"""Generic independent review: frozen packets, named assignments, append-only decisions."""
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.errors import blocked, not_permitted
from app.core.policy import REVIEW_POLICY
from app.models.identity import Account, WorkspaceGrant
from app.models.reviews import ReviewAssignment, ReviewDecision, ReviewPacket, WorkItem
from app.services.command_service import Ctx, target

FINALIZERS: dict[str, Callable[[Ctx, ReviewPacket, bool], Any]] = {}


def capabilities_of(ctx: Ctx, account_id: UUID) -> set[str]:
    grant = ctx.db.scalar(select(WorkspaceGrant).where(WorkspaceGrant.workspace_id == ctx.workspace.id, WorkspaceGrant.account_id == account_id))
    return set(grant.capabilities) if grant else set()


def open_packet(ctx: Ctx, record, digest_value: str, reviewer_username: str | None, *, read_set: list | None = None,
                watch_set: dict | None = None) -> ReviewPacket:
    rule = REVIEW_POLICY["rules"][record.kind]
    reviewer = ctx.db.scalar(select(Account).where(Account.username == (reviewer_username or ""))) if reviewer_username else None
    if reviewer is None:
        raise blocked("independent_reviewer_required", "Name the independent reviewer required by the review policy before submitting.",
                      target=(record.kind, record.id), next_action="Assign a reviewer who holds the review grant and did not author this version.")
    if rule["review_capability"] not in capabilities_of(ctx, reviewer.id):
        raise blocked("reviewer_not_permitted", f"{reviewer.display_name} does not hold the '{rule['review_capability']}' grant.",
                      target=(record.kind, record.id), next_action="Assign a reviewer holding the required grant.")
    if rule["independent_of_author"] and reviewer.id == record.recorded_by:
        raise blocked("independent_reviewer_required", "The author cannot be the independent reviewer of their own version.",
                      target=(record.kind, record.id), next_action="Assign a different reviewer.")
    packet = ctx.new(ReviewPacket, target_kind=record.kind, target_id=record.id, target_digest=digest_value,
                     policy={"id": REVIEW_POLICY["id"], "version": REVIEW_POLICY["version"], "rule": rule, "note": REVIEW_POLICY["note"]},
                     read_set=read_set or [], watch_set=watch_set or {}, author_id=record.recorded_by, author_name=record.recorded_by_name)
    ctx.db.flush()
    ctx.new(ReviewAssignment, packet_id=packet.id, scope="independent_review", assignee_id=reviewer.id, assignee_name=reviewer.display_name)
    ctx.audit("review.submit", packet, detail={"target_kind": record.kind, "target_id": str(record.id), "reviewer": reviewer.display_name})
    return packet


def decide(ctx: Ctx, packet_id: UUID, body) -> dict:
    packet = ctx.get(ReviewPacket, packet_id)
    ctx.expect(packet, body.expected_revision)
    rule = packet.policy["rule"]
    assignment = next((a for a in ctx.all(ReviewAssignment, ReviewAssignment.packet_id == packet.id) if a.assignee_id == ctx.account.id), None)
    # Authority comes from the authenticated session: the assignee, holding the grant, who is not the author.
    if assignment is None:
        raise not_permitted("Only the reviewer assigned to this packet can record its decision.", target=("review_packet", packet.id),
                            next_action="Sign in as the assigned reviewer.")
    ctx.require(rule["review_capability"], ("review_packet", packet.id))
    if rule["independent_of_author"] and packet.author_id == ctx.account.id:
        raise not_permitted("An author cannot review their own work, whatever grants the account holds.", target=("review_packet", packet.id))
    if packet.status == "changes_requested":
        raise blocked("unresolved_objection", "This packet has an unresolved objection; the author must submit a successor revision.",
                      target=("review_packet", packet.id), next_action="Review the successor revision once it is submitted.")
    if packet.status != "open":
        raise blocked("review_closed", "This review packet is already decided.", target=("review_packet", packet.id))
    rationale = (body.rationale or "").strip()
    if body.decision == "object" and len(rationale) < 8:
        raise blocked("reason_required", "An objection needs a rationale the author can respond to.", target=("review_packet", packet.id))
    decision = ctx.new(ReviewDecision, packet_id=packet.id, assignment_id=assignment.id, scope=assignment.scope, decision=body.decision,
                       rationale=rationale or None, target_digest=packet.target_digest)
    packet.status = "approved" if body.decision == "approve" else "changes_requested"
    ctx.touch(packet)
    ctx.db.flush()
    FINALIZERS[packet.target_kind](ctx, packet, body.decision == "approve")
    ctx.audit("review.decide", packet, reason=rationale or None, detail={"decision": body.decision, "target_kind": packet.target_kind,
                                                                         "target_id": str(packet.target_id)})
    return target(packet, decision_id=str(decision.id), decision=body.decision)


def packet_view(ctx: Ctx, packet_id: UUID | None) -> dict | None:
    packet = ctx.find(ReviewPacket, packet_id)
    if packet is None:
        return None
    return {"packet": packet, "assignments": ctx.all(ReviewAssignment, ReviewAssignment.packet_id == packet.id),
            "decisions": ctx.all(ReviewDecision, ReviewDecision.packet_id == packet.id)}


def history(ctx: Ctx, target_ids: list[UUID]) -> list[dict]:
    """Every packet and decision for a version family, including resolved disagreements."""
    packets = [p for p in ctx.all(ReviewPacket) if p.target_id in set(target_ids)]
    return [packet_view(ctx, p.id) for p in packets]


def open_work(ctx: Ctx, work_kind: str, record, owner_id, owner_name, reason: str, next_action: str, change: dict | None = None,
              due_at=None) -> WorkItem:
    for item in ctx.all(WorkItem, WorkItem.target_id == record.id, WorkItem.work_kind == work_kind, WorkItem.status == "open"):
        if item.change == (change or {}):
            return item
    return ctx.new(WorkItem, work_kind=work_kind, target_kind=record.kind, target_id=record.id, owner_id=owner_id, owner_name=owner_name,
                   reason=reason, next_action=next_action, change=change or {}, due_at=due_at)


def close_work(ctx: Ctx, item_id: UUID, body) -> dict:
    item = ctx.get(WorkItem, item_id)
    ctx.expect(item, body.expected_revision)
    if item.owner_id != ctx.account.id:
        raise not_permitted("Only the owner of this work item can close it.", target=("work_item", item.id))
    if len(body.resolution.strip()) < 8:
        raise blocked("reason_required", "Record how this work was resolved.", target=("work_item", item.id))
    item.status, item.resolution = "closed", body.resolution.strip()
    ctx.touch(item)
    ctx.audit("work.close", item, reason=item.resolution)
    return target(item)
