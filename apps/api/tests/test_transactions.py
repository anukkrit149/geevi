"""U1: transaction proof on real PostgreSQL with domain commands (tasks and signatures)."""
import threading
import uuid

from app.services import command_service
from tests.helpers import W, draft_plan, make_tasks, meera_planned, meera_ready, submit_plan


def test_two_clients_update_distinct_tasks_without_loss_and_same_task_conflicts(api, workspace):
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"], owner="isha")
    a, b = tasks["STEP-CONFIRM-VENUE"], tasks["STEP-FOLLOWUP"]
    mira, rao = api("mira"), api("rao")
    results = {}

    def edit(client, key, task, note):
        results[key] = client.http.post(f"/api/v1{W(workspace)}/tasks/{task['id']}/update", headers=client.headers(),
                                        json={"command_id": str(uuid.uuid4()), "expected_revision": task["revision"], "note": note})

    threads = [threading.Thread(target=edit, args=(mira, "a", a, "Mira's note on task A")), threading.Thread(target=edit, args=(rao, "b", b, "Rao's note on task B"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert results["a"].status_code == 200 and results["b"].status_code == 200
    now = {t["sop_step_id"]: t for t in api("mira").get(f"{W(workspace)}/tasks")}
    assert now["STEP-CONFIRM-VENUE"]["note"] == "Mira's note on task A" and now["STEP-FOLLOWUP"]["note"] == "Rao's note on task B"
    # Two edits of the SAME task loaded at the same revision: exactly one wins, the other gets a typed conflict.
    same = now["STEP-PREP-VISIT"]
    threads = [threading.Thread(target=edit, args=(mira, "x", same, "first")), threading.Thread(target=edit, args=(rao, "y", same, "second"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    codes = sorted(r.status_code for r in (results["x"], results["y"]))
    assert codes == [200, 409]
    loser = results["x"] if results["x"].status_code == 409 else results["y"]
    assert loser.json()["error"]["code"] == "stale_target" and loser.json()["error"]["details"]["current_revision"] == same["revision"] + 1


def test_failed_signature_commit_leaves_no_partial_approval_and_same_id_retry_resolves_it(api, workspace, monkeypatch):
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    submit_plan(api, workspace, plan_id)
    view = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    body = {"expected_revision": view["plan"]["revision"], "packet_id": view["packet"]["id"], "digest": view["packet"]["target_digest"]}
    command = str(uuid.uuid4())

    def explode(ctx):
        from sqlalchemy.exc import OperationalError
        raise OperationalError("COMMIT", {}, Exception("simulated connection loss at commit"))

    monkeypatch.setattr(command_service, "_before_commit", explode)
    rao = api("rao")
    failed = rao.http.post(f"/api/v1{W(workspace)}/plans/{plan_id}/approve", json={"command_id": command, **body}, headers=rao.headers())
    assert failed.status_code == 500 and failed.json()["error"]["code"] == "storage_failure"
    monkeypatch.undo()
    after = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    assert after["approval"] is None and after["plan"] == view["plan"] and after["disposition"] is None and after["packet"]["status"] == "open"
    assert api("rao").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}") == []
    assert not [e for e in api("rao").get(f"{W(workspace)}/audit") if e["action"] == "plan.approve"]
    first = api("rao").post(f"{W(workspace)}/plans/{plan_id}/approve", body, command_id=command)
    again = api("rao").post(f"{W(workspace)}/plans/{plan_id}/approve", body, command_id=command)
    assert first["replayed"] is False and again["replayed"] is True and again["data"] == first["data"]
    assert len([e for e in api("rao").get(f"{W(workspace)}/audit") if e["action"] == "plan.approve"]) == 1
    # A different actor replaying the signer's command id cannot obtain or reuse the signature.
    api("mira").fail(f"{W(workspace)}/plans/{plan_id}/approve", body, code="command_id_conflict", status=409, command_id=command)
