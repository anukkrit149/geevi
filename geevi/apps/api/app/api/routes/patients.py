from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import Commander, commander, reader
from app.models import sources as m
from app.schemas import sources as s
from app.schemas.commands import CommandResult
from app.services import profile, sources
from app.services.command_service import Ctx

router = APIRouter(tags=["patients"])
W = "/workspaces/{workspace_id}"


@router.get(W + "/patients", response_model=list[s.PatientDetail])
def list_patients(ctx: Ctx = Depends(reader)):
    return [{"patient": p, "identifiers": sources.identifiers_of(ctx, "patient", p.id),
             "episodes": ctx.all(m.Episode, m.Episode.patient_id == p.id)} for p in ctx.all(m.Patient)]


@router.post(W + "/patients", response_model=CommandResult)
def register_patient(workspace_id: UUID, body: s.PatientCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "patient.register", body, lambda ctx: sources.register_patient(ctx, body), "patient.register")


@router.get(W + "/patients/{patient_id}", response_model=s.PatientDetail)
def get_patient(patient_id: UUID, ctx: Ctx = Depends(reader)):
    patient = ctx.get(m.Patient, patient_id)
    return {"patient": patient, "identifiers": sources.identifiers_of(ctx, "patient", patient.id),
            "episodes": ctx.all(m.Episode, m.Episode.patient_id == patient.id)}


@router.get(W + "/patients/{patient_id}/profile", response_model=s.ProfileOut)
def get_profile(patient_id: UUID, as_of_seq: int | None = None, ctx: Ctx = Depends(reader)):
    return profile.project(ctx, patient_id, as_of_seq)


@router.get(W + "/patients/{patient_id}/snapshots", response_model=list[s.SnapshotOut])
def list_snapshots(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return ctx.all(m.ProfileSnapshot, m.ProfileSnapshot.patient_id == patient_id)


@router.get(W + "/patients/{patient_id}/assessments", response_model=list[s.AssessmentOut])
def list_assessments(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return ctx.all(m.ClinicalAssessment, m.ClinicalAssessment.patient_id == patient_id)


@router.post(W + "/patients/{patient_id}/assessments", response_model=CommandResult)
def record_assessment(workspace_id: UUID, patient_id: UUID, body: s.AssessmentCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "assessment.record", body, lambda ctx: sources.record_assessment(ctx, patient_id, body), "clinical.assess")


@router.get(W + "/patients/{patient_id}/discussions", response_model=list[s.DiscussionOut])
def list_discussions(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return ctx.all(m.PatientDiscussion, m.PatientDiscussion.patient_id == patient_id)


@router.post(W + "/patients/{patient_id}/discussions", response_model=CommandResult)
def record_discussion(workspace_id: UUID, patient_id: UUID, body: s.DiscussionCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "discussion.record", body, lambda ctx: sources.record_discussion(ctx, patient_id, body), "discussion.record")


@router.get(W + "/patients/{patient_id}/expected-inputs", response_model=list[s.ExpectedInputOut])
def list_expected_inputs(patient_id: UUID, ctx: Ctx = Depends(reader)):
    ctx.get(m.Patient, patient_id)
    return ctx.all(m.ExpectedInput, m.ExpectedInput.patient_id == patient_id)


@router.post(W + "/expected-inputs", response_model=CommandResult)
def create_expected_input(workspace_id: UUID, body: s.ExpectedInputCreate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "expected_input.create", body, lambda ctx: sources.create_expected_input(ctx, body), "source.import")


@router.post(W + "/expected-inputs/{item_id}/update", response_model=CommandResult)
def update_expected_input(workspace_id: UUID, item_id: UUID, body: s.ExpectedInputUpdate, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "expected_input.update", body, lambda ctx: sources.update_expected_input(ctx, item_id, body), "source.import")


@router.post(W + "/expected-inputs/{item_id}/link-report", response_model=CommandResult)
def link_expected_input(workspace_id: UUID, item_id: UUID, body: s.ExpectedInputLink, cmd: Commander = Depends(commander)):
    return cmd.run(workspace_id, "expected_input.link", body, lambda ctx: sources.link_expected_input(ctx, item_id, body), "source.import")
