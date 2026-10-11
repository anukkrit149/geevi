"""U8: exact patient-plan approval over an immutable packet."""
import threading

from app.services import command_service
from tests.helpers import W, draft_plan, meera_planned, meera_ready, sign_plan, submit_plan, upload


def test_signed_decision_context_preserves_the_assessment_known_at_that_decision(api, workspace):
    s = meera_planned(api, workspace)
    before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    context = before["decision_context"]
    assert context["assessment"] and context["findings"] and context["patient_goals"]
    assert all(c["requirement_text"] for c in context["criteria"])
    assert any(e["departure"] for e in context["exceptions"])
    api("rao").post(f"{W(workspace)}/patients/{s['meera']}/assessments", {
        "narrative": "A later clinical assessment with a different interpretation for review.", "dimension_notes": {"fitness": "Later assessment."}})
    after = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert after["decision_context"] == context and after["approval"] == before["approval"]


def test_save_submit_and_sign_are_separate_and_the_packet_is_exact(api, workspace):
    s = meera_ready(api, workspace)
    plan_id, body = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    view = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    assert view["plan"]["status"] == "draft" and view["packet"] is None and view["approval"] is None
    api("rao").post(f"{W(workspace)}/plans/{plan_id}/save", {"expected_revision": 1, **body, "intent": "Updated individual intent for the fictional preparation pathway."})
    api("rao").fail(f"{W(workspace)}/plans/{plan_id}/approve", {"expected_revision": 2, "packet_id": plan_id, "digest": "x"}, code="wrong_state")
    frozen = submit_plan(api, workspace, plan_id)
    api("rao").fail(f"{W(workspace)}/plans/{plan_id}/save", {"expected_revision": 3, **body}, code="wrong_state")
    # A signature naming a different digest, or made by an account without the grant, is refused.
    api("rao").fail(f"{W(workspace)}/plans/{plan_id}/approve", {"expected_revision": 3, "packet_id": frozen["packet_id"], "digest": "0" * 64}, code="stale_target", status=409)
    for user in ("mira", "sen", "isha", "operator"):
        api(user).fail(f"{W(workspace)}/plans/{plan_id}/approve", {"expected_revision": 3, "packet_id": frozen["packet_id"], "digest": frozen["digest"], "actor": "rao"},
                       code="actor_not_permitted", headers={"X-Actor": "rao"})
    result = sign_plan(api, workspace, plan_id)
    view = api("mira").get(f"{W(workspace)}/plans/{plan_id}")
    approval = view["approval"]
    assert approval["recorded_by_name"] == "Dr. Rao" and approval["target_digest"] == frozen["digest"] == view["plan"]["content_digest"] == result["data"]["digest"]
    kinds = [r["kind"] for r in approval["read_set"]]
    assert kinds[:3] == ["protocol_version", "applicability_review", "profile_snapshot"] and "patient_discussion" in kinds and kinds.count("observation_version") >= 15
    assert approval["read_set"][0]["id"] == s["protocol"] and approval["read_set"][1]["id"] == s["applicability"]
    assert any(k.endswith("/reports/*") for k in approval["watch_set"]) and any(k.startswith("protocol/") for k in approval["watch_set"])
    assert view["disposition"] == "active" and view["currency"]["status"] == "current" and "not verified institutional" in view["signature_notice"]
    assert "not a verified institutional signature" in approval["statement"]
    api("rao").fail(f"{W(workspace)}/plans/{plan_id}/save", {"expected_revision": view["plan"]["revision"], **body}, code="immutable_version")


def test_plan_requires_latest_discussion_and_accepted_applicability(api, workspace):
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    api("mira").post(f"{W(workspace)}/patients/{s['meera']}/discussions", {"participants": ["Patient", "Mira"], "attributed_to": "patient",
                                                                           "goals": "Now prefers afternoon appointments."})
    api("rao").fail(f"{W(workspace)}/plans/{plan_id}/submit", {"expected_revision": 1}, code="discussion_not_current")


def test_previous_signed_plan_is_retained_while_a_successor_is_drafted(api, workspace):
    s = meera_planned(api, workspace)
    first = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    successor, body = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]], intent="Revised individual intent after the follow-up conversation.")
    during = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert during["plan"] == first["plan"] and during["approval"] == first["approval"] and during["disposition"] == "active"
    api("rao").fail(f"{W(workspace)}/patients/{s['meera']}/plans", body, code="revision_in_progress")
    submit_plan(api, workspace, successor)
    sign_plan(api, workspace, successor)
    versions = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/plans")
    assert [(v["plan"]["version_no"], v["plan"]["status"], v["disposition"]) for v in versions] == [(1, "superseded", "superseded"), (2, "approved", "active")]
    assert versions[0]["approval"] == first["approval"] and versions[0]["plan"]["content_digest"] == first["plan"]["content_digest"]  # signed history kept
    assert versions[1]["plan"]["previous_version_id"] == s["plan"]
    held = api("rao").post(f"{W(workspace)}/plans/{successor}/disposition", {"expected_revision": versions[1]["plan"]["revision"], "disposition": "held",
                                                                            "reason": "Held pending a venue confirmation."})
    after = api("rao").get(f"{W(workspace)}/plans/{successor}")
    assert held["data"]["disposition"] == "held" and after["disposition"] == "held" and after["plan"]["revision"] == versions[1]["plan"]["revision"]
    assert after["currency"]["status"] == "current"  # disposition and review currency are separate


def test_concurrent_material_change_prevents_a_partial_or_stale_signature(api, workspace, monkeypatch):
    """Both writers take the same workspace lock: whichever commits first, no stale signature can result."""
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    submit_plan(api, workspace, plan_id)
    doc_id = upload(api, workspace, s["meera"], "meera-molecular-preliminary")["target"]["id"]
    doc = api("mira").get(f"{W(workspace)}/sources/{doc_id}")["document"]
    view = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    at_commit, release, results = threading.Event(), threading.Event(), {}
    original = command_service._before_commit

    def gate(ctx):
        original(ctx)
        if ctx.account.username == "mira":
            at_commit.set()
            assert release.wait(10)

    monkeypatch.setattr(command_service, "_before_commit", gate)
    mira, rao = api("mira"), api("rao")

    def associate_now():
        results["associate"] = mira.http.post(f"/api/v1{W(workspace)}/sources/{doc_id}/associate", headers=mira.headers(), json={
            "command_id": "11111111-1111-4111-8111-111111111111", "expected_revision": doc["revision"], "patient_id": s["meera"], "checked": True,
            "note": "Identifier and accession checked."})

    def sign_now():
        results["sign"] = rao.http.post(f"/api/v1{W(workspace)}/plans/{plan_id}/approve", headers=rao.headers(), json={
            "command_id": "22222222-2222-4222-8222-222222222222", "expected_revision": view["plan"]["revision"], "packet_id": view["packet"]["id"],
            "digest": view["packet"]["target_digest"]})

    t1 = threading.Thread(target=associate_now)
    t1.start()
    assert at_commit.wait(10)  # the relevant result holds the workspace lock, not yet committed
    t2 = threading.Thread(target=sign_now)
    t2.start()
    t2.join(0.6)
    assert t2.is_alive(), "the signature must wait for the in-flight relevant change"
    release.set()
    t1.join(10)
    t2.join(10)
    assert results["associate"].status_code == 200
    assert results["sign"].status_code == 409 and results["sign"].json()["error"]["code"] == "stale_dependency"
    after = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    assert after["approval"] is None and after["plan"]["status"] == "submitted" and after["disposition"] is None
    assert api("rao").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}") == []  # nothing partial was written
