from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import check_origin, current_account, current_session
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.policy import DEV_ACCOUNTS
from app.core.security import new_token, token_hash, verify_password
from app.db.session import get_db
from app.models.identity import Account, AuthSession, Workspace, WorkspaceGrant
from app.schemas.identity import DevIdentity, LoginRequest, SessionOut

router = APIRouter(tags=["session"])


def _session_out(db: Session, account: Account, session: AuthSession) -> dict:
    rows = db.execute(select(Workspace, WorkspaceGrant).join(WorkspaceGrant, WorkspaceGrant.workspace_id == Workspace.id)
                      .where(WorkspaceGrant.account_id == account.id).order_by(Workspace.created_at)).all()
    return {"account": account, "csrf_token": session.csrf_token,
            "workspaces": [{"id": w.id, "name": w.name, "data_label": w.data_label, "capabilities": g.capabilities,
                            "sequence": w.sequence, "active_container_id": w.active_container_id} for w, g in rows]}


@router.post("/session", response_model=SessionOut)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    check_origin(request)
    settings = get_settings()
    account = db.scalar(select(Account).where(Account.username == body.username.strip().lower()))
    if account is None or not account.active or not verify_password(account.password_hash, body.password):
        raise DomainError(401, "invalid_credentials", "The username or password is not correct.")
    token = new_token()
    session = AuthSession(account_id=account.id, token_hash=token_hash(token), csrf_token=new_token(),
                          expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours))
    db.add(session)
    db.commit()
    response.set_cookie(settings.cookie_name, token, httponly=True, samesite="strict", secure=settings.cookie_secure,
                        max_age=settings.session_hours * 3600, path="/")
    response.headers["Cache-Control"] = "no-store"
    return _session_out(db, account, session)


@router.get("/session", response_model=SessionOut)
def read_session(session: AuthSession = Depends(current_session), account: Account = Depends(current_account),
                 db: Session = Depends(get_db)):
    return _session_out(db, account, session)


@router.delete("/session", status_code=204)
def logout(response: Response, session: AuthSession = Depends(current_session), db: Session = Depends(get_db)):
    session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie(get_settings().cookie_name, path="/")


@router.get("/dev/identities", response_model=list[DevIdentity])
def dev_identities(db: Session = Depends(get_db)):
    """Names of seeded fictional identities for the sign-in page. Only available in development mode."""
    if not get_settings().dev_mode:
        raise DomainError(404, "not_found", "Development identities are disabled outside development mode.")
    accounts = {a.username: a for a in db.scalars(select(Account).where(Account.is_development.is_(True)))}
    return [{"username": u, "display_name": accounts[u].display_name, "role_title": accounts[u].role_title}
            for u in DEV_ACCOUNTS if u in accounts]
