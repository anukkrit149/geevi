"""Development fixture loader (U4).

Reads ONLY the approved input files named in the manifest. It never reads the gold annotations and
never fabricates reviews, approvals or signatures: loaded documents arrive unassociated and
unreviewed, exactly as if a coordinator had just received them.
"""
import base64
import json
from pathlib import Path
from types import SimpleNamespace

from app.core.config import get_settings
from app.core.errors import DomainError
from app.schemas.sources import DocumentUpload, PatientCreate, RelTime
from app.services import sources
from app.services.command_service import Ctx
from app.services.dev_seed import require_dev_mode


def _root() -> Path:
    return get_settings().fixtures_dir.resolve()


def manifest() -> dict:
    return json.loads((_root() / "manifest.json").read_text())


def scenario() -> dict:
    return json.loads((_root() / "scenario.json").read_text())


def input_path(relative: str) -> Path:
    """Resolve a manifest path; anything outside inputs/ (gold, arbitrary local paths) is refused."""
    inputs = (_root() / "inputs").resolve()
    path = (_root() / relative).resolve()
    if inputs not in path.parents or not path.is_file():
        raise DomainError(403, "fixture_path_rejected", "Only declared fixture input files can be loaded.")
    return path


def load(ctx: Ctx, level: str) -> dict:
    """level: 'patients' registers Meera and Arun; 'sources' also receives their baseline documents."""
    require_dev_mode()
    data = manifest()
    patients: dict[str, str] = {}
    import uuid
    for key, spec in data["patients"].items():
        result = sources.register_patient(ctx, PatientCreate(command_id=uuid.uuid4(), **spec))
        patients[key] = result["target"]["id"]
    ctx.db.flush()
    received = []
    if level == "sources":
        for entry in data["inputs"]:
            if entry["stage"] != "baseline":
                continue
            raw = input_path(entry["file"]).read_bytes()
            body = DocumentUpload(command_id=uuid.uuid4(), patient_id=patients[entry["patient"]], filename=Path(entry["file"]).name,
                                  media_type=entry["media_type"], content_base64=base64.b64encode(raw).decode(), doc_kind=entry["doc_kind"],
                                  title=entry["title"], issuer=entry["issuer"], accession=entry["accession"],
                                  received_time=RelTime(**entry["received_time"]))
            parsed = sources.prepare_upload(body.content_base64, body.media_type, body.doc_kind)
            received.append(sources.receive_document(ctx, body, parsed)["target"]["id"])
            ctx.db.flush()
    return {"patients": patients, "documents": received}


def loader_context(db, account, workspace) -> Ctx:
    """Records are attributed to the fixture loader run by the invoking development account."""
    actor = SimpleNamespace(id=account.id, display_name=f"Fixture loader (run by {account.display_name})", username=account.username)
    workspace.sequence += 1
    return Ctx(db, actor, workspace, workspace.active_container_id, frozenset({"patient.register", "source.import"}), seq=workspace.sequence)

