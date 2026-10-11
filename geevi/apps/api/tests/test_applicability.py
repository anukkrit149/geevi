"""U7: criterion-level applicability and scoped review currency."""
from tests.helpers import (
    W,
    arun_planned,
    assess_and_discuss,
    baseline,
    draft_plan,
    intake,
    knowledge,
    make_tasks,
    meera_planned,
    meera_ready,
    open_impacts,
    sign_plan,
    submit_plan,
    task_do,
)


def test_unknown_stays_unknown_and_not_applicable_needs_rationale(api, workspace):
    k = knowledge(api, workspace)
    pid, _ = baseline(api, workspace, "meera")
    assess_and_discuss(api, workspace, pid)
    api("mira").fail(f"{W(workspace)}/patients/{pid}/applicability", {"protocol_version_id": k["protocol"]}, code="actor_not_permitted")
    review = api("rao").post(f"{W(workspace)}/patients/{pid}/applicability", {"protocol_version_id": k["protocol"]})["target"]["id"]
    current = api("rao").get(f"{W(workspace)}/patients/{pid}/applicability")[0]
    assert [c["assessment"] for c in current["criteria"]] == [None] * 5 and current["snapshot_id"]
    api("rao").fail(f"{W(workspace)}/applicability/{review}/accept", {"expected_revision": 1}, code="applicability_incomplete")
    criteria = [{"requirement_id": c["requirement_id"], "assessment": "match", "rationale": "", "supporting": []} for c in current["criteria"]]
    criteria[3].update(assessment="not_applicable")
    criteria[4].update(assessment="unknown")
    api("rao").post(f"{W(workspace)}/applicability/{review}/save", {"expected_revision": 1, "criteria": criteria})
    error = api("rao").fail(f"{W(workspace)}/applicability/{review}/accept", {"expected_revision": 2}, code="applicability_incomplete")
    assert error["details"]["criteria"] == [{"requirement_id": "REQ-VENUE", "message": "'not applicable' needs an attributed rationale."}]
    criteria[3].update(rationale="Visit already held before referral to this service.")
    api("rao").post(f"{W(workspace)}/applicability/{review}/save", {"expected_revision": 2, "criteria": criteria})
    done = api("rao").post(f"{W(workspace)}/applicability/{review}/accept", {"expected_revision": 3})
    assert done["data"]["unknown_requirements"] == ["REQ-MOLECULAR"]
    accepted = api("rao").get(f"{W(workspace)}/patients/{pid}/applicability")[0]
    assert accepted["status"] == "accepted" and accepted["criteria"][4]["assessment"] == "unknown" and accepted["recorded_by_name"] == "Dr. Rao"
    api("rao").fail(f"{W(workspace)}/applicability/{review}/save", {"expected_revision": 4, "criteria": criteria}, code="immutable_version")


def test_new_relevant_result_blocks_stale_signature_through_watch_scope(api, workspace):
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    submit_plan(api, workspace, plan_id)
    # A molecular report that was NOT in the packet's read set arrives and is associated by Mira.
    doc_id, _ = intake(api, workspace, s["meera"], "meera-molecular-preliminary")
    error = sign_plan(api, workspace, plan_id, expect=409)["error"]
    assert error["code"] == "stale_dependency" and "reopen" in error["next_action"]
    scopes = {c["scope"].split("/", 2)[2]: c for c in error["details"]["changes"] if "scope" in c}
    assert set(scopes) == {"reports/*", "reports/molecular"}
    change = scopes["reports/molecular"]["last_change"]
    assert change["actor"] == "Mira" and change["document_id"] == doc_id  # the explanation names the exact change and who made it
    view = api("rao").get(f"{W(workspace)}/plans/{plan_id}")
    assert view["plan"]["status"] == "submitted" and view["approval"] is None and len(view["packet_changes"]) == 2
    # Authorised path: reopen, re-freeze with the new material, sign.
    api("rao").post(f"{W(workspace)}/plans/{plan_id}/reopen", {"expected_revision": view["plan"]["revision"]})
    submit_plan(api, workspace, plan_id)
    assert sign_plan(api, workspace, plan_id)["data"]["approval_id"]


def test_task_owner_edit_preserves_review_but_clinical_obligation_edit_opens_targeted_work(api, workspace):
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    watch_before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["approval"]["watch_set"]
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "update", owner_username="mira", note="Covering for Isha this week")
    view = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert view["currency"] == {"status": "current", "reasons": []} and open_impacts(api, workspace) == []
    assert view["approval"]["watch_set"] == watch_before
    # Changing the AUTHORED clinical timing of the follow-up is clinical: it opens scoped review owned by Rao.
    obligation = api("mira").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}")[0]
    from tests.helpers import DAY
    api("mira").post(f"{W(workspace)}/follow-ups/{obligation['id']}/propose-due-change",
                     {"expected_revision": obligation["revision"], "due": DAY(28), "reason": "Patient asked to move the review later."})
    impacts = open_impacts(api, workspace)
    assert len(impacts) == 1 and impacts[0]["owner_name"] == "Dr. Rao" and impacts[0]["change"]["event_kind"] == "obligation_change"
    assert impacts[0]["scope_key"].endswith("/obligations") and impacts[0]["plan_version_id"] == s["plan"]
    after = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert after["currency"]["status"] == "review_needed" and after["disposition"] == "active" and after["plan"]["status"] == "approved"
    unchanged = api("mira").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}")[0]
    assert unchanged["due"]["value"] == 14 and unchanged["pending_change"]["due"]["value"] == 28  # not applied without clinical action


def test_reopened_applicability_draft_retains_accepted_version(api, workspace):
    s = meera_planned(api, workspace)
    draft = api("rao").post(f"{W(workspace)}/patients/{s['meera']}/applicability", {"protocol_version_id": s["protocol"]})["target"]["id"]
    rows = {a["id"]: a for a in api("rao").get(f"{W(workspace)}/patients/{s['meera']}/applicability")}
    assert rows[s["applicability"]]["status"] == "accepted" and rows[draft]["status"] == "draft" and rows[draft]["supersedes_id"] == s["applicability"]
    assert rows[draft]["criteria"] == rows[s["applicability"]]["criteria"]
    view = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert view["plan"]["status"] == "approved" and view["currency"]["status"] == "current" and view["disposition"] == "active"


def test_fact_correction_affects_only_dependants_and_preserves_historical_care(api, workspace):
    s = meera_planned(api, workspace)
    s.update(arun_planned(api, workspace, s))
    care = api("isha").post(f"{W(workspace)}/patients/{s['meera']}/care-events", {
        "status": "performed", "actual_time": {"value": 3, "unit": "day"}, "narrative": "Preparation visit checklist carried out.", "plan_version_id": s["plan"]})["target"]["id"]
    before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    intake(api, workspace, s["meera"], "meera-marrow-correction")  # corrects a fact pinned by Meera's signed packet
    impacts = open_impacts(api, workspace)
    assert [(i["patient_id"], i["needs_classification"], i["change"]["event_kind"]) for i in impacts] == [(s["meera"], False, "source_change")]
    assert impacts[0]["scope_key"].endswith("/reports/*") and impacts[0]["owner_name"] == "Dr. Rao" and impacts[0]["plan_version_id"] == s["plan"]
    after = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert after["plan"] == before["plan"] and after["approval"] == before["approval"] and after["disposition"] == "active"
    assert after["currency"]["status"] == "review_needed"
    assert api("rao").get(f"{W(workspace)}/plans/{s['arun_plan']}")["currency"]["status"] == "current"  # Arun is not a dependant
    events = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/care-events")
    assert [e["id"] for e in events] == [care] and events[0]["plan_version_id"] == s["plan"] and events[0]["status"] == "performed"
