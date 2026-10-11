from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models.care import CareEvent, PlannedEvent, Task
from app.schemas import care as s
from app.schemas.commands import CommandResult
from app.services import care
from app.services.command_service import Ctx

router = APIRouter(tags=["care"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/tasks", response_model=list[s.TaskOut])
def list_tasks(patient_id: UUID | None = None, mine: bool = False, ctx: Ctx = Depends(reader)):
    rows = ctx.all(Task, *([Task.patient_id == patient_id] if patient_id else []))
    return [care.task_view(ctx, t) for t in rows if not mine or t.owner_id == ctx.account.id]


@router.post(W + "/plans/{plan_id}/tasks", response_model=CommandResult)
def instantiate(workspace_id: UUID, plan_id: UUID, body: s.TaskInstantiate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.instantiate", body, lambda ctx: care.instantiate(ctx, plan_id, body), "task.assign")


@router.post(W + "/tasks/{task_id}/update", response_model=CommandResult)
def update(workspace_id: UUID, task_id: UUID, body: s.TaskUpdate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.update", body, lambda ctx: care.update(ctx, task_id, body), "task.assign")


@router.post(W + "/tasks/{task_id}/send", response_model=CommandResult)
def send(workspace_id: UUID, task_id: UUID, body: s.TaskAction, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.send", body, lambda ctx: care.send(ctx, task_id, body), "task.assign")


@router.post(W + "/tasks/{task_id}/receive", response_model=CommandResult)
def receive(workspace_id: UUID, task_id: UUID, body: s.TaskAction, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.receive", body, lambda ctx: care.receive(ctx, task_id, body), "task.act")


@router.post(W + "/tasks/{task_id}/accept", response_model=CommandResult)
def accept(workspace_id: UUID, task_id: UUID, body: s.TaskAction, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.accept", body, lambda ctx: care.accept(ctx, task_id, body), "task.act")


@router.post(W + "/tasks/{task_id}/return", response_model=CommandResult)
def give_back(workspace_id: UUID, task_id: UUID, body: s.TaskReason, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.return", body, lambda ctx: care.give_back(ctx, task_id, body, "returned"), "task.act")


@router.post(W + "/tasks/{task_id}/block", response_model=CommandResult)
def block(workspace_id: UUID, task_id: UUID, body: s.TaskReason, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.block", body, lambda ctx: care.give_back(ctx, task_id, body, "blocked"), "task.act")


@router.post(W + "/tasks/{task_id}/complete", response_model=CommandResult)
def complete(workspace_id: UUID, task_id: UUID, body: s.TaskComplete, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.complete", body, lambda ctx: care.complete(ctx, task_id, body), "task.act")


@router.post(W + "/tasks/{task_id}/cancel", response_model=CommandResult)
def cancel(workspace_id: UUID, task_id: UUID, body: s.TaskReason, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "task.cancel", body, lambda ctx: care.cancel(ctx, task_id, body), "task.assign")


@router.get(W + "/patients/{patient_id}/planned-events", response_model=list[s.PlannedEventOut])
def planned_events(patient_id: UUID, ctx: Ctx = Depends(reader)):
    return ctx.all(PlannedEvent, PlannedEvent.patient_id == patient_id)


@router.post(W + "/patients/{patient_id}/planned-events", response_model=CommandResult)
def schedule_event(workspace_id: UUID, patient_id: UUID, body: s.PlannedEventCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "planned_event.schedule", body, lambda ctx: care.schedule_event(ctx, patient_id, body))


@router.get(W + "/patients/{patient_id}/care-events", response_model=list[s.CareEventOut])
def care_events(patient_id: UUID, ctx: Ctx = Depends(reader)):
    return ctx.all(CareEvent, CareEvent.patient_id == patient_id)


@router.post(W + "/patients/{patient_id}/care-events", response_model=CommandResult)
def record_care(workspace_id: UUID, patient_id: UUID, body: s.CareEventCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "care.record", body, lambda ctx: care.record_care(ctx, patient_id, body), "care.record")


@router.post(W + "/episodes/{episode_id}/transfer/request", response_model=CommandResult)
def request_transfer(workspace_id: UUID, episode_id: UUID, body: s.TransferRequest, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "episode.transfer_request", body, lambda ctx: care.request_transfer(ctx, episode_id, body), "transfer.request")


@router.post(W + "/episodes/{episode_id}/transfer/receive", response_model=CommandResult)
def receive_transfer(workspace_id: UUID, episode_id: UUID, body: s.TransferReceive, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "episode.transfer_receive", body, lambda ctx: care.receive_transfer(ctx, episode_id, body), "transfer.receive")
