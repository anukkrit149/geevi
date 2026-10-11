"""U11: protocol v2 and source changes create reproducible, independent per-patient decisions."""
from app.services import command_service
from tests.helpers import (
    SCENARIO,
    W,
    accept_applicability,
    accepted_evidence,
    approved_plan,
    arun_planned,
    decide,
    intake,
    meera_planned,
    open_impacts,
    protocol_body,
    publish_protocol_v2,
    resolve_impact,
)


def _two_patients(api, ws):
    s = meera_planned(api, ws)
    s.update(arun_planned(api, ws, s))
    _, _, s["appraisal2"] = accepted_evidence(api, ws, "v2", "research-caregiver-contact")
    return s


def test_publishing_v2_creates_two_impacts_resolved_independently(api, workspace):
    """AE1: Meera retains v1; Arun adopts v2 only through a newly approved plan."""
    s = _two_patients(api, workspace)
    plans_before = {p: api("rao").get(f"{W(workspace)}/plans/{s[p]}") for p in ("plan", "arun_plan")}
    v2, published = publish_protocol_v2(api, workspace, s["protocol"], [s["appraisal"], s["appraisal2"]])
    assert published["data"]["impacts_created"] == 2
    impacts = {i["patient_id"]: i for i in open_impacts(api, workspace)}
    assert set(impacts) == {s["meera"], s["arun"]} and all(i["owner_name"] == "Dr. Rao" and i["needs_classification"] is False for i in impacts.values())
    assert impacts[s["meera"]]["change_event_id"] == impacts[s["arun"]]["change_event_id"] and impacts[s["meera"]]["change"]["source_id"] == v2
    # Publication changed no individual plan.
    for key, before in plans_before.items():
        after = api("rao").get(f"{W(workspace)}/plans/{s[key]}")
        assert after["plan"] == before["plan"] and after["approval"] == before["approval"] and after["currency"]["status"] == "review_needed"
    # Meera: retain v1 with rationale and a review trigger.
    api("rao").fail(f"{W(workspace)}/impacts/{impacts[s['meera']]['id']}/resolve", {"expected_revision": 1, "disposition": "retained", "rationale": "Keep the current plan"},
                    code="review_trigger_required")
    resolve_impact(api, workspace, impacts[s["meera"]]["id"], "retained", review_trigger="Revisit at the next routine review")
    remaining = open_impacts(api, workspace)
    assert [i["patient_id"] for i in remaining] == [s["arun"]]  # resolving Meera's impact leaves Arun's open
    # Arun: 'adopt' alone cannot close; it needs a linked, newly approved successor plan on v2.
    arun_impact = impacts[s["arun"]]["id"]
    api("rao").fail(f"{W(workspace)}/impacts/{arun_impact}/resolve", {"expected_revision": 1, "disposition": "adopted", "rationale": "Adopting version two"},
                    code="adoption_requires_approved_plan")
    api("rao").fail(f"{W(workspace)}/impacts/{arun_impact}/resolve", {"expected_revision": 1, "disposition": "adopted", "rationale": "Linking the old plan",
                                                                      "linked_plan_version_id": s["arun_plan"]}, code="adoption_requires_approved_plan")
    applicability_v2 = accept_applicability(api, workspace, s["arun"], v2)
    successor = approved_plan(api, workspace, s["arun"], applicability_v2)
    resolve_impact(api, workspace, arun_impact, "adopted", linked_plan_version_id=successor)
    assert open_impacts(api, workspace) == []
    meera_plan = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    assert meera_plan["plan"]["protocol_version_id"] == s["protocol"] and meera_plan["plan"]["status"] == "approved" and meera_plan["currency"]["status"] == "current"
    arun_versions = api("rao").get(f"{W(workspace)}/patients/{s['arun']}/plans")
    assert [(v["plan"]["protocol_version_id"], v["plan"]["status"]) for v in arun_versions] == [(s["protocol"], "superseded"), (v2, "approved")]
    # Every closed impact reconstructs its change, patient basis and authorised disposition.
    closed = {i["patient_id"]: i for i in api("sen").get(f"{W(workspace)}/impacts")}
    m, a = closed[s["meera"]], closed[s["arun"]]
    assert (m["state"], m["disposition"], m["review_trigger"], m["plan_version_id"]) == ("closed", "retained", "Revisit at the next routine review", s["plan"])
    assert (a["state"], a["disposition"], a["linked_plan_version_id"], a["plan_version_id"]) == ("closed", "adopted", successor, s["arun_plan"])
    assert m["change"]["event_kind"] == "protocol_published" and [h["event"] for h in a["history"]] == ["opened", "adopted"] and a["history"][-1]["by"] == "Dr. Rao"
    api("mira").fail(f"{W(workspace)}/impacts/{m['id']}/resolve", {"expected_revision": 2, "disposition": "retained", "rationale": "Coordinator resolving"}, code="actor_not_permitted")


def test_duplicate_event_yields_one_impact_and_a_second_change_keeps_its_own_reason(api, workspace):
    s = meera_planned(api, workspace)
    doc_id, _ = intake(api, workspace, s["meera"], "meera-marrow-addendum")  # association + review of one document = one change event
    first = open_impacts(api, workspace)
    assert len(first) == 1 and first[0]["change"]["dedupe_key"] == f"source:{doc_id}" and len(first[0]["change"]["detail"]["events"]) == 2
    assert first[0]["needs_classification"] is True and first[0]["next_action"] == "Classify relevance"
    intake(api, workspace, s["meera"], "meera-marrow-correction")  # a second, distinct change
    both = open_impacts(api, workspace)
    assert len(both) == 2 and both[0]["change_event_id"] != both[1]["change_event_id"]
    assert "addendum" in both[0]["change"]["description"] and "corrected" in both[1]["change"]["description"]
    assert both[1]["needs_classification"] is False  # a pinned fact was corrected: relevance is certain
    api("rao").post(f"{W(workspace)}/impacts/{both[0]['id']}/classify", {"expected_revision": both[0]["revision"], "relevant": False,
                                                                        "rationale": "Additive reticulin finding does not bear on the preparation pathway."})
    left = open_impacts(api, workspace)
    assert [i["id"] for i in left] == [both[1]["id"]]


def test_more_information_stays_open_and_owned(api, workspace):
    s = _two_patients(api, workspace)
    publish_protocol_v2(api, workspace, s["protocol"], [s["appraisal"], s["appraisal2"]])
    impact = next(i for i in open_impacts(api, workspace) if i["patient_id"] == s["meera"])
    result = resolve_impact(api, workspace, impact["id"], "more_information")
    assert result["data"] == {"state": "more_information", "disposition": None}
    again = open_impacts(api, workspace, s["meera"])[0]
    assert again["state"] == "more_information" and again["owner_name"] == "Dr. Rao" and again["next_action"].startswith("Record more information")
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}")["currency"]["status"] == "review_needed"
    resolve_impact(api, workspace, impact["id"], "not_applicable")
    assert open_impacts(api, workspace, s["meera"]) == []


def test_withdrawal_blocks_new_selection_preserves_history_and_nominates_review(api, workspace):
    s = _two_patients(api, workspace)
    version = api("rao").get(f"{W(workspace)}/protocols/{s['protocol']}")["version"]
    result = api("rao").post(f"{W(workspace)}/protocols/{s['protocol']}/withdraw", {"expected_revision": version["revision"],
                                                                                    "reason": "Withdrawn pending rewrite of the venue branch."})
    assert result["data"]["impacts_created"] == 2
    api("rao").fail(f"{W(workspace)}/patients/{s['meera']}/applicability", {"protocol_version_id": s["protocol"]}, code="protocol_not_selectable")
    impacts = open_impacts(api, workspace)
    assert {i["change"]["event_kind"] for i in impacts} == {"protocol_withdrawn"} and len(impacts) == 2
    view = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    # No automatic stop: the signed plan and its disposition are untouched, only review is nominated.
    assert view["plan"]["status"] == "approved" and view["disposition"] == "active" and view["approval"] is not None and view["currency"]["status"] == "review_needed"
    assert "stop" not in str(impacts[0]["change"]["description"]).lower()


def test_new_research_question_changes_no_patient_decision(api, workspace):
    s = meera_planned(api, workspace)
    before = api("rao").get(f"{W(workspace)}/plans/{s['plan']}")
    origin = {"kind": "case_origin", "patient_id": s["meera"], "note": "Raised from this fictional case"}
    api("rao").post(f"{W(workspace)}/research/questions", {**SCENARIO["research"]["question_v2"], "origin": origin})
    accepted_evidence(api, workspace, "v2", "research-caregiver-contact")  # even accepted new evidence changes nothing by itself
    assert api("rao").get(f"{W(workspace)}/plans/{s['plan']}") == before and open_impacts(api, workspace) == []


def test_failed_publication_persists_neither_version_nor_partial_impacts(api, workspace, monkeypatch):
    """AE1/U11.6: publication and its impact set commit or fail together."""
    s = _two_patients(api, workspace)
    v2 = api("rao").post(f"{W(workspace)}/protocols/{s['protocol']}/revise", {"rationale": "Add caregiver contact confirmation.", "evidence": [s["appraisal2"]]})["target"]["id"]
    api("rao").post(f"{W(workspace)}/protocols/{v2}/save", {"expected_revision": 1, **protocol_body("v2", [s["appraisal"], s["appraisal2"]])})
    packet = api("rao").post(f"{W(workspace)}/protocols/{v2}/submit", {"expected_revision": 2, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, workspace, "sen", packet)

    def explode(ctx):
        raise RuntimeError("simulated failure after impacts were nominated, before commit")

    monkeypatch.setattr(command_service, "_before_commit", explode)
    rao = api("rao")
    command = "33333333-3333-4333-8333-333333333333"
    failed = rao.http.post(f"/api/v1{W(workspace)}/protocols/{v2}/publish", json={"command_id": command, "expected_revision": 4}, headers=rao.headers())
    assert failed.status_code == 500
    monkeypatch.undo()
    assert api("rao").get(f"{W(workspace)}/protocols/{v2}")["version"]["lifecycle"] == "approved"
    assert api("rao").get(f"{W(workspace)}/protocols/{s['protocol']}")["version"]["lifecycle"] == "effective"
    assert api("rao").get(f"{W(workspace)}/impacts") == []
    done = api("rao").post(f"{W(workspace)}/protocols/{v2}/publish", {"expected_revision": 4}, command_id=command)  # same-id retry applies it once
    assert done["data"]["impacts_created"] == 2 and len(open_impacts(api, workspace)) == 2
    assert api("rao").post(f"{W(workspace)}/protocols/{v2}/publish", {"expected_revision": 4}, command_id=command)["replayed"] is True
    assert len(api("rao").get(f"{W(workspace)}/impacts")) == 2
