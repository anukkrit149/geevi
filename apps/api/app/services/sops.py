"""U6 departmental SOP versions: operational steps that become task specifications, never orders."""
from app.core.errors import blocked
from app.models.department import ProtocolVersion, SopVersion
from app.services import publication, reviews
from app.services.command_service import Ctx


def _validate(ctx: Ctx, record: SopVersion) -> None:
    ids = [s.get("id") for s in record.steps]
    if not ids or len(set(ids)) != len(ids):
        raise blocked("invalid_steps", "An SOP needs role-owned steps with unique identifiers.", target=("sop_version", record.id))
    for step in record.steps:
        if not all((step.get(k) or "").strip() for k in ("title", "role", "expected_evidence")) or not set(step.get("depends_on") or []) <= set(ids):
            raise blocked("invalid_steps", f"Step {step.get('id')}: title, role, expected completion evidence and valid dependencies are required.",
                          target=("sop_version", record.id))
    if record.protocol_version_id and ctx.find(ProtocolVersion, record.protocol_version_id) is None:
        raise blocked("invalid_association", "The related protocol version does not exist.", target=("sop_version", record.id))


KIND = publication.DocKind(SopVersion, ("purpose", "steps", "escalation", "protocol_version_id"), _validate)
reviews.FINALIZERS["sop_version"] = publication.finalizer(KIND)


def values(body) -> dict:
    return {"title": body.title.strip(), "purpose": body.purpose.strip(), "escalation": body.escalation.strip(),
            "steps": [s.model_dump(mode="json") for s in body.steps], "protocol_version_id": body.protocol_version_id}
