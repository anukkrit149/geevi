from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models.exceptions import ExceptionRequest
from app.schemas import exceptions as s
from app.schemas.commands import CommandResult
from app.schemas.reviews import RevisionOnly
from app.services import exceptions
from app.services.command_service import Ctx

router = APIRouter(tags=["exceptions"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/exceptions", response_model=list[s.ExceptionOut])
def list_requests(patient_id: UUID | None = None, ctx: Ctx = Depends(reader)):
    where = [ExceptionRequest.patient_id == patient_id] if patient_id else []
    return [exceptions.view(ctx, e) for e in ctx.all(ExceptionRequest, *where)]


@router.post(W + "/patients/{patient_id}/exceptions", response_model=CommandResult)
def request(workspace_id: UUID, patient_id: UUID, body: s.ExceptionRequestBody, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "exception.request", body, lambda ctx: exceptions.request(ctx, patient_id, body), "exception.request")


@router.post(W + "/exceptions/{request_id}/revise", response_model=CommandResult)
def revise(workspace_id: UUID, request_id: UUID, body: s.ExceptionRevise, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "exception.revise", body, lambda ctx: exceptions.revise(ctx, request_id, body), "exception.request")


@router.post(W + "/exceptions/{request_id}/decide", response_model=CommandResult)
def decide(workspace_id: UUID, request_id: UUID, body: s.ExceptionDecide, cmd: Commander = Depends(commander)):
    # The capability depends on the exception type and is checked inside the handler against the server grant.
    return cmd.run(workspace_id, "exception.decide", body, lambda ctx: exceptions.decide(ctx, request_id, body))


@router.post(W + "/exceptions/{request_id}/record-expiry", response_model=CommandResult)
def record_expiry(workspace_id: UUID, request_id: UUID, body: RevisionOnly, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "exception.expire", body, lambda ctx: exceptions.record_expiry(ctx, request_id, body), "records.read")


@router.post(W + "/exceptions/{request_id}/withdraw", response_model=CommandResult)
def withdraw(workspace_id: UUID, request_id: UUID, body: s.ExceptionWithdraw, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "exception.withdraw", body, lambda ctx: exceptions.withdraw(ctx, request_id, body), "exception.request")
