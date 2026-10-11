from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.policy import DEV_ACCOUNTS
from app.models.identity import Account, Workspace, WorkspaceContainer, WorkspaceGrant


def create_workspace(db: Session, name: str, *, origin: str = "created", created_by=None, extra_grants: dict | None = None) -> Workspace:
    """New workspace with an empty active container and the fixed development grant template."""
    ws = Workspace(name=name, data_label="fictional")
    db.add(ws)
    db.flush()
    container = WorkspaceContainer(workspace_id=ws.id, status="active", origin=origin, created_by=created_by,
                                   provenance={"origin": origin})
    db.add(container)
    db.flush()
    ws.active_container_id = container.id
    for account in db.scalars(select(Account).where(Account.username.in_(DEV_ACCOUNTS))):
        db.add(WorkspaceGrant(workspace_id=ws.id, account_id=account.id,
                              capabilities=list(DEV_ACCOUNTS[account.username]["capabilities"])))
    for account_id, caps in (extra_grants or {}).items():
        db.add(WorkspaceGrant(workspace_id=ws.id, account_id=account_id, capabilities=caps))
    db.flush()
    return ws
