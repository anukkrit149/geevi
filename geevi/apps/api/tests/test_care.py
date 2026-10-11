"""U9: SOP-derived handoffs, scheduling versus delivery, and attributed actual care."""
from tests.helpers import DAY, W, draft_plan, make_tasks, meera_planned, sign_plan, submit_plan, task_do


def test_sent_handoff_stays_unaccepted_until_isha_acts_and_returns_keep_owner_and_reason(api, workspace):
    s = meera_planned(api, workspace)
    api("isha").fail(f"{W(workspace)}/plans/{s['plan']}/tasks", {"sop_version_id": s["sop"]}, code="actor_not_permitted")
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    venue, prep = tasks["STEP-CONFIRM-VENUE"], tasks["STEP-PREP-VISIT"]
    assert venue["status"] == "draft" and venue["sop_version_id"] == s["sop"] and venue["sop_version_no"] == 1 and venue["plan_version_id"] == s["plan"]
    assert venue["expected_evidence"] == "Confirmation note naming who was contacted" and prep["depends_on"] == [venue["id"]]
    make_tasks(api, workspace, s["plan"], s["sop"])  # instantiating again creates no duplicates
    assert len(api("mira").get(f"{W(workspace)}/tasks?patient_id={s['meera']}")) == 4
    task_do(api, workspace, "mira", venue["id"], "send")
    sent = next(t for t in api("isha").get(f"{W(workspace)}/tasks?mine=true") if t["id"] == venue["id"])
    assert sent["status"] == "sent" and [e["event"] for e in sent["events"]] == ["created", "sent"]  # sent is not accepted
    api("mira").fail(f"{W(workspace)}/tasks/{venue['id']}/accept", {"expected_revision": sent["revision"]}, code="actor_not_permitted")
    api("isha").fail(f"{W(workspace)}/tasks/{venue['id']}/complete", {"expected_revision": sent["revision"], "evidence": "Done without accepting"}, code="wrong_state")
    task_do(api, workspace, "isha", venue["id"], "receive")
    task_do(api, workspace, "isha", venue["id"], "return", reason="Patient phone number is missing from the packet.")
    returned = next(t for t in api("mira").get(f"{W(workspace)}/tasks") if t["id"] == venue["id"])
    assert returned["status"] == "returned" and returned["owner_name"] == "Isha"
    assert returned["events"][-1]["reason"] == "Patient phone number is missing from the packet." and returned["events"][-1]["recorded_by_name"] == "Isha"
    task_do(api, workspace, "mira", venue["id"], "send")
    task_do(api, workspace, "isha", venue["id"], "accept")
    task_do(api, workspace, "isha", venue["id"], "block", reason="Clinic line unanswered; will retry tomorrow.")
    blocked = next(t for t in api("mira").get(f"{W(workspace)}/tasks") if t["id"] == venue["id"])
    assert blocked["status"] == "blocked" and blocked["owner_name"] == "Isha" and "retry tomorrow" in blocked["events"][-1]["reason"]
    task_do(api, workspace, "isha", venue["id"], "accept")
    # Dependencies and completion evidence are enforced.
    task_do(api, workspace, "mira", prep["id"], "send")
    task_do(api, workspace, "isha", prep["id"], "accept")
    api("isha").fail(f"{W(workspace)}/tasks/{prep['id']}/complete", {"expected_revision": 4, "evidence": "Checklist done at the visit."}, code="dependency_incomplete")
    api("isha").fail(f"{W(workspace)}/tasks/{venue['id']}/complete", {"expected_revision": 9, "evidence": "ok"}, code="evidence_required")
    task_do(api, workspace, "isha", venue["id"], "complete", evidence="Spoke to Meera's sister; satellite clinic, Day 3, 10:00 confirmed.")
    done = next(t for t in api("mira").get(f"{W(workspace)}/tasks") if t["id"] == venue["id"])
    assert done["status"] == "completed" and done["completion_evidence"]["by"] == "Isha"
    episode = api("rao").get(f"{W(workspace)}/patients/{s['meera']}")["episodes"][0]
    assert episode["status"] == "ongoing"  # completing tasks infers no discharge or outcome


def test_scheduling_creates_no_delivery_assertion(api, workspace):
    s = meera_planned(api, workspace)
    event = api("isha").post(f"{W(workspace)}/patients/{s['meera']}/planned-events", {
        "event_type": "preparation_visit", "description": "Preparation visit at the satellite clinic", "scheduled_time": DAY(3),
        "location": "Satellite clinic", "plan_version_id": s["plan"]})["target"]["id"]
    planned = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/planned-events")
    assert [(p["id"], p["status"]) for p in planned] == [(event, "scheduled")]
    assert api("rao").get(f"{W(workspace)}/patients/{s['meera']}/care-events") == []


def test_actual_care_statuses_preserve_source_time_and_attribution(api, workspace):
    s = meera_planned(api, workspace)
    path = f"{W(workspace)}/patients/{s['meera']}/care-events"
    api("mira").fail(path, {"status": "performed", "actual_time": DAY(3), "narrative": "Coordinator recording care", "plan_version_id": s["plan"]}, code="actor_not_permitted")
    api("isha").fail(path, {"status": "performed", "narrative": "No time recorded for this visit", "plan_version_id": s["plan"]}, code="actual_time_required")
    api("isha").post(path, {"status": "partial", "actual_time": DAY(3), "narrative": "Checklist started; consent leaflet not available on the day.", "plan_version_id": s["plan"]})
    api("isha").post(path, {"status": "deferred", "narrative": "Second part deferred at the patient's request.", "plan_version_id": s["plan"]})
    api("isha").post(path, {"status": "unknown", "narrative": "Outside clinic visit reported by phone; details not confirmed.", "plan_version_id": s["plan"]})
    # An external performer and the transcribing account stay distinct.
    api("isha").fail(path, {"status": "performed", "actual_time": DAY(4), "narrative": "Blood draw at outside clinic", "source": "external_report", "plan_version_id": s["plan"]},
                     code="performer_required")
    api("isha").post(path, {"status": "performed", "actual_time": DAY(4), "narrative": "Blood draw at the outside clinic, per faxed note.", "source": "external_report",
                            "performer_name": "Nurse at Fictional Lakeside Clinic", "plan_version_id": s["plan"]})
    events = api("rao").get(path)
    assert [e["status"] for e in events] == ["partial", "deferred", "unknown", "performed"]
    direct, external = events[0], events[3]
    assert direct["performer_name"] == "Isha" and direct["transcriber_name"] is None and direct["source"] == "direct" and direct["actual_time"]["value"] == 3
    assert external["performer_name"] == "Nurse at Fictional Lakeside Clinic" and external["transcriber_name"] == "Isha" and external["performer_account_id"] is None
    assert events[1]["actual_time"] is None and events[2]["actual_time"] is None


def test_late_event_references_older_plan_without_reactivating_it(api, workspace):
    s = meera_planned(api, workspace)
    successor, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]], intent="Second version of the individual plan (fictional).")
    submit_plan(api, workspace, successor)
    sign_plan(api, workspace, successor)
    api("isha").post(f"{W(workspace)}/patients/{s['meera']}/care-events", {
        "status": "performed", "actual_time": DAY(2), "narrative": "Late entry: preparation call made under the first plan.", "plan_version_id": s["plan"]})
    versions = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/plans")
    assert [(v["plan"]["status"], v["disposition"]) for v in versions] == [("superseded", "superseded"), ("approved", "active")]
    event = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/care-events")[0]
    assert event["plan_version_id"] == s["plan"]
    draft_only, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    api("isha").fail(f"{W(workspace)}/patients/{s['meera']}/care-events", {"status": "performed", "actual_time": DAY(5), "narrative": "Against an unsigned draft",
                                                                         "plan_version_id": draft_only}, code="invalid_association")


def test_pending_transfer_retains_original_responsibility_until_explicit_receipt(api, workspace):
    s = meera_planned(api, workspace)
    episode = api("rao").get(f"{W(workspace)}/patients/{s['meera']}")["episodes"][0]
    api("mira").fail(f"{W(workspace)}/episodes/{episode['id']}/transfer/request", {"expected_revision": 1, "to_service": "Fictional regional service",
                                                                                  "reason": "Coordinator cannot transfer"}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/episodes/{episode['id']}/transfer/request", {"expected_revision": 1, "to_service": "Fictional regional service",
                                                                                 "reason": "Patient is moving closer to the regional unit."})
    pending = api("rao").get(f"{W(workspace)}/patients/{s['meera']}")["episodes"][0]
    assert pending["status"] == "transfer_pending" and pending["responsible_team"] == "Fictional AML team" and pending["disposition"]["transfer"]["received"] is None
    api("rao").fail(f"{W(workspace)}/episodes/{episode['id']}/transfer/receive", {"expected_revision": 2, "receipt_note": "Sender cannot receive"}, code="actor_not_permitted")
    api("isha").post(f"{W(workspace)}/episodes/{episode['id']}/transfer/receive", {"expected_revision": 2, "receipt_note": "Received with the full preparation packet."})
    done = api("rao").get(f"{W(workspace)}/patients/{s['meera']}")["episodes"][0]
    assert done["status"] == "transferred" and done["responsible_team"] == "Fictional regional service"
    assert done["disposition"]["transfer"]["received"]["by"] == "Isha" and done["disposition"]["transfer"]["received"]["previous_team"] == "Fictional AML team"
