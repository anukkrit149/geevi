from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.security import token_hash
from app.db.session import get_db
from app.models.identity import Account, AuthSession
from app.services.command_service import CommandBase, Ctx, read_context, run_command

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def check_origin(request: Request) -> None:
    """Writes must come from the documented same-origin frontend (or a non-browser client)."""
    origin = request.headers.get("origin")
    settings = get_settings()
    if not origin or origin in settings.allowed_origins:
        return
    if settings.same_origin_writes:
        # A browser cannot forge Origin or Host on a cross-site request, so equality proves same-origin.
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
        if host and urlsplit(origin).netloc == host:
            return
    raise DomainError(403, "origin_rejected", "This request origin is not allowed to perform writes.")


def current_session(request: Request, db: Session = Depends(get_db)) -> AuthSession:
    token = request.cookies.get(get_settings().cookie_name)
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token))) if token else None
    if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise DomainError(401, "not_authenticated", "Sign in with a development account to continue.",
                          next_action="Sign in again.")
    if request.method in UNSAFE:
        check_origin(request)
        if request.headers.get("x-csrf-token") != session.csrf_token:
            raise DomainError(403, "csrf_rejected", "The request is missing a valid CSRF token for this session.",
                              next_action="Reload the page and retry the same action.")
    return session


def current_account(session: AuthSession = Depends(current_session), db: Session = Depends(get_db)) -> Account:
    account = db.get(Account, session.account_id)
    if account is None or not account.active:
        raise DomainError(401, "not_authenticated", "This development account is not active.")
    return account


def reader(workspace_id: UUID, account: Account = Depends(current_account), db: Session = Depends(get_db)) -> Ctx:
    """Read context for clinical/research records: requires the records.read grant in this workspace."""
    ctx = read_context(db, account, workspace_id)
    ctx.require("records.read", ("workspace", workspace_id))
    return ctx


def member(workspace_id: UUID, account: Account = Depends(current_account), db: Session = Depends(get_db)) -> Ctx:
    """Workspace membership without record-read scope (used by operator import/export views)."""
    return read_context(db, account, workspace_id)


@dataclass
class Commander:
    request: Request
    db: Session
    account: Account

    def run(self, workspace_id: UUID, action: str, body: CommandBase, handler: Callable[[Ctx], dict[str, Any]],
            capability: str | None = None) -> dict[str, Any]:
        return run_command(self.db, self.account, workspace_id, action, body, self.request.url.path, handler, capability)


def commander(request: Request, account: Account = Depends(current_account), db: Session = Depends(get_db)) -> Commander:
    return Commander(request, db, account)
