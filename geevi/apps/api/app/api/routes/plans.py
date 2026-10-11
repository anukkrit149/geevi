from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models import sources as m
from app.models.plans import PatientPlanVersion
from app.schemas import plans as s
from app.schemas.commands import CommandResult
from app.schemas.reviews import RevisionOnly
from app.services import plans
from app.services.command_service import Ctx

router = APIRouter(tags=["plans"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/patients/{patient_id}/plans", response_model=list[s.PlanView])
def list_plans(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return [plans.view(ctx, p) for p in plans.family_versions(ctx, patient_id)]


@router.get(W + "/plans/{plan_id}", response_model=s.PlanView)
def get_plan(plan_id: UUID, ctx: Ctx = Depends(reader)):
    return plans.view(ctx, ctx.get(PatientPlanVersion, plan_id))


@router.post(W + "/patients/{patient_id}/plans", response_model=CommandResult)
def start(workspace_id: UUID, patient_id: UUID, body: s.PlanStart, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.start", body, lambda ctx: plans.start(ctx, patient_id, body), "plan.author")


@router.post(W + "/plans/{plan_id}/save", response_model=CommandResult)
def save(workspace_id: UUID, plan_id: UUID, body: s.PlanSave, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.save", body, lambda ctx: plans.save(ctx, plan_id, body), "plan.author")


@router.post(W + "/plans/{plan_id}/submit", response_model=CommandResult)
def submit(workspace_id: UUID, plan_id: UUID, body: RevisionOnly, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.submit", body, lambda ctx: plans.submit(ctx, plan_id, body), "plan.author")


@router.post(W + "/plans/{plan_id}/reopen", response_model=CommandResult)
def reopen(workspace_id: UUID, plan_id: UUID, body: RevisionOnly, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.reopen", body, lambda ctx: plans.reopen(ctx, plan_id, body), "plan.author")


@router.post(W + "/plans/{plan_id}/approve", response_model=CommandResult)
def approve(workspace_id: UUID, plan_id: UUID, body: s.PlanApprove, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.approve", body, lambda ctx: plans.approve(ctx, plan_id, body), "plan.approve")


@router.post(W + "/plans/{plan_id}/disposition", response_model=CommandResult)
def disposition(workspace_id: UUID, plan_id: UUID, body: s.DispositionBody, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "plan.disposition", body, lambda ctx: plans.set_disposition(ctx, plan_id, body), "plan.approve")
