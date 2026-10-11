"""U10: concerns and routine follow-up are separate, owned duties."""
from tests.helpers import DAY, W, intake, meera_planned, open_impacts, resolve_impact

NEXT = {"purpose": "Next routine follow-up review", "due": DAY(28), "owner_username": "mira"}


def _obligation(api, ws, pid, index=0):
    return api("rao").get(f"{W(ws)}/follow-ups?patient_id={pid}")[index]


def test_information_review_with_an_explicit_next_duty_replaces_the_completed_review_obligation(api, workspace):
    s = meera_planned(api, workspace)
    old = _obligation(api, workspace, s["meera"])
    api("rao").post(f"{W(workspace)}/follow-ups/{old['id']}/decide", {
        "expected_revision": old["revision"], "decision": "more_information", "actual_time": DAY(14),
        "rationale": "The review occurred; additional information is needed for the next decision.", "next": NEXT})
    rows = api("rao").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}")
    assert [(r["state"], r["due"]["value"]) for r in rows] == [("fulfilled", 14), ("open", 28)]
    assert rows[1]["previous_obligation_id"] == old["id"] and rows[1]["owner_name"] == "Mira"


def test_acknowledged_concern_without_response_stays_open_and_owned(api, workspace):
    s = meera_planned(api, workspace)
    concern = api("mira").post(f"{W(workspace)}/patients/{s['meera']}/concerns", {
        "narrative": "Caregiver phoned: Meera is worried about getting to the satellite clinic on Day 3.", "attributed_to": "caregiver", "owner_username": "isha"})["target"]["id"]
    api("isha").post(f"{W(workspace)}/concerns/{concern}/acknowledge", {"expected_revision": 2})
    row = api("rao").get(f"{W(workspace)}/concerns?patient_id={s['meera']}")[0]
    assert row["status"] == "acknowledged" and row["owner_name"] == "Isha" and "not a response" in row["unresolved_duty"]
    assert [e["event"] for e in row["events"]] == ["reported", "acknowledged"] and row["attributed_to"] == "caregiver"
    api("rao").fail(f"{W(workspace)}/concerns/{concern}/review", {"expected_revision": 3, "narrative": "Closing without a response", "close": True}, code="response_required")
    api("mira").fail(f"{W(workspace)}/concerns/{concern}/respond", {"expected_revision": 3, "narrative": "Coordinator responding instead"}, code="actor_not_permitted")
    api("isha").post(f"{W(workspace)}/concerns/{concern}/respond", {"expected_revision": 3, "narrative": "Called back: transport arranged with the sister for Day 3."})
    api("isha").post(f"{W(workspace)}/concerns/{concern}/escalate", {"expected_revision": 4, "narrative": "Caregiver also asked a question the team cannot answer.",
                                                                    "to_service": "Fictional AML clinician on call", "owner_username": "rao"})
    escalated = api("rao").get(f"{W(workspace)}/concerns")[0]
    assert escalated["status"] == "escalated" and escalated["owner_name"] == "Dr. Rao" and escalated["responsible_service"] == "Fictional AML clinician on call"
    api("rao").post(f"{W(workspace)}/concerns/{concern}/review", {"expected_revision": 5, "narrative": "Reviewed the question with the caregiver by phone.", "close": True})
    closed = api("rao").get(f"{W(workspace)}/concerns")[0]
    assert closed["status"] == "closed" and [e["event"] for e in closed["events"]] == ["reported", "acknowledged", "responded", "escalated", "closed"]
    assert [e["recorded_by_name"] for e in closed["events"]] == ["Mira", "Isha", "Isha", "Isha", "Dr. Rao"]


def test_routine_review_needs_no_concern_retains_plan_and_creates_next_obligation(api, workspace):
    """AE4: scheduling is not delivery; an unchanged review keeps the same plan and records the next duty."""
    s = meera_planned(api, workspace)
    obligation = _obligation(api, workspace, s["meera"])
    assert obligation["authored"] is True and obligation["owner_name"] == "Mira" and obligation["state"] == "open" and obligation["due"]["value"] == 14
    api("mira").post(f"{W(workspace)}/follow-ups/{obligation['id']}/schedule", {"expected_revision": 1, "scheduled_time": DAY(14)})
    assert api("rao").get(f"{W(workspace)}/patients/{s['meera']}/care-events") == [] and api("rao").get(f"{W(workspace)}/concerns") == []
    planned = api("rao").get(f"{W(workspace)}/patients/{s['meera']}/planned-events")
    assert planned[0]["obligation_id"] == obligation["id"] and planned[0]["status"] == "scheduled"
    api("isha").post(f"{W(workspace)}/patients/{s['meera']}/care-events", {"status": "performed", "actual_time": DAY(14), "narrative": "Routine review visit attended.",
                                                                         "plan_version_id": s["plan"], "planned_event_id": planned[0]["id"]})
    api("mira").fail(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", {"expected_revision": 2, "decision": "continue_unchanged", "rationale": "Coordinator deciding",
                                                                             "next": NEXT}, code="actor_not_permitted")
    api("rao").fail(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", {"expected_revision": 2, "decision": "continue_unchanged",
                                                                            "rationale": "No change needed at this review."}, code="next_obligation_required")
    before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    result = api("rao").post(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", {
        "expected_revision": 2, "decision": "continue_unchanged", "rationale": "Reviewed at the routine visit; the documented plan continues unchanged.",
        "actual_time": DAY(14), "next": NEXT})["data"]
    assert result["plan_version_id"] == s["plan"]
    after = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert after["plan"] == before["plan"] and after["approval"] == before["approval"] and len(api("rao").get(f"{W(workspace)}/patients/{s['meera']}/plans")) == 1
    obligations = api("rao").get(f"{W(workspace)}/follow-ups?patient_id={s['meera']}")
    assert [(o["state"], o["due"]["value"]) for o in obligations] == [("fulfilled", 14), ("open", 28)]
    assert obligations[1]["previous_obligation_id"] == obligation["id"] and obligations[1]["owner_name"] == "Mira" and obligations[1]["plan_version_id"] == s["plan"]
    decision = obligations[0]["decisions"][0]
    assert decision["decision"] == "continue_unchanged" and decision["recorded_by_name"] == "Dr. Rao" and decision["next_obligation_id"] == obligations[1]["id"]
    assert decision["input_packet"]["plan_digest"] == before["plan"]["content_digest"] and decision["input_packet"]["profile_snapshot_id"]
    episode = api("rao").get(f"{W(workspace)}/patients/{s['meera']}")["episodes"][0]
    assert episode["status"] == "ongoing"  # the episode stays ongoing with its next duty visible


def test_unreviewed_new_result_blocks_unsupported_continuation(api, workspace):
    s = meera_planned(api, workspace)
    obligation = _obligation(api, workspace, s["meera"])
    intake(api, workspace, s["meera"], "meera-blood-day-6")  # follow-up result arrives
    body = {"expected_revision": 1, "decision": "continue_unchanged", "rationale": "Routine review; continue unchanged.", "next": NEXT}
    error = api("rao").fail(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", body, code="plan_review_needed")
    assert error["details"]["reasons"][0]["needs_classification"] is True and "Dr. Rao" in error["next_action"]
    impact = open_impacts(api, workspace, s["meera"])[0]
    api("rao").post(f"{W(workspace)}/impacts/{impact['id']}/classify", {"expected_revision": impact["revision"], "relevant": True,
                                                                       "rationale": "Follow-up counts are relevant to the routine review."})
    api("rao").fail(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", body, code="plan_review_needed")
    resolve_impact(api, workspace, impact["id"], "retained", review_trigger="Next routine review")
    api("rao").post(f"{W(workspace)}/follow-ups/{obligation['id']}/decide", body)
    # A non-continuation decision can still be recorded while input is outstanding.
    nxt = _obligation(api, workspace, s["meera"], 1)
    api("rao").post(f"{W(workspace)}/follow-ups/{nxt['id']}/decide", {"expected_revision": nxt["revision"], "decision": "more_information",
                                                                     "rationale": "Awaiting the final molecular report before deciding."})
    assert _obligation(api, workspace, s["meera"], 1)["state"] == "open"


def test_missed_review_keeps_unknown_outcome_through_reschedule_transfer_and_cancellation(api, workspace):
    s = meera_planned(api, workspace)
    obligation = _obligation(api, workspace, s["meera"])
    oid = obligation["id"]
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/schedule", {"expected_revision": 1, "scheduled_time": DAY(14)})
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/miss", {"expected_revision": 2, "reason": "Patient did not attend; reason not yet known."})
    missed = _obligation(api, workspace, s["meera"])
    assert missed["state"] == "missed" and missed["history"][-1]["outcome"] == "unknown" and missed["owner_name"] == "Mira"
    api("mira").fail(f"{W(workspace)}/follow-ups/{oid}/schedule", {"expected_revision": 3, "scheduled_time": DAY(16)}, code="reason_required")
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/schedule", {"expected_revision": 3, "scheduled_time": DAY(16), "reason": "Rebooked after the missed visit."})
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/transfer", {"expected_revision": 4, "owner_username": "isha", "reason": "Isha will coordinate the rebooked visit."})
    moved = _obligation(api, workspace, s["meera"])
    assert moved["state"] == "transferred" and moved["owner_name"] == "Isha" and moved["scheduled_time"]["value"] == 16 and moved["due"]["value"] == 14
    assert [h["event"] for h in moved["history"]] == ["created", "scheduled", "missed", "rescheduled", "transferred"]
    assert moved["history"][-1]["previous_owner"] == "Mira"
    extra = api("mira").post(f"{W(workspace)}/patients/{s['meera']}/follow-ups", {"purpose": "Administrative check of contact details", "due": DAY(20), "owner_username": "mira"})["target"]["id"]
    api("mira").post(f"{W(workspace)}/follow-ups/{extra}/cancel", {"expected_revision": 1, "reason": "Contact details confirmed by phone instead."})
    cancelled = next(o for o in api("rao").get(f"{W(workspace)}/follow-ups") if o["id"] == extra)
    assert cancelled["state"] == "cancelled" and cancelled["authored"] is False and cancelled["history"][-1]["reason"].startswith("Contact details")


def test_clinical_schedule_change_uses_scoped_review_but_administrative_edit_does_not(api, workspace):
    s = meera_planned(api, workspace)
    obligation = _obligation(api, workspace, s["meera"])
    oid = obligation["id"]
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/schedule", {"expected_revision": 1, "scheduled_time": DAY(13)})
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/schedule", {"expected_revision": 2, "scheduled_time": DAY(14), "reason": "Clinic room changed its opening day."})
    assert open_impacts(api, workspace) == [] and api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["currency"]["status"] == "current"
    api("mira").post(f"{W(workspace)}/follow-ups/{oid}/propose-due-change", {"expected_revision": 3, "due": DAY(30), "reason": "Family asked to delay the review."})
    impact = open_impacts(api, workspace)[0]
    body = {"expected_revision": 4, "decision": "continue_unchanged", "rationale": "Routine review; continue unchanged.", "next": NEXT}
    api("rao").fail(f"{W(workspace)}/follow-ups/{oid}/decide", body, code="plan_review_needed")
    resolve_impact(api, workspace, impact["id"], "retained", review_trigger="Raise again at the next routine review")
    assert _obligation(api, workspace, s["meera"])["due"]["value"] == 14  # the authored timing stands
    extra = api("mira").post(f"{W(workspace)}/patients/{s['meera']}/follow-ups", {"purpose": "Administrative reminder call", "due": DAY(10), "owner_username": "mira"})["target"]["id"]
    api("mira").fail(f"{W(workspace)}/follow-ups/{extra}/propose-due-change", {"expected_revision": 1, "due": DAY(11), "reason": "Not an authored obligation"}, code="not_authored")


def test_cancelling_authored_followup_opens_clinical_review_and_preserves_signed_plan(api, workspace):
    s = meera_planned(api, workspace)
    before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    obligation = _obligation(api, workspace, s["meera"])
    api("mira").post(f"{W(workspace)}/follow-ups/{obligation['id']}/cancel", {"expected_revision": obligation["revision"], "reason": "Patient requested cancellation of the scheduled duty."})
    after = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert after["approval"]["id"] == before["approval"]["id"] and after["plan"]["status"] == "approved"
    assert after["currency"]["status"] == "review_needed" and len(open_impacts(api, workspace)) == 1
