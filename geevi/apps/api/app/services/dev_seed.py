"""Development-only seeding of fictional identities. Refuses to run outside explicit dev mode."""
import json
import secrets
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.policy import DEV_ACCOUNTS
from app.core.security import hash_password
from app.models.identity import Account


def require_dev_mode() -> None:
    if not get_settings().dev_mode:
        raise DomainError(403, "dev_mode_required", "Demo seeding is disabled unless GEEVI_DEV_MODE=true is set explicitly.")


def load_or_create_credentials(path: Path) -> dict[str, str]:
    """Passwords live only in an ignored local file; they are generated, never committed."""
    credentials = json.loads(path.read_text()) if path.exists() else {}
    changed = False
    for username in DEV_ACCOUNTS:
        if username not in credentials:
            credentials[username] = secrets.token_urlsafe(12)
            changed = True
    if changed:
        path.write_text(json.dumps(credentials, indent=2) + "\n")
        path.chmod(0o600)
    return credentials


def seed_accounts(db: Session, passwords: dict[str, str]) -> dict[str, Account]:
    require_dev_mode()
    accounts = {}
    for username, spec in DEV_ACCOUNTS.items():
        account = db.scalar(select(Account).where(Account.username == username))
        if account is None:
            account = Account(username=username, is_development=True, active=True, password_hash="")
            db.add(account)
        account.display_name, account.role_title = spec["display_name"], spec["role_title"]
        account.password_hash = hash_password(passwords[username])
        accounts[username] = account
    db.flush()
    return accounts
