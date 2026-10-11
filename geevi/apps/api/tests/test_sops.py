"""U6: the departmental SOP has its own versions, steps and review lifecycle."""
from tests.helpers import SCENARIO, W, accepted_evidence, decide, publish_protocol_v1, publish_sop, sop_body


def test_sop_requires_independent_review_and_is_separate_from_the_protocol(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    protocol = publish_protocol_v1(api, workspace, [appraisal])
    before = api("rao").get(f"{W(workspace)}/protocols/{protocol}")["version"]
    sid = api("rao").post(f"{W(workspace)}/sops", sop_body(protocol))["target"]["id"]
    api("rao").fail(f"{W(workspace)}/sops/{sid}/publish", {"expected_revision": 1}, code="required_review_absent")
    api("rao").fail(f"{W(workspace)}/sops/{sid}/submit", {"expected_revision": 1, "reviewer_username": "isha"}, code="reviewer_not_permitted")
    packet = api("rao").post(f"{W(workspace)}/sops/{sid}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, workspace, "sen", packet)
    api("mira").fail(f"{W(workspace)}/sops/{sid}/publish", {"expected_revision": 3}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/sops/{sid}/publish", {"expected_revision": 3})
    detail = api("isha").get(f"{W(workspace)}/sops/{sid}")
    sop = detail["version"]
    assert sop["lifecycle"] == "effective" and sop["purpose"] == SCENARIO["sop"]["purpose"] and sop["protocol_version_id"] == protocol
    assert [(s["id"], s["role"]) for s in sop["steps"]][0] == ("STEP-CONFIRM-VENUE", "Care team") and all(s["expected_evidence"] for s in sop["steps"])
    assert sop["escalation"] == "Fictional AML coordinator desk" and detail["reviews"][0]["decisions"][0]["recorded_by_name"] == "Dr. Sen"
    assert api("rao").get(f"{W(workspace)}/protocols/{protocol}")["version"] == before  # publishing an SOP never alters the protocol


def test_invalid_steps_are_rejected(api, workspace):
    steps = [{"id": "STEP-A", "title": "Do a thing", "role": "Care team", "expected_evidence": "Note", "depends_on": ["STEP-MISSING"]}]
    sid = api("rao").post(f"{W(workspace)}/sops", sop_body(steps=steps))["target"]["id"]
    api("rao").fail(f"{W(workspace)}/sops/{sid}/submit", {"expected_revision": 1, "reviewer_username": "sen"}, code="invalid_steps")


def test_sop_revision_leaves_protocol_and_old_version_intact(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    protocol = publish_protocol_v1(api, workspace, [appraisal])
    v1 = publish_sop(api, workspace, protocol)
    old = api("rao").get(f"{W(workspace)}/sops/{v1}")["version"]
    protocol_before = api("rao").get(f"{W(workspace)}/protocols/{protocol}")["version"]
    v2 = api("rao").post(f"{W(workspace)}/sops/{v1}/revise", {"rationale": "Add an explicit escalation contact step."})["target"]["id"]
    steps = [*SCENARIO["sop"]["steps"], {"id": "STEP-ESCALATE", "title": "Escalate unanswered handoffs", "role": "Coordinator", "expected_evidence": "Escalation note"}]
    api("rao").post(f"{W(workspace)}/sops/{v2}/save", {"expected_revision": 1, **sop_body(protocol, steps=steps)})
    packet = api("rao").post(f"{W(workspace)}/sops/{v2}/submit", {"expected_revision": 2, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, workspace, "sen", packet)
    api("rao").post(f"{W(workspace)}/sops/{v2}/publish", {"expected_revision": 4})
    family = api("rao").get(f"{W(workspace)}/sops/{v2}")["family"]
    assert [(v["version_no"], v["lifecycle"], len(v["steps"])) for v in family] == [(1, "superseded", 4), (2, "effective", 5)]
    kept = api("rao").get(f"{W(workspace)}/sops/{v1}")["version"]
    assert kept["content_digest"] == old["content_digest"] and kept["steps"] == old["steps"]
    assert api("rao").get(f"{W(workspace)}/protocols/{protocol}")["version"] == protocol_before
