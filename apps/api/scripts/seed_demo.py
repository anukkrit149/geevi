"""Controlled demo setup: fictional development identities and one demo workspace.

Creates accounts and (optionally) unreviewed fixture inputs. It never creates reviews, approvals,
publications or signatures; those are performed by signed-in accounts through the API/UI.

Usage (development only):
  GEEVI_DEV_MODE=true uv run --project apps/api python apps/api/scripts/seed_demo.py [--load none|patients|sources] [--name NAME]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.models.identity import Workspace  # noqa: E402
from app.services import fixture_loader  # noqa: E402
from app.services.dev_seed import load_or_create_credentials, require_dev_mode, seed_accounts  # noqa: E402
from app.services.workspaces import create_workspace  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", choices=["none", "patients", "sources"], default="none")
    parser.add_argument("--name", default="Geevi demo department (fictional)")
    args = parser.parse_args()
    require_dev_mode()
    settings = get_settings()
    credentials = load_or_create_credentials(settings.credentials_file)
    with get_sessionmaker()() as db:
        accounts = seed_accounts(db, credentials)
        ws = db.scalar(select(Workspace).where(Workspace.name == args.name))
        if ws is None:
            ws = create_workspace(db, args.name, origin="demo_seed", created_by=accounts["operator"].id)
            if args.load != "none":
                fixture_loader.load(fixture_loader.loader_context(db, accounts["operator"], ws), args.load)
            print(f"created workspace '{args.name}' ({ws.id})")
        else:
            print(f"workspace '{args.name}' already exists ({ws.id}); left unchanged")
        db.commit()
    print(f"development identities: {', '.join(credentials)}")
    print(f"fictional passwords are stored in the ignored local file {settings.credentials_file}")


if __name__ == "__main__":
    main()
