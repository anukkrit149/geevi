"""Development-only helpers. Every route refuses to run unless GEEVI_DEV_MODE=true."""
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_account
from app.core.errors import not_permitted
from app.db.session import get_db
from app.models.identity import Account, WorkspaceGrant
from app.services import fixture_loader
from app.services.dev_seed import require_dev_mode
from app.services.workspaces import create_workspace

router = APIRouter(tags=["development"])


class DemoWorkspaceCreate(BaseModel):
    name: str
    load: Literal["none", "patients", "sources"] = "none"


class DemoWorkspaceOut(BaseModel):
    workspace_id: UUID
    patients: dict[str, str]
    documents: list[str]


@router.post("/dev/workspaces", response_model=DemoWorkspaceOut)
def create_demo_workspace(body: DemoWorkspaceCreate, account: Account = Depends(current_account), db: Session = Depends(get_db)):
    """Isolated fictional workspace, optionally with unreviewed fixture inputs. No approvals are created."""
    require_dev_mode()
    grants = db.scalars(select(WorkspaceGrant).where(WorkspaceGrant.account_id == account.id)).all()
    if not any("workspace.manage" in g.capabilities for g in grants):
        raise not_permitted("Only the development operator can create demo workspaces.")
    ws = create_workspace(db, body.name.strip() or "Demo workspace", origin="demo_seed", created_by=account.id)
    loaded = {"patients": {}, "documents": []}
    if body.load != "none":
        loaded = fixture_loader.load(fixture_loader.loader_context(db, account, ws), body.load)
    db.commit()
    return {"workspace_id": ws.id, **loaded}


@router.get("/dev/scenario", response_model=dict[str, Any])
def get_scenario(account: Account = Depends(current_account)):
    """Authored fictional scenario text (inputs only; never the test gold) to prefill demo forms."""
    require_dev_mode()
    return fixture_loader.scenario()
