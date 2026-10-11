"""U1: sessions, CSRF/Origin, capability and workspace scope are enforced below the UI."""
import uuid

from app.services.workspaces import create_workspace


def test_unauthenticated_requests_fail(api, workspace):
    anon = api(None)
    assert anon.get(f"/workspaces/{workspace}/notes", expect=401)["error"]["code"] == "not_authenticated"
    anon.fail(f"/workspaces/{workspace}/notes", {"text": "x"}, code="not_authenticated", status=401)
    assert anon.http.post("/api/v1/session", json={"username": "rao", "password": "wrong"}).status_code == 401


def test_csrf_and_origin_are_required_for_writes(api, workspace):
    rao = api("rao")
    body = {"command_id": str(uuid.uuid4()), "text": "x"}
    assert rao.http.post(f"/api/v1/workspaces/{workspace}/notes", json=body).json()["error"]["code"] == "csrf_rejected"
    r = rao.http.post(f"/api/v1/workspaces/{workspace}/notes", json=body, headers=rao.headers({"Origin": "https://evil.example"}))
    assert r.status_code == 403 and r.json()["error"]["code"] == "origin_rejected"
    assert rao.get(f"/workspaces/{workspace}/notes") == []


def test_client_actor_headers_and_fields_grant_nothing(api, workspace):
    operator = api("operator")
    forged = {"X-Actor": "rao", "X-Role": "oncologist", "X-User-Id": api("rao").account_id}
    error = operator.fail(f"/workspaces/{workspace}/notes", {"text": "x", "actor": "rao", "role": "oncologist"},
                          code="actor_not_permitted", status=403, headers=forged)
    assert error["details"]["required_capability"] == "note.write"
    # The operator has no clinical record read scope either.
    assert operator.get(f"/workspaces/{workspace}/notes", expect=403)["error"]["code"] == "actor_not_permitted"


def test_cross_workspace_access_fails(api, workspace, db):
    other = create_workspace(db, "No grants here")
    from sqlalchemy import delete

    from app.models.identity import WorkspaceGrant
    db.execute(delete(WorkspaceGrant).where(WorkspaceGrant.workspace_id == other.id))
    db.commit()
    rao = api("rao")
    assert rao.get(f"/workspaces/{other.id}/notes", expect=403)["error"]["code"] == "actor_not_permitted"
    rao.fail(f"/workspaces/{other.id}/notes", {"text": "x"}, code="actor_not_permitted", status=403)
    note = rao.post(f"/workspaces/{workspace}/notes", {"text": "mine"})["target"]
    # A record id from one workspace cannot be addressed through another workspace.
    second = create_workspace(db, "Second")
    db.commit()
    rao.fail(f"/workspaces/{second.id}/notes/{note['id']}/update", {"expected_revision": 1, "text": "x"}, code="not_found", status=404)


def test_logout_revokes_the_server_session(api, workspace):
    from tests.conftest import Api
    mira = Api("mira")
    assert mira.get("/session")["account"]["username"] == "mira"
    assert mira.http.delete("/api/v1/session", headers=mira.headers()).status_code == 204
    assert mira.get("/session", expect=401)["error"]["code"] == "not_authenticated"


def test_session_reports_development_identity_and_no_secrets(api):
    session = api("sen").get("/session")
    assert session["account"]["is_development"] is True
    assert "development identity" in session["identity_notice"].lower()
    assert "password" not in str(session).lower()
    names = [i["username"] for i in api(None).get("/dev/identities")]
    assert names == ["rao", "sen", "mira", "isha", "operator"]


def test_same_origin_writes_accept_only_the_host_the_request_was_sent_to(api, workspace, monkeypatch):
    from app.core.config import get_settings
    rao = api("rao")
    post = lambda headers: rao.http.post(f"/api/v1/workspaces/{workspace}/notes", json={"command_id": str(uuid.uuid4()), "text": "x"},  # noqa: E731
                                         headers=rao.headers(headers))
    public = {"Origin": "https://geevi.example.app", "X-Forwarded-Host": "geevi.example.app"}
    assert post(public).json()["error"]["code"] == "origin_rejected"  # off by default
    monkeypatch.setenv("GEEVI_SAME_ORIGIN_WRITES", "true")
    get_settings.cache_clear()
    try:
        assert post(public).status_code == 200
        assert post({"Origin": "https://evil.example", "X-Forwarded-Host": "geevi.example.app"}).json()["error"]["code"] == "origin_rejected"
        assert post({"Origin": "https://geevi.example.app.evil.example", "X-Forwarded-Host": "geevi.example.app"}).status_code == 403
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_hosted_database_urls_are_normalised_to_the_psycopg_driver():
    from app.core.config import Settings
    assert Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
    assert Settings(database_url="postgresql+psycopg://u@h/db").database_url == "postgresql+psycopg://u@h/db"
