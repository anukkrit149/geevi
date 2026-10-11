"""U13: complete archive and staged restore, including a restore into a completely fresh database."""
import base64
import copy
import hashlib
import uuid

from sqlalchemy import text

from app.services import staging
from tests.helpers import DAY, INPUTS, W, intake, make_tasks, meera_planned, raw, register, task_do

VOLATILE = {"recovery_snapshots"}


def _journey(api, ws):
    """A workspace with facts, history, signatures, tasks, care, an amendment and an open impact."""
    s = meera_planned(api, ws)
    tasks = make_tasks(api, ws, s["plan"], s["sop"])
    task_do(api, ws, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "send")
    task_do(api, ws, "isha", tasks["STEP-CONFIRM-VENUE"]["id"], "accept")
    api("isha").post(f"{W(ws)}/patients/{s['meera']}/care-events", {"status": "partial", "actual_time": DAY(3), "narrative": "Checklist partly completed.",
                                                                  "plan_version_id": s["plan"]})
    intake(api, ws, s["meera"], "meera-marrow-correction")
    return s


def _export(api, ws, mode="full"):
    return api("operator").get(f"{W(ws)}/archive?mode={mode}")


def test_fresh_database_restore_reproduces_history_digests_geometry_and_exact_bytes(api, workspace, fresh_database):
    s = _journey(api, workspace)
    archive = _export(api, workspace)
    assert archive["schema"] == "geevi-archive/1" and archive["kind"] == "full_backup" and archive["complete"] is True and archive["incomplete_reasons"] == []
    assert archive["labels"]["contains_real_patient_data"] is False and "password hashes" in archive["excluded"]
    flat = str({k: v for k, v in archive.items() if k != "originals"}).lower()
    assert "password_hash" not in flat and "token_hash" not in flat and "csrf" not in flat and "$argon2" not in flat
    assert archive["counts"]["plan_approvals"] == 1 and archive["counts"]["command_receipts"] > 50 and archive["counts"]["audit_events"] > 50
    plan_before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    marrow_doc = s["docs"]["meera-marrow"][0]
    with fresh_database() as (target, Api):
        op, rao = Api("operator"), Api("rao")
        job = op.post(f"{W(target)}/imports/archive", {"archive": archive})
        assert job["status"] == "validated" and job["report"]["complete"] is True and job["report"]["counts"] == archive["counts"]
        assert rao.get(f"{W(target)}/patients") == []  # staged, not active
        op.post(f"{W(target)}/imports/{job['id']}/activate")
        # Same logical ids, digests, signatures, read sets and history.
        plan_after = rao.get(f"{W(target)}/plans/{s['plan']}")
        assert plan_after["plan"] == plan_before["plan"] and plan_after["approval"] == plan_before["approval"]
        assert plan_after["currency"] == plan_before["currency"] and plan_after["currency"]["status"] == "review_needed"
        # Exact original bytes and source geometry.
        content = rao.http.get(f"/api/v1{W(target)}/sources/{marrow_doc}/content")
        assert content.content == raw("meera-marrow") and hashlib.sha256(content.content).hexdigest() == INPUTS["meera-marrow"]["sha256"]
        observations = rao.get(f"{W(target)}/observations?patient_id={s['meera']}&include_history=true")
        cellularity = sorted((o for o in observations if o["analyte"] == "Cellularity"), key=lambda o: o["version_no"])
        assert [(o["value_text"], o["status"]) for o in cellularity] == [("90 %", "superseded"), ("80 %", "current")]
        assert cellularity[0]["source_ref"]["region"] and cellularity[0]["source_ref"]["page"] == 1
        tasks = rao.get(f"{W(target)}/tasks?patient_id={s['meera']}")
        assert [e["event"] for e in next(t for t in tasks if t["sop_step_id"] == "STEP-CONFIRM-VENUE")["events"]] == ["created", "sent", "accepted"]
        # A second export from the restored database is content-identical.
        again = op.get(f"{W(target)}/archive")
        for name, rows in archive["tables"].items():
            if name not in VOLATILE:
                assert again["tables"][name] == rows, name
        assert [(o["sha256"], o["base64"]) for o in again["originals"]] == [(o["sha256"], o["base64"]) for o in archive["originals"]]
        snapshot = op.get(f"{W(target)}/recovery-snapshots")[0]
        assert snapshot["source_kind"] == "archive" and "grant no current permissions" in snapshot["note"]
        # The restored workspace keeps working: a new command builds on restored history.
        rao.post(f"{W(target)}/notes", {"text": "Restored and usable"})
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["plan"] == plan_before["plan"]  # the source database was untouched


def test_missing_or_corrupt_original_prevents_a_complete_backup_claim(api, workspace, db):
    register(api, workspace, "meera")
    pid = api("rao").get(f"{W(workspace)}/patients")[0]["patient"]["id"]
    intake(api, workspace, pid, "meera-cyto")
    intake(api, workspace, pid, "meera-referral")
    review = _export(api, workspace, "review")
    assert review["kind"] == "review_packet" and review["complete"] is False and "not a backup" in review["incomplete_reasons"][0]
    assert all(o["base64"] is None for o in review["originals"])
    # Simulate a lost original (bypassing the immutable-blob trigger, as storage loss would).
    db.execute(text("ALTER TABLE source_blobs DISABLE TRIGGER source_blobs_immutable"))
    db.execute(text("UPDATE source_blobs SET data = NULL WHERE sha256 = :sha"), {"sha": INPUTS["meera-cyto"]["sha256"]})
    db.execute(text("UPDATE source_blobs SET data = :junk WHERE sha256 = :sha"), {"sha": INPUTS["meera-referral"]["sha256"], "junk": b"%PDF-corrupted"})
    db.execute(text("ALTER TABLE source_blobs ENABLE TRIGGER source_blobs_immutable"))
    db.commit()
    archive = _export(api, workspace)
    assert archive["complete"] is False and len(archive["incomplete_reasons"]) == 2
    assert any("missing" in r for r in archive["incomplete_reasons"]) and any("corrupt" in r for r in archive["incomplete_reasons"])
    assert [o["available"] for o in archive["originals"]] == [False, False]
    # Restoring it is allowed but honestly incomplete, and the missing original stays unavailable.
    target = api("operator").http.post("/api/v1/workspaces", json={"command_id": str(uuid.uuid4()), "name": "Incomplete restore"}, headers=api("operator").headers()).json()["id"]
    job = api("operator").post(f"{W(target)}/imports/archive", {"archive": archive})
    assert job["report"]["complete"] is False and len(job["report"]["incomplete_reasons"]) == 2
    api("operator").post(f"{W(target)}/imports/{job['id']}/activate")
    doc = api("rao").get(f"{W(target)}/sources")[0]
    assert doc["original_available"] is False and api("rao").get(f"{W(target)}/sources/{doc['id']}/content", expect=404)["error"]["code"] == "original_unavailable"


def test_unsupported_schema_decode_mismatch_oversize_and_cross_scope_references_fail_before_activation(api, workspace, monkeypatch):
    s = meera_planned(api, workspace)
    archive = _export(api, workspace)
    op = api("operator")
    path = f"{W(workspace)}/imports/archive"
    op.fail(path, {"archive": {**archive, "schema": "geevi-archive/99"}}, code="unsupported_archive_schema")
    tampered = copy.deepcopy(archive)
    tampered["originals"][0]["base64"] = base64.b64encode(b"%PDF-not the original bytes").decode()
    op.fail(path, {"archive": tampered}, code="original_hash_mismatch")
    wrong_length = copy.deepcopy(archive)
    wrong_length["originals"][0]["length"] += 1
    op.fail(path, {"archive": wrong_length}, code="original_hash_mismatch")
    # A record pointing at an identity outside the archive's own scope.
    dangling = copy.deepcopy(archive)
    dangling["tables"]["patient_plan_versions"][0]["patient_id"] = str(uuid.uuid4())
    error = op.fail(path, {"archive": dangling}, code="reference_validation_failed")
    assert error["details"]["active_workspace_unchanged"] is True
    unknown_field = copy.deepcopy(archive)
    unknown_field["tables"]["patients"][0]["is_admin"] = True
    op.fail(path, {"archive": unknown_field}, code="unsupported_archive_content")
    from app.core.config import get_settings
    monkeypatch.setenv("GEEVI_MAX_ARCHIVE_BYTES", "2000")
    get_settings.cache_clear()
    try:
        op.fail(path, {"archive": archive}, code="archive_too_large", status=413)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    jobs = op.get(f"{W(workspace)}/imports")
    assert [j["status"] for j in jobs] == ["failed"] and jobs[0]["staging_container_id"] is None  # only the reference failure reached staging
    op.fail(f"{W(workspace)}/imports/{jobs[0]['id']}/activate", code="not_validated")
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["plan"]["status"] == "approved"  # the active workspace is intact


def test_interrupted_import_leaves_the_current_container_active(api, workspace, monkeypatch):
    s = meera_planned(api, workspace)
    archive = _export(api, workspace)
    op = api("operator")
    before = op.get("/session")["workspaces"]
    active_before = next(w for w in before if w["id"] == workspace)["active_container_id"]

    def crash(job):
        raise RuntimeError("simulated crash while staging")

    monkeypatch.setattr(staging, "_before_stage_commit", crash)
    command = str(uuid.uuid4())
    assert op.http.post(f"/api/v1{W(workspace)}/imports/archive", json={"command_id": command, "archive": archive}, headers=op.headers()).status_code == 500
    monkeypatch.undo()
    assert op.get(f"{W(workspace)}/imports") == []
    assert next(w for w in op.get("/session")["workspaces"] if w["id"] == workspace)["active_container_id"] == active_before
    job = op.post(f"{W(workspace)}/imports/archive", {"archive": archive}, command_id=command)  # same-id retry stages exactly once
    assert job["status"] == "validated" and len(op.get(f"{W(workspace)}/imports")) == 1
    assert next(w for w in op.get("/session")["workspaces"] if w["id"] == workspace)["active_container_id"] == active_before
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["approval"] is not None
    api("rao").fail(f"{W(workspace)}/imports/archive", {"archive": archive}, code="actor_not_permitted")
    assert api("rao").http.get(f"/api/v1{W(workspace)}/archive").json()["error"]["code"] == "actor_not_permitted"


def test_password_session_or_capability_injection_cannot_grant_authority(api, workspace):
    register(api, workspace, "meera")
    archive = _export(api, workspace)
    op = api("operator")
    for section in ("accounts", "workspace_grants", "auth_sessions"):
        hostile = copy.deepcopy(archive)
        hostile["tables"][section] = [{"username": "operator", "capabilities": ["plan.approve", "protocol.publish"], "password_hash": "x"}]
        error = op.fail(f"{W(workspace)}/imports/archive", {"archive": hostile}, code="forbidden_archive_content")
        assert error["details"]["sections"] == [section]
    top_level = {**copy.deepcopy(archive), "grants": [{"account": "operator", "capabilities": ["plan.approve"]}]}
    op.fail(f"{W(workspace)}/imports/archive", {"archive": top_level}, code="forbidden_archive_content")
    # A restored history names Dr. Rao as a recorder; that grants the restoring operator nothing.
    job = op.post(f"{W(workspace)}/imports/archive", {"archive": archive})
    op.post(f"{W(workspace)}/imports/{job['id']}/activate")
    session = op.get("/session")
    assert set(next(w for w in session["workspaces"] if w["id"] == workspace)["capabilities"]) == {"workspace.manage", "archive.export", "archive.import", "legacy.import"}
    assert op.get(f"{W(workspace)}/patients", expect=403)["error"]["code"] == "actor_not_permitted"


def test_restoring_beside_existing_records_preserves_logical_ids_without_collisions(api, workspace):
    s = meera_planned(api, workspace)
    archive = _export(api, workspace)
    plan_before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    op = api("operator")
    # Restore into the SAME workspace: identical logical ids now exist in two containers.
    job = op.post(f"{W(workspace)}/imports/archive", {"archive": archive})
    api("rao").post(f"{W(workspace)}/notes", {"text": "Written to the active container while a restore is staged"})
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}") == plan_before  # staged copy rewrote nothing
    result = op.post(f"{W(workspace)}/imports/{job['id']}/activate")
    restored = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert restored["plan"] == plan_before["plan"] and restored["approval"] == plan_before["approval"]
    assert api("rao").get(f"{W(workspace)}/notes") == []  # the archive's snapshot is now active; the note stayed in the retired container
    assert result["job"]["previous_container_id"] != result["active_container_id"]
    # And into a different workspace: the same logical ids coexist without touching each other.
    other = op.http.post("/api/v1/workspaces", json={"command_id": str(uuid.uuid4()), "name": "Side-by-side"}, headers=op.headers()).json()["id"]
    second = op.post(f"{W(other)}/imports/archive", {"archive": archive})
    op.post(f"{W(other)}/imports/{second['id']}/activate")
    api("rao").post(f"{W(other)}/plans/{s['plan']}/disposition", {"expected_revision": restored["plan"]["revision"], "disposition": "held",
                                                                 "reason": "Held only in the side-by-side copy."})
    assert api("rao").get(f"{W(other)}/plans/{s['plan']}")["disposition"] == "held"
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["disposition"] == "active"
