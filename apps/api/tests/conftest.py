"""Tests run against a dedicated disposable PostgreSQL database (never SQLite, never a shared database)."""
import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command

API_ROOT = Path(__file__).resolve().parents[1]
ADMIN_URL = os.environ.get("GEEVI_TEST_ADMIN_URL", "postgresql+psycopg://geevi@127.0.0.1:5433/postgres")
PASSWORDS = {u: f"test-{u}-pw" for u in ("rao", "sen", "mira", "isha", "operator")}


@pytest.fixture(scope="session", autouse=True)
def database():
    name = f"geevi_test_{uuid.uuid4().hex[:10]}"
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = ADMIN_URL.rsplit("/", 1)[0] + "/" + name
    os.environ["GEEVI_DATABASE_URL"] = url
    os.environ["GEEVI_DEV_MODE"] = "true"
    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker
    for cached in (get_settings, get_engine, get_sessionmaker):
        cached.cache_clear()
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    from app.services.dev_seed import seed_accounts
    with get_sessionmaker()() as db:
        seed_accounts(db, PASSWORDS)
        db.commit()
    yield url
    get_engine().dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture()
def db():
    from app.db.session import get_sessionmaker
    with get_sessionmaker()() as session:
        yield session


class Api:
    """Authenticated HTTP client for one development account (real sessions, cookies and CSRF)."""

    def __init__(self, username: str | None = None):
        from fastapi.testclient import TestClient

        from app.main import app
        self.http = TestClient(app, raise_server_exceptions=False)
        self.csrf = None
        self.username = username
        if username:
            r = self.http.post("/api/v1/session", json={"username": username, "password": PASSWORDS[username]})
            assert r.status_code == 200, r.text
            self.csrf = r.json()["csrf_token"]
            self.account_id = r.json()["account"]["id"]

    def headers(self, extra=None):
        return {**({"X-CSRF-Token": self.csrf} if self.csrf else {}), **(extra or {})}

    def get(self, path, expect=200, **kw):
        r = self.http.get("/api/v1" + path, **kw)
        assert r.status_code == expect, f"GET {path} -> {r.status_code} {r.text[:600]}"
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else r

    def post(self, path, body=None, expect=200, command_id=None, headers=None):
        payload = {"command_id": command_id or str(uuid.uuid4()), **(body or {})}
        r = self.http.post("/api/v1" + path, json=payload, headers=self.headers(headers))
        assert r.status_code == expect, f"POST {path} -> {r.status_code} (expected {expect}) {r.text[:800]}"
        return r.json()

    def fail(self, path, body=None, code=None, status=None, **kw):
        payload = {"command_id": kw.pop("command_id", None) or str(uuid.uuid4()), **(body or {})}
        r = self.http.post("/api/v1" + path, json=payload, headers=self.headers(kw.pop("headers", None)))
        assert r.status_code >= 400, f"POST {path} unexpectedly succeeded: {r.text[:400]}"
        error = r.json()["error"]
        if code:
            assert error["code"] == code, f"expected {code}, got {error}"
        if status:
            assert r.status_code == status, f"expected {status}, got {r.status_code} {error}"
        return error


@pytest.fixture()
def api():
    cache: dict[str, Api] = {}

    def get(username: str | None) -> Api:
        if username not in cache:
            cache[username] = Api(username)
        return cache[username]
    return get


@pytest.fixture()
def workspace(db):
    from app.services.workspaces import create_workspace
    ws = create_workspace(db, f"Test workspace {uuid.uuid4().hex[:6]}")
    db.commit()
    return str(ws.id)


@pytest.fixture()
def fresh_database(database):
    """A second, completely empty PostgreSQL database with only migrations and development accounts."""
    from contextlib import contextmanager

    from app.core.config import get_settings
    from app.db.session import get_engine, get_sessionmaker

    @contextmanager
    def switch():
        name = f"geevi_restore_{uuid.uuid4().hex[:10]}"
        admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        get_engine().dispose()
        os.environ["GEEVI_DATABASE_URL"] = ADMIN_URL.rsplit("/", 1)[0] + "/" + name
        for cached in (get_settings, get_engine, get_sessionmaker):
            cached.cache_clear()
        try:
            cfg = Config(str(API_ROOT / "alembic.ini"))
            cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
            command.upgrade(cfg, "head")
            from app.services.dev_seed import seed_accounts
            from app.services.workspaces import create_workspace
            with get_sessionmaker()() as session:
                seed_accounts(session, PASSWORDS)
                ws = create_workspace(session, "Restored workspace")
                session.commit()
                workspace_id = str(ws.id)
            yield workspace_id, Api
        finally:
            get_engine().dispose()
            os.environ["GEEVI_DATABASE_URL"] = database
            for cached in (get_settings, get_engine, get_sessionmaker):
                cached.cache_clear()
            with admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            admin.dispose()
    return switch
