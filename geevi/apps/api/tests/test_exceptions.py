"""U8: typed, scoped exceptions with server-enforced approvers."""
import time
from datetime import UTC, datetime, timedelta

from tests.helpers import (
    W,
    accept_applicability,
    approved_plan,
    assess_and_discuss,
    baseline,
    decide_exception,
    draft_plan,
    knowledge,
    make_tasks,
    meera_planned,
    meera_ready,
    open_impacts,
    request_exception,
    sign_plan,
    submit_plan,
    task_do,
)


def test_permitted_venue_preference_supports_meeras_exact_plan(api, workspace):
    s = meera_ready(api, workspace)
    exception = next(e for e in api("rao").get(f"{W(workspace)}/exceptions?patient_id={s['meera']}"))
    assert exception["effective_status"] == "approved" and exception["exception_type"] == "operational" and exception["requirement_id"] == "REQ-VENUE"
    assert exception["discussion_id"] and exception["review_trigger"] and exception["decisions"][0]["recorded_by_name"] == "Dr. Rao"
    plan = approved_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    view = api("rao").get(f"{W(workspace)}/plans/{plan}")
    venue_gate = next(g for g in view["gates"] if g["requirement_id"] == "REQ-VENUE")
    assert venue_gate == {"requirement_id": "REQ-VENUE", "assessment": "difference", "satisfied": True, "code": None, "message": None,
                          "exception_id": s["venue"], "exception_state": "approved"}
    assert any(r == {"kind": "exception_request", "id": s["venue"], "digest": exception["content_digest"]} for r in view["approval"]["read_set"])
    # The shared protocol is untouched by the individual exception.
    protocol = api("rao").get(f"{W(workspace)}/protocols/{s['protocol']}")["version"]
    assert protocol["version_no"] == 1 and protocol["lifecycle"] == "effective" and protocol["requirements"][3]["waiver"] == {"allowed": True, "exception_type": "operational"}


def test_exception_alone_cannot_approve_plan_and_edited_request_needs_new_decisions(api, workspace):
    s = meera_ready(api, workspace)
    assert api("rao").get(f"{W(workspace)}/patients/{s['meera']}/plans") == []  # an approved exception approved no plan
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    current = api("rao").get(f"{W(workspace)}/exceptions")[0]
    revised = api("rao").post(f"{W(workspace)}/exceptions/{s['venue']}/revise", {
        "expected_revision": current["revision"], "departure": "Hold the visit at the patient's home address instead.", "rationale": "Revised request after a further conversation.",
        "review_trigger": "Review at the next visit."})["target"]["id"]
    rows = {e["id"]: e for e in api("rao").get(f"{W(workspace)}/exceptions")}
    assert rows[s["venue"]]["status"] == "superseded" and rows[revised]["effective_status"] == "pending" and rows[revised]["decisions"] == []
    assert rows[revised]["version_no"] == 2 and "Awaiting 1 more decision" in rows[revised]["next_action"]
    plan = api("rao").get(f"{W(workspace)}/plans/{plan_id}")["plan"]
    body = {"applicability_id": plan["applicability_id"], "discussion_id": plan["discussion_id"], "exception_ids": [revised], "intent": plan["intent"], "obligations": plan["obligations"]}
    api("rao").post(f"{W(workspace)}/plans/{plan_id}/save", {"expected_revision": plan["revision"], **body})
    submit_plan(api, workspace, plan_id)
    error = sign_plan(api, workspace, plan_id, expect=422)["error"]
    assert error["code"] == "exception_not_approved" and error["details"]["gates"][0]["exception_state"] == "pending"
    decide_exception(api, workspace, "rao", revised)
    # The decision changed the watched exception scope: the frozen packet is stale and must be re-submitted.
    assert sign_plan(api, workspace, plan_id, expect=409)["error"]["code"] == "stale_dependency"
    api("rao").post(f"{W(workspace)}/plans/{plan_id}/reopen", {"expected_revision": api("rao").get(f"{W(workspace)}/plans/{plan_id}")["plan"]["revision"]})
    submit_plan(api, workspace, plan_id)
    sign_plan(api, workspace, plan_id)


def test_pending_clinical_exception_blocks_only_its_affected_action(api, workspace):
    """AE3: the molecular requirement gates one SOP step. Independent preparation continues."""
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    planning = tasks["STEP-PLANNING-VISIT"]
    assert planning["gates"][0]["code"] == "exception_required" and planning["requires"] == ["REQ-MOLECULAR"]
    blocked = api("mira").fail(f"{W(workspace)}/tasks/{planning['id']}/send", {"expected_revision": planning["revision"]}, code="dependent_scope_unresolved")
    assert "other tasks are unaffected" in blocked["next_action"]
    clinical = request_exception(api, workspace, s["meera"], s["protocol"], "molecular")
    # A coordinator, a care-team member, the operator, or a forged actor field cannot decide a clinical exception.
    for user in ("mira", "isha", "operator"):
        error = api(user).fail(f"{W(workspace)}/exceptions/{clinical}/decide",
                               {"expected_revision": 1, "decision": "approve", "rationale": "Trying to authorise", "actor": "sen", "role": "reviewer"},
                               headers={"X-Actor": "sen"})
        assert error["code"] == "actor_not_permitted"
    first = decide_exception(api, workspace, "rao", clinical)
    assert first["data"] == {"status": "pending", "approvals": 1, "approvals_required": 2}  # one of two required approvals
    api("rao").fail(f"{W(workspace)}/exceptions/{clinical}/decide", {"expected_revision": 2, "decision": "approve", "rationale": "Approving twice"}, code="already_decided")
    still = api("mira").fail(f"{W(workspace)}/tasks/{planning['id']}/send", {"expected_revision": planning["revision"]}, code="dependent_scope_unresolved")
    assert still["details"]["gates"][0]["exception_state"] == "pending"
    pending = next(e for e in api("sen").get(f"{W(workspace)}/exceptions") if e["id"] == clinical)
    assert pending["owner_name"] == "Dr. Rao" and "Awaiting 1 more decision" in pending["next_action"]
    # Independent preparation whose dependencies permit it still works.
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "send")
    task_do(api, workspace, "isha", tasks["STEP-CONFIRM-VENUE"]["id"], "accept")
    # With Sen's independent approval the dependent dispatch becomes possible.
    decide_exception(api, workspace, "sen", clinical)
    task_do(api, workspace, "mira", planning["id"], "send")
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["plan"]["status"] == "approved"


def test_rejected_exception_and_non_waivable_scope_cannot_be_bypassed(api, workspace):
    k = knowledge(api, workspace)
    pid, _ = baseline(api, workspace, "meera")
    assess_and_discuss(api, workspace, pid)
    # Identity is non-waivable: nobody can even request an exception for it.
    for user, code in (("rao", "non_waivable"), ("mira", "actor_not_permitted"), ("operator", "actor_not_permitted")):
        api(user).fail(f"{W(workspace)}/patients/{pid}/exceptions", {"protocol_version_id": k["protocol"], "requirement_id": "REQ-IDENTITY", "exception_type": "operational",
                                                                    "departure": "Skip the identity review", "rationale": "No time to review", "review_trigger": "never", "approved": True}, code=code)
    api("rao").fail(f"{W(workspace)}/patients/{pid}/exceptions", {"protocol_version_id": k["protocol"], "requirement_id": "REQ-VENUE", "exception_type": "clinical",
                                                                 "departure": "Use another venue", "rationale": "Wrong type requested", "review_trigger": "x-review"}, code="exception_type_not_permitted")
    api("rao").fail(f"{W(workspace)}/patients/{pid}/exceptions", {"protocol_version_id": k["protocol"], "requirement_id": "REQ-VENUE", "exception_type": "operational",
                                                                 "departure": "Use another venue", "rationale": "No expiry or trigger"}, code="expiry_or_trigger_required")
    applicability = accept_applicability(api, workspace, pid, k["protocol"], **{"REQ-IDENTITY": "unknown", "REQ-VENUE": "difference"})
    venue = request_exception(api, workspace, pid, k["protocol"])
    decide_exception(api, workspace, "rao", venue, "reject")
    plan_id, _ = draft_plan(api, workspace, pid, applicability, [venue])
    submit_plan(api, workspace, plan_id)
    error = sign_plan(api, workspace, plan_id, expect=422)["error"]
    codes = {g["requirement_id"]: g["code"] for g in error["details"]["gates"]}
    assert codes == {"REQ-IDENTITY": "required_input_missing", "REQ-VENUE": "exception_not_approved"}
    assert api("rao").get(f"{W(workspace)}/plans/{plan_id}")["approval"] is None


def test_expiry_preserves_historical_care_and_creates_future_review(api, workspace):
    k = knowledge(api, workspace)
    pid, _ = baseline(api, workspace, "meera")
    assess_and_discuss(api, workspace, pid)
    applicability = accept_applicability(api, workspace, pid, k["protocol"], **{"REQ-VENUE": "difference"})
    venue = request_exception(api, workspace, pid, k["protocol"], review_trigger=None, expires_at=(datetime.now(UTC) + timedelta(seconds=2)).isoformat())
    decide_exception(api, workspace, "rao", venue)
    plan = approved_plan(api, workspace, pid, applicability, [venue])
    tasks = make_tasks(api, workspace, plan, k["sop"])
    care = api("isha").post(f"{W(workspace)}/patients/{pid}/care-events", {"status": "performed", "actual_time": {"value": 3, "unit": "day"},
                                                                          "narrative": "Visit held at the satellite clinic.", "plan_version_id": plan})["target"]["id"]
    api("rao").fail(f"{W(workspace)}/exceptions/{venue}/record-expiry", {"expected_revision": 2}, code="not_expired")
    time.sleep(2.2)
    row = next(e for e in api("rao").get(f"{W(workspace)}/exceptions") if e["id"] == venue)
    assert row["status"] == "approved" and row["effective_status"] == "expired"  # guards use the effective state even before it is recorded
    obligation = api("rao").get(f"{W(workspace)}/follow-ups?patient_id={pid}")[0]
    from tests.helpers import DAY
    api("rao").fail(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", {
        "expected_revision": obligation["revision"], "decision": "continue_unchanged", "rationale": "Routine review, no change.",
        "next": {"purpose": "Next routine review", "due": DAY(28), "owner_username": "mira"}}, code="exception_not_approved")
    expired = api("mira").post(f"{W(workspace)}/exceptions/{venue}/record-expiry", {"expected_revision": 2})
    assert expired["data"]["impacts_created"] == 1
    impact = open_impacts(api, workspace, pid)[0]
    assert impact["change"]["event_kind"] == "exception_expired" and impact["owner_name"] == "Dr. Rao" and impact["plan_version_id"] == plan
    api("mira").fail(f"{W(workspace)}/tasks/{tasks['STEP-CONFIRM-VENUE']['id']}/send", {"expected_revision": 2}, code="plan_review_needed")  # future action blocked
    events = api("rao").get(f"{W(workspace)}/patients/{pid}/care-events")
    assert [e["id"] for e in events] == [care] and events[0]["status"] == "performed"  # completed care is intact
    view = api("rao").get(f"{W(workspace)}/plans/{plan}")
    assert view["plan"]["status"] == "approved" and view["disposition"] == "active" and view["currency"]["status"] == "review_needed"
