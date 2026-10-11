from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models.impacts import ImpactReview
from app.schemas import impacts as s
from app.schemas.commands import CommandResult
from app.services import impacts
from app.services.command_service import Ctx

router = APIRouter(tags=["impacts"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/impacts", response_model=list[s.ImpactOut])
def list_impacts(patient_id: UUID | None = None, state: str | None = None, ctx: Ctx = Depends(reader)):
    rows = ctx.all(ImpactReview, *([ImpactReview.patient_id == patient_id] if patient_id else []))
    return [impacts.view(ctx, i) for i in rows if not state or (i.state != "closed" if state == "open" else i.state == state)]


@router.get(W + "/impacts/{impact_id}", response_model=s.ImpactOut)
def get_impact(impact_id: UUID, ctx: Ctx = Depends(reader)):
    return impacts.view(ctx, ctx.get(ImpactReview, impact_id))


@router.post(W + "/impacts/{impact_id}/classify", response_model=CommandResult)
def classify(workspace_id: UUID, impact_id: UUID, body: s.ImpactClassify, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "impact.classify", body, lambda ctx: impacts.classify(ctx, impact_id, body), "impact.resolve")


@router.post(W + "/impacts/{impact_id}/resolve", response_model=CommandResult)
def resolve(workspace_id: UUID, impact_id: UUID, body: s.ImpactResolve, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "impact.resolve", body, lambda ctx: impacts.resolve(ctx, impact_id, body), "impact.resolve")
