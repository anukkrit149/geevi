"""U1: idempotent commands, entity revisions and the shared workspace lock."""
import threading
import uuid

from app.services import command_service


def test_identical_command_returns_one_receipt(api, workspace):
    rao = api("rao")
    cid = str(uuid.uuid4())
    first = rao.post(f"/workspaces/{workspace}/notes", {"text": "Bring referral folder"}, command_id=cid)
    again = rao.post(f"/workspaces/{workspace}/notes", {"text": "Bring referral folder"}, command_id=cid)
    assert first["replayed"] is False and again["replayed"] is True
    assert again["target"] == first["target"]
    assert len(rao.get(f"/workspaces/{workspace}/notes")) == 1


def test_same_command_id_with_changed_payload_or_actor_fails(api, workspace):
    cid = str(uuid.uuid4())
    api("rao").post(f"/workspaces/{workspace}/notes", {"text": "Original"}, command_id=cid)
    api("rao").fail(f"/workspaces/{workspace}/notes", {"text": "Changed"}, code="command_id_conflict", status=409, command_id=cid)
    api("mira").fail(f"/workspaces/{workspace}/notes", {"text": "Original"}, code="command_id_conflict", status=409, command_id=cid)
    assert [n["text"] for n in api("rao").get(f"/workspaces/{workspace}/notes")] == ["Original"]


def test_distinct_entities_survive_and_same_entity_conflicts(api, workspace):
    rao, mira = api("rao"), api("mira")
    a = rao.post(f"/workspaces/{workspace}/notes", {"text": "A"})["target"]
    b = rao.post(f"/workspaces/{workspace}/notes", {"text": "B"})["target"]
    # Two clients edit different notes loaded at the same time: both survive.
    rao.post(f"/workspaces/{workspace}/notes/{a['id']}/update", {"expected_revision": 1, "text": "A by Rao"})
    mira.post(f"/workspaces/{workspace}/notes/{b['id']}/update", {"expected_revision": 1, "text": "B by Mira"})
    assert sorted(n["text"] for n in rao.get(f"/workspaces/{workspace}/notes")) == ["A by Rao", "B by Mira"]
    # A stale edit of the same note is rejected with the current revision.
    error = mira.fail(f"/workspaces/{workspace}/notes/{a['id']}/update", {"expected_revision": 1, "text": "lost?"},
                      code="stale_target", status=409)
    assert error["details"] == {"expected_revision": 1, "current_revision": 2}
    assert error["next_action"]


def test_workspace_lock_serializes_concurrent_writers(api, workspace, monkeypatch):
    """A second writer cannot read or check dependencies until the first transaction ends."""
    rao, mira = api("rao"), api("mira")
    first_at_commit, release, order = threading.Event(), threading.Event(), []
    original = command_service._before_commit

    def gate(ctx):
        original(ctx)
        if ctx.account.username == "rao":
            first_at_commit.set()
            assert release.wait(10)
        order.append(ctx.account.username)

    monkeypatch.setattr(command_service, "_before_commit", gate)
    t1 = threading.Thread(target=lambda: rao.post(f"/workspaces/{workspace}/notes", {"text": "first"}))
    t1.start()
    assert first_at_commit.wait(10)
    t2 = threading.Thread(target=lambda: mira.post(f"/workspaces/{workspace}/notes", {"text": "second"}))
    t2.start()
    t2.join(0.6)
    assert t2.is_alive() and order == [], "second writer must wait on the workspace row lock"
    release.set()
    t1.join(10)
    t2.join(10)
    assert order == ["rao", "mira"]
    notes = rao.get(f"/workspaces/{workspace}/notes")
    assert [n["recorded_seq"] for n in notes] == [1, 2]


def test_aborted_commit_leaves_nothing_and_same_id_retry_resolves_unknown_outcome(api, workspace, monkeypatch):
    rao = api("rao")
    cid = str(uuid.uuid4())

    def explode(ctx):
        raise RuntimeError("simulated connection loss before commit")

    monkeypatch.setattr(command_service, "_before_commit", explode)
    r = rao.http.post(f"/api/v1/workspaces/{workspace}/notes", json={"command_id": cid, "text": "x"}, headers=rao.headers())
    assert r.status_code == 500
    monkeypatch.undo()
    assert rao.get(f"/workspaces/{workspace}/notes") == []
    assert rao.get(f"/workspaces/{workspace}/audit") == []
    # The client does not know the outcome: retrying the SAME command id applies it exactly once.
    done = rao.post(f"/workspaces/{workspace}/notes", {"text": "x"}, command_id=cid)
    assert done["replayed"] is False
    assert rao.post(f"/workspaces/{workspace}/notes", {"text": "x"}, command_id=cid)["replayed"] is True
    assert len(rao.get(f"/workspaces/{workspace}/notes")) == 1
