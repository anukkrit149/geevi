from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.core.policy import REVIEW_POLICY
from app.models.department import ProtocolVersion, SopVersion
from app.models.research import EvidenceAppraisal
from app.models.reviews import ReviewAssignment, ReviewPacket, WorkItem
from app.schemas import research as s
from app.schemas.commands import CommandResult
from app.services import protocols, publication, reviews, sops
from app.services.command_service import Ctx

router = APIRouter(tags=["department"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/policy", response_model=dict[str, Any])
def policy(ctx: Ctx = Depends(reader)):
    return REVIEW_POLICY


def _routes(path: str, kind: publication.DocKind, values, detail_model, out_model, create_model, save_model, author: str, publish_cap: str):
    name = kind.model.kind

    @router.get(W + path, response_model=list[out_model], name=f"list_{name}")
    def list_versions(ctx: Ctx = Depends(reader)):
        return [publication.view(ctx, kind, v) for v in ctx.all(kind.model, order=(kind.model.recorded_seq, kind.model.version_no))]

    @router.get(W + path + "/{version_id}", response_model=detail_model, name=f"get_{name}")
    def get_version(version_id: UUID, ctx: Ctx = Depends(reader)):
        return publication.detail(ctx, kind, version_id)

    @router.post(W + path, response_model=CommandResult, name=f"create_{name}")
    def create(workspace_id: UUID, body: create_model, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.create", body, lambda ctx: publication.create(ctx, kind, values(body)), author)

    @router.post(W + path + "/{version_id}/revise", response_model=CommandResult, name=f"revise_{name}")
    def revise(workspace_id: UUID, version_id: UUID, body: s.ReviseBody, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.revise", body, lambda ctx: publication.revise(ctx, kind, version_id, body), author)

    @router.post(W + path + "/{version_id}/save", response_model=CommandResult, name=f"save_{name}")
    def save(workspace_id: UUID, version_id: UUID, body: save_model, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.save", body, lambda ctx: publication.save(ctx, kind, version_id, body.expected_revision, values(body)), author)

    @router.post(W + path + "/{version_id}/submit", response_model=CommandResult, name=f"submit_{name}")
    def submit(workspace_id: UUID, version_id: UUID, body: s.SubmitForReview, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.submit", body, lambda ctx: publication.submit(ctx, kind, version_id, body), author)

    @router.post(W + path + "/{version_id}/publish", response_model=CommandResult, name=f"publish_{name}")
    def publish(workspace_id: UUID, version_id: UUID, body: s.PublishBody, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.publish", body, lambda ctx: publication.publish(ctx, kind, version_id, body), publish_cap)

    @router.post(W + path + "/{version_id}/withdraw", response_model=CommandResult, name=f"withdraw_{name}")
    def withdraw(workspace_id: UUID, version_id: UUID, body: s.WithdrawBody, cmd: Commander = Depends(commander)):
        return cmd.run(workspace_id, f"{name}.withdraw", body, lambda ctx: publication.withdraw(ctx, kind, version_id, body), publish_cap)


_routes("/protocols", protocols.KIND, protocols.values, s.ProtocolDetail, s.ProtocolOut, s.ProtocolCreate, s.ProtocolSave, "protocol.author", "protocol.publish")
_routes("/sops", sops.KIND, sops.values, s.SopDetail, s.SopOut, s.SopCreate, s.SopSave, "sop.author", "sop.publish")

_TITLES = {"protocol_version": ProtocolVersion, "sop_version": SopVersion, "evidence_appraisal": EvidenceAppraisal}


@router.get(W + "/review-packets", response_model=list[s.ReviewInboxItem])
def review_inbox(mine: bool = True, status: str | None = "open", ctx: Ctx = Depends(reader)):
    """Review work for the signed-in account (server-derived), or every packet when mine=false."""
    items = []
    for packet in ctx.all(ReviewPacket):
        if packet.target_kind not in _TITLES:  # plan packets are signed by the treating clinician, not reviewed here
            continue
        assignments = ctx.all(ReviewAssignment, ReviewAssignment.packet_id == packet.id)
        if (status and packet.status != status) or (mine and not any(a.assignee_id == ctx.account.id for a in assignments)):
            continue
        record = ctx.find(_TITLES[packet.target_kind], packet.target_id)
        title = getattr(record, "title", None) or (f"Evidence appraisal v{record.version_no}" if record else packet.target_kind)
        items.append({**reviews.packet_view(ctx, packet.id), "target_title": title})
    return items


@router.post(W + "/review-packets/{packet_id}/decide", response_model=CommandResult)
def decide(workspace_id: UUID, packet_id: UUID, body: s.ReviewDecide, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "review.decide", body, lambda ctx: reviews.decide(ctx, packet_id, body))


@router.get(W + "/work-items", response_model=list[s.WorkItemOut])
def work_items(status: str | None = "open", ctx: Ctx = Depends(reader)):
    return [w for w in ctx.all(WorkItem) if not status or w.status == status]


@router.post(W + "/work-items/{item_id}/close", response_model=CommandResult)
def close_work(workspace_id: UUID, item_id: UUID, body: s.WorkClose, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "work.close", body, lambda ctx: reviews.close_work(ctx, item_id, body))
