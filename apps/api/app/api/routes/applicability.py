from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models import sources as m
from app.models.reviews import ApplicabilityReview
from app.schemas import reviews as s
from app.schemas.commands import CommandResult
from app.services import applicability
from app.services.command_service import Ctx

router = APIRouter(tags=["applicability"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/patients/{patient_id}/applicability", response_model=list[s.ApplicabilityOut])
def list_reviews(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return ctx.all(ApplicabilityReview, ApplicabilityReview.patient_id == patient_id)


@router.post(W + "/patients/{patient_id}/applicability", response_model=CommandResult)
def start(workspace_id: UUID, patient_id: UUID, body: s.ApplicabilityStart, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "applicability.start", body, lambda ctx: applicability.start(ctx, patient_id, body), "clinical.assess")


@router.post(W + "/applicability/{review_id}/save", response_model=CommandResult)
def save(workspace_id: UUID, review_id: UUID, body: s.ApplicabilitySave, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "applicability.save", body, lambda ctx: applicability.save(ctx, review_id, body), "clinical.assess")


@router.post(W + "/applicability/{review_id}/accept", response_model=CommandResult)
def accept(workspace_id: UUID, review_id: UUID, body: s.RevisionOnly, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "applicability.accept", body, lambda ctx: applicability.accept(ctx, review_id, body), "clinical.assess")
