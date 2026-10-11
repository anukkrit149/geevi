"""U2: explicit legacy import into staging, original preservation and honest disclosure."""
import hashlib
import os
import uuid
from pathlib import Path

import pytest

from app.services import staging
from tests.helpers import W, b64, raw, register

LEGACY_APP = Path(__file__).resolve().parents[4] / "product"


def legacy_case(key: str, original: bytes, **extra) -> dict:
    sha = hashlib.sha256(original).hexdigest()
    return {"id": key, "revision": 4,
            "documents": [{"id": "D1", "hash": sha, "name": f"{key}-intake.pdf", "title": "Intake report", "pages": ["Reported diagnosis: AML\nNPM1: Pending"],
                           "layouts": [{"segments": [{"start": 0, "end": 23, "box": [0.1, 0.2, 0.4, 0.02]}]}], "pageCount": 1, "kind": "pdf",
                           "identity": "checked", "claimed": f"DEMO-{key.upper()}", "receivedAt": "2026-09-01T10:00:00.000Z",
                           "identityReview": {"by": "coordinator", "note": "Checked against referral", "at": "2026-09-01T10:05:00.000Z"}}],
            "facts": [{"id": "F1", "docId": "D1", "hash": sha, "label": "Reported diagnosis", "category": "diagnosis", "value": "AML", "originalValue": "AML",
                       "quote": "Reported diagnosis: AML", "page": 1, "start": 0, "end": 23, "boxes": [[0.1, 0.2, 0.4, 0.02]], "status": "verified", "seen": True,
                       "review": {"by": "Dr. Rao · demo", "at": "2026-09-01T11:00:00.000Z", "reason": ""}},
                      {"id": "F2", "docId": "D1", "hash": sha, "label": "NPM1", "category": "biomarker", "value": "Pending", "originalValue": "Pending",
                       "quote": "NPM1: Pending", "page": 1, "start": 24, "end": 37, "boxes": [], "status": "candidate", "seen": False, "review": None}],
            "annotations": [{"id": "A1", "docId": "D1", "page": 1, "hash": sha, "box": [0.1, 0.1, 0.2, 0.2], "note": "Region reviewed by clinician", "by": "Dr. Rao · demo"}],
            "tasks": [{"id": "T1", "text": "Prepare the initial profile", "owner": "Coordinator", "status": "open"}],
            "plan": {"text": "Review the diagnostic profile and discuss the next treatment step.", "version": 2},
            "protocol": {"text": "Legacy prose protocol for this patient", "approval": {"by": "Dr. Rao · demo", "at": "2026-09-02T09:00:00.000Z"}},
            "profileSignoff": {"by": "Dr. Rao · demo", "scope": "Initial profile reviewed", "revision": 3},
            "encounters": [{"id": "E1", "disposition": "continue", "by": "Dr. Rao · demo"}], "history": [], "audit": [{"text": "Report received", "role": "coordinator"}],
            "messages": [], **extra}


def snapshot(**cases) -> dict:
    return {"casebook-intake-v1": cases, "casebook-research-lab-v1": [{"id": "q1", "title": "Legacy question", "scope": "x", "papers": [], "applications": []}]}


def original(name: str, data: bytes) -> dict:
    return {"filename": name, "media_type": "application/pdf", "content_base64": b64(data)}


def tree_state(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(root.rglob("*")) if p.is_file() and "node_modules" not in p.parts}


@pytest.fixture(autouse=True)
def legacy_app_untouched():
    before = tree_state(LEGACY_APP) if LEGACY_APP.exists() else {}
    yield
    assert (tree_state(LEGACY_APP) if LEGACY_APP.exists() else {}) == before, "the legacy app directory must never be modified"


def test_payloads_and_supplied_originals_keep_identity_provenance_and_geometry(api, workspace):
    op = api("operator")
    meera_bytes, arun_bytes = raw("meera-referral"), raw("arun-referral")
    body = {"snapshots": snapshot(meera=legacy_case("meera", meera_bytes), arun=legacy_case("arun", arun_bytes)),
            "originals": [original("renamed-by-user.pdf", meera_bytes), original("another-name.pdf", arun_bytes)]}
    job = op.post(f"{W(workspace)}/imports/legacy", body)
    assert job["status"] == "validated" and job["report"]["complete"] is True and job["report"]["originals_supplied"] == 2
    assert job["report"]["unmapped"]["protocol"] == 2 and job["report"]["unmapped"]["research_question"] == 1
    # Staged only: the active workspace is still empty until the operator explicitly activates.
    assert api("rao").get(f"{W(workspace)}/patients") == []
    op.post(f"{W(workspace)}/imports/{job['id']}/activate")
    patients = {p["identifiers"][0]["value"]: p for p in api("rao").get(f"{W(workspace)}/patients")}
    assert set(patients) == {"DEMO-MEERA", "DEMO-ARUN"} and patients["DEMO-MEERA"]["identifiers"][0]["system"] == "legacy-casebook"
    pid = patients["DEMO-MEERA"]["patient"]["id"]
    doc = api("rao").get(f"{W(workspace)}/sources?patient_id={pid}")[0]
    assert doc["sha256"] == hashlib.sha256(meera_bytes).hexdigest() and doc["original_available"] is True and doc["association_status"] == "associated"
    assert doc["association_review"]["legacy"] is True and doc["legacy"]["layouts"][0]["segments"][0]["box"] == [0.1, 0.2, 0.4, 0.02]
    content = api("rao").http.get(f"/api/v1{W(workspace)}/sources/{doc['id']}/content")
    assert content.status_code == 200 and content.content == meera_bytes  # matched by hash although the filename differed
    cands = {c["assertion"]["analyte"]: c for c in api("rao").get(f"{W(workspace)}/sources/{doc['id']}")["candidates"]}
    assert cands["Reported diagnosis"]["source_ref"]["region"] == [0.1, 0.2, 0.5, 0.22] and cands["Reported diagnosis"]["source_ref"]["span"] == [0, 23]
    assert cands["Reported diagnosis"]["status"] == "unreviewed" and cands["Reported diagnosis"]["assertion"]["legacy"]["status"] == "verified"
    assert cands["NPM1"]["assertion"]["result_state"] == "pending"
    # With the matching original present, a current reviewer can verify against it in the new app.
    api("mira").post(f"{W(workspace)}/candidates/{cands['Reported diagnosis']['id']}/review", {"expected_revision": 1, "disposition": "verified", "source_inspected": True})
    api("mira").fail(f"{W(workspace)}/candidates/{cands['NPM1']['id']}/review", {"expected_revision": 1, "disposition": "verified", "source_inspected": True}, code="source_not_cited")
    snapshots = op.get(f"{W(workspace)}/recovery-snapshots")
    assert snapshots[0]["source_kind"] == "legacy" and snapshots[0]["source_fingerprint"] == job["source_fingerprint"]


def test_metadata_only_packet_is_never_a_complete_migration(api, workspace):
    op = api("operator")
    packet = {"prototype": True, "notClinicalAuthorization": True, "createdAt": "2026-09-03T00:00:00Z",
              "patient": {"name": "Meera", "id": "DEMO-MEERA"}, "case": legacy_case("meera", raw("meera-referral"))}
    job = op.post(f"{W(workspace)}/imports/legacy", {"packets": [packet]})
    report = job["report"]
    assert report["complete"] is False and len(report["missing_originals"]) == 1
    assert any("not a complete migration" in d for d in report["disclosures"]) and any("not supplied" in d for d in report["disclosures"])
    op.post(f"{W(workspace)}/imports/{job['id']}/activate")
    pid = api("rao").get(f"{W(workspace)}/patients")[0]["patient"]["id"]
    doc = api("rao").get(f"{W(workspace)}/sources?patient_id={pid}")[0]
    assert doc["original_available"] is False
    assert api("rao").get(f"{W(workspace)}/sources/{doc['id']}/content", expect=404)["error"]["code"] == "original_unavailable"
    cand = api("rao").get(f"{W(workspace)}/sources/{doc['id']}")["candidates"][0]
    api("mira").fail(f"{W(workspace)}/candidates/{cand['id']}/review", {"expected_revision": 1, "disposition": "verified", "source_inspected": True}, code="original_unavailable")
    assert api("rao").get(f"{W(workspace)}/observations?patient_id={pid}") == []


def test_legacy_prose_plan_and_approval_stay_unmapped(api, workspace):
    op = api("operator")
    job = op.post(f"{W(workspace)}/imports/legacy", {"snapshots": snapshot(meera=legacy_case("meera", raw("meera-referral")))})
    op.post(f"{W(workspace)}/imports/{job['id']}/activate")
    records = api("rao").get(f"{W(workspace)}/legacy-records")
    by_kind = {r["legacy_kind"]: r for r in records}
    assert by_kind["protocol"]["mapping_status"] == "unmapped" and by_kind["protocol"]["payload"]["approval"]["by"] == "Dr. Rao · demo"
    assert "not a reviewed departmental publication" in by_kind["protocol"]["note"] and "not a current clinical signature" in by_kind["plan"]["note"]
    assert {"plan", "protocol", "profileSignoff", "encounters", "tasks", "audit", "annotation", "research_question"} <= set(by_kind)
    assert all(r["mapping_status"] == "unmapped" for r in records)
    # No legacy approval became a shared publication, an SOP or a signed plan in this application.
    pid = api("rao").get(f"{W(workspace)}/patients")[0]["patient"]["id"]
    assert api("rao").get(f"{W(workspace)}/protocols") == [] and api("rao").get(f"{W(workspace)}/sops") == []
    assert api("rao").get(f"{W(workspace)}/patients/{pid}/plans") == []


def test_interrupted_or_retried_staging_never_replaces_active_records(api, workspace, monkeypatch):
    op = api("operator")
    live = register(api, workspace, "meera")  # an active record that must survive
    body = {"snapshots": snapshot(arun=legacy_case("arun", raw("arun-referral"))), "originals": [original("a.pdf", raw("arun-referral"))]}
    cid = str(uuid.uuid4())

    def crash(job):
        raise RuntimeError("simulated interruption during staging")

    monkeypatch.setattr(staging, "_before_stage_commit", crash)
    assert op.http.post(f"/api/v1{W(workspace)}/imports/legacy", json={"command_id": cid, **body}, headers=op.headers()).status_code == 500
    monkeypatch.undo()
    assert op.get(f"{W(workspace)}/imports") == [] and [p["patient"]["id"] for p in api("rao").get(f"{W(workspace)}/patients")] == [live]
    job = op.post(f"{W(workspace)}/imports/legacy", body, command_id=cid)
    assert op.post(f"{W(workspace)}/imports/legacy", body, command_id=cid)["id"] == job["id"]  # retry returns the same staged job
    assert len(op.get(f"{W(workspace)}/imports")) == 1 and len(api("rao").get(f"{W(workspace)}/patients")) == 1
    act = str(uuid.uuid4())
    first = op.post(f"{W(workspace)}/imports/{job['id']}/activate", command_id=act)
    again = op.post(f"{W(workspace)}/imports/{job['id']}/activate", command_id=act)
    assert first["replayed"] is False and again["replayed"] is True and again["active_container_id"] == first["active_container_id"]
    op.fail(f"{W(workspace)}/imports/{job['id']}/activate", code="already_activated", status=409)
    # Clinical accounts cannot stage or activate imports.
    api("rao").fail(f"{W(workspace)}/imports/legacy", body, code="actor_not_permitted")


def test_wrong_original_hash_and_excluded_format_fail_without_changes(api, workspace):
    op = api("operator")
    case = legacy_case("meera", raw("meera-referral"))
    wrong = op.fail(f"{W(workspace)}/imports/legacy", {"snapshots": snapshot(meera=case), "originals": [original("meera-intake.pdf", raw("meera-cyto"))]},
                    code="original_hash_mismatch", status=422)
    assert wrong["details"]["mismatched"][0]["filename"] == "meera-intake.pdf"
    old = op.fail(f"{W(workspace)}/imports/legacy", {"snapshots": {"casebook-evidence-demo-v2": {"anything": 1}}}, code="unsupported_legacy_format")
    assert old["details"]["excluded"] == ["casebook-evidence-demo-v2"]
    op.fail(f"{W(workspace)}/imports/legacy", {"snapshots": {"some-other-store": {}}}, code="unsupported_legacy_format")
    op.fail(f"{W(workspace)}/imports/legacy", {}, code="unsupported_legacy_format")
    assert op.get(f"{W(workspace)}/imports") == [] and api("rao").get(f"{W(workspace)}/patients") == []


def test_later_legacy_export_is_a_new_explicit_choice_not_a_merge(api, workspace):
    op = api("operator")
    first = op.post(f"{W(workspace)}/imports/legacy", {"snapshots": snapshot(meera=legacy_case("meera", raw("meera-referral")))})
    op.post(f"{W(workspace)}/imports/{first['id']}/activate")
    later_case = legacy_case("meera", raw("meera-referral"), revision=9, tasks=[])
    second = op.post(f"{W(workspace)}/imports/legacy", {"snapshots": snapshot(meera=later_case)})
    assert second["id"] != first["id"] and second["status"] == "validated" and second["source_fingerprint"] != first["source_fingerprint"]
    # Until explicitly activated, the later export changes nothing in the active workspace.
    assert len(api("rao").get(f"{W(workspace)}/patients")) == 1
    assert any(r["legacy_kind"] == "tasks" for r in api("rao").get(f"{W(workspace)}/legacy-records"))
    discarded = op.post(f"{W(workspace)}/imports/{second['id']}/discard")
    assert discarded["status"] == "discarded" and discarded["staging_container_id"] is None
    assert os.path.isdir(LEGACY_APP)
