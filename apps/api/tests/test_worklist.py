"""U12 backend projections: the Today worklist and the patient timeline."""
from tests.helpers import (
    DAY,
    SCENARIO,
    W,
    accepted_evidence,
    make_tasks,
    meera_planned,
    publish_protocol_v2,
    request_exception,
    task_do,
)


def test_today_shows_each_account_only_its_own_owned_work(api, workspace):
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "send")
    request_exception(api, workspace, s["meera"], s["protocol"], "molecular")
    api("mira").post(f"{W(workspace)}/expected-inputs", {"patient_id": s["meera"], "artifact": "Final molecular report", "report_type": "molecular",
                                                        "owner_username": "mira", "next_action": "Chase the genetics laboratory"})
    _, _, second = accepted_evidence(api, workspace, "v2", "research-caregiver-contact")
    publish_protocol_v2(api, workspace, s["protocol"], [s["appraisal"], second])
    kinds = lambda user: api(user).get(f"{W(workspace)}/today")["counts"]  # noqa: E731
    assert kinds("isha") == {"task": 1}
    assert kinds("sen") == {"exception": 1}
    assert kinds("mira") == {"expected_input": 1, "follow_up": 1, "task": 3}
    rao = api("rao").get(f"{W(workspace)}/today")
    assert rao["counts"] == {"exception": 1, "impact": 1, "task": 3}
    impact = next(i for i in rao["items"] if i["kind"] == "impact")
    assert impact["owner"] == "Dr. Rao" and impact["next_action"] == "Record a disposition" and impact["patient_id"] == s["meera"]
    assert api("operator").get(f"{W(workspace)}/today", expect=403)["error"]["code"] == "actor_not_permitted"


def test_timeline_keeps_planned_accepted_and_actual_activity_distinct(api, workspace):
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "send")
    task_do(api, workspace, "isha", tasks["STEP-CONFIRM-VENUE"]["id"], "accept")
    api("isha").post(f"{W(workspace)}/patients/{s['meera']}/planned-events", {"event_type": "preparation_visit", "description": "Preparation visit", "scheduled_time": DAY(3)})
    api("isha").post(f"{W(workspace)}/patients/{s['meera']}/care-events", {"status": "performed", "actual_time": DAY(3), "narrative": "Preparation visit held.",
                                                                         "source": "external_report", "performer_name": "Outside nurse", "plan_version_id": s["plan"]})
    rows = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/timeline")
    assert [r["seq"] for r in rows] == sorted(r["seq"] for r in rows)
    lanes = {r["lane"] for r in rows}
    assert {"source", "decision", "handoff", "planned", "actual"} <= lanes
    assert [r["title"] for r in rows if r["lane"] == "handoff"] == ["Handoff sent: Confirm appointment venue and time with the patient",
                                                                   "Handoff accepted: Confirm appointment venue and time with the patient"]
    actual = next(r for r in rows if r["lane"] == "actual")
    assert actual["actor"] == "Outside nurse (transcribed by Isha)" and actual["clinical_time"]["value"] == 3
    assert any(r["title"].startswith("Plan v1 approved (demonstration signature)") for r in rows)
    assert SCENARIO["label"] == "fictional"
