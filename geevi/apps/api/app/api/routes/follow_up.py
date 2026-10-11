from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models.follow_up import Concern, ConcernEvent, EncounterDecision, FollowUpObligation
from app.schemas import follow_up as s
from app.schemas.commands import CommandResult
from app.services import follow_up
from app.services.command_service import Ctx

router = APIRouter(tags=["follow-up"])
W = "/workspaces/{workspace_id}"


def _concern(ctx: Ctx, c: Concern) -> dict:
    return {**{col.name: getattr(c, col.name) for col in c.__table__.columns}, "events": ctx.all(ConcernEvent, ConcernEvent.concern_id == c.id)}


def _obligation(ctx: Ctx, o: FollowUpObligation) -> dict:
    return {**{col.name: getattr(o, col.name) for col in o.__table__.columns},
            "decisions": ctx.all(EncounterDecision, EncounterDecision.obligation_id == o.id)}


@router.get(W + "/concerns", response_model=list[s.ConcernOut])
def list_concerns(patient_id: UUID | None = None, ctx: Ctx = Depends(reader)):
    return [_concern(ctx, c) for c in ctx.all(Concern, *([Concern.patient_id == patient_id] if patient_id else []))]


@router.post(W + "/patients/{patient_id}/concerns", response_model=CommandResult)
def report(workspace_id: UUID, patient_id: UUID, body: s.ConcernCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "concern.report", body, lambda ctx: follow_up.report_concern(ctx, patient_id, body), "concern.record")


@router.post(W + "/concerns/{concern_id}/acknowledge", response_model=CommandResult)
def acknowledge(workspace_id: UUID, concern_id: UUID, body: s.ConcernAction, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "concern.acknowledge", body, lambda ctx: follow_up.acknowledge(ctx, concern_id, body), "concern.respond")


@router.post(W + "/concerns/{concern_id}/respond", response_model=CommandResult)
def respond(workspace_id: UUID, concern_id: UUID, body: s.ConcernNarrative, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "concern.respond", body, lambda ctx: follow_up.respond(ctx, concern_id, body), "concern.respond")


@router.post(W + "/concerns/{concern_id}/escalate", response_model=CommandResult)
def escalate(workspace_id: UUID, concern_id: UUID, body: s.ConcernEscalate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "concern.escalate", body, lambda ctx: follow_up.escalate(ctx, concern_id, body), "concern.respond")


@router.post(W + "/concerns/{concern_id}/review", response_model=CommandResult)
def review(workspace_id: UUID, concern_id: UUID, body: s.ConcernReview, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "concern.review", body, lambda ctx: follow_up.review(ctx, concern_id, body), "concern.review")


@router.get(W + "/follow-ups", response_model=list[s.FollowUpOut])
def list_obligations(patient_id: UUID | None = None, ctx: Ctx = Depends(reader)):
    return [_obligation(ctx, o) for o in ctx.all(FollowUpObligation, *([FollowUpObligation.patient_id == patient_id] if patient_id else []))]


@router.post(W + "/patients/{patient_id}/follow-ups", response_model=CommandResult)
def create(workspace_id: UUID, patient_id: UUID, body: s.FollowUpCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.create", body, lambda ctx: follow_up.create(ctx, patient_id, body), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/schedule", response_model=CommandResult)
def schedule(workspace_id: UUID, obligation_id: UUID, body: s.FollowUpSchedule, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.schedule", body, lambda ctx: follow_up.schedule(ctx, obligation_id, body), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/miss", response_model=CommandResult)
def miss(workspace_id: UUID, obligation_id: UUID, body: s.FollowUpReason, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.miss", body, lambda ctx: follow_up.mark(ctx, obligation_id, body, "missed"), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/cancel", response_model=CommandResult)
def cancel(workspace_id: UUID, obligation_id: UUID, body: s.FollowUpReason, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.cancel", body, lambda ctx: follow_up.mark(ctx, obligation_id, body, "cancelled"), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/transfer", response_model=CommandResult)
def transfer(workspace_id: UUID, obligation_id: UUID, body: s.FollowUpTransfer, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.transfer", body, lambda ctx: follow_up.transfer(ctx, obligation_id, body), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/propose-due-change", response_model=CommandResult)
def propose_due_change(workspace_id: UUID, obligation_id: UUID, body: s.DueChange, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.due_change", body, lambda ctx: follow_up.propose_due_change(ctx, obligation_id, body), "followup.manage")


@router.post(W + "/follow-ups/{obligation_id}/decide", response_model=CommandResult)
def decide(workspace_id: UUID, obligation_id: UUID, body: s.EncounterDecide, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "follow_up.decide", body, lambda ctx: follow_up.decide(ctx, obligation_id, body), "followup.decide")
