"""U5: evidence is reviewed independently of protocol publication and patient approval."""
from tests.helpers import W, accept_appraisal, accepted_evidence, b64, decide, draft_appraisal, raw, register


def test_sen_accepts_cited_appraisal_without_publishing_or_approving_anything(api, workspace):
    register(api, workspace, "meera")
    question, source, appraisal = draft_appraisal(api, workspace)
    accept_appraisal(api, workspace, appraisal)
    detail = api("rao").get(f"{W(workspace)}/research/questions/{question}")
    accepted = detail["appraisals"][0]
    assert accepted["status"] == "accepted" and accepted["citations"][0]["source_id"] == source and accepted["content"]["study_design"].startswith("Retrospective")
    decision = detail["reviews"][0]["decisions"][0]
    assert decision["decision"] == "approve" and decision["recorded_by_name"] == "Dr. Sen" and decision["target_digest"] == accepted["content_digest"]
    assert detail["reviews"][0]["packet"]["policy"]["rule"]["independent_of_author"] is True
    # R9: acceptance publishes no protocol and touches no patient record.
    assert api("rao").get(f"{W(workspace)}/protocols") == [] and api("rao").get(f"{W(workspace)}/sops") == []
    assert "no patient recommendation" in detail["recommendation_notice"]
    # The evidence file and its cited passage reload through the same API/database.
    content = api("sen").http.get(f"/api/v1{W(workspace)}/research/sources/{source}/content")
    assert content.status_code == 200 and content.content == raw("research-preparation-audit")
    passage = next(p for s in api("sen").get(f"{W(workspace)}/research/sources") if s["id"] == source for p in s["passages"]
                   if p["id"] == accepted["citations"][0]["passage_id"])
    assert passage["text"].startswith("Finding 1") and len(passage["region"]) == 4


def test_missing_or_non_independent_reviewer_blocks_acceptance(api, workspace):
    _, _, appraisal = draft_appraisal(api, workspace)
    path = f"{W(workspace)}/research/appraisals/{appraisal}/submit"
    api("rao").fail(path, {"expected_revision": 1}, code="independent_reviewer_required")
    api("rao").fail(path, {"expected_revision": 1, "reviewer_username": "rao"}, code="reviewer_not_permitted")  # author holds no review grant
    api("rao").fail(path, {"expected_revision": 1, "reviewer_username": "mira"}, code="reviewer_not_permitted")
    packet = api("rao").post(path, {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    # Only the assigned reviewer's own session can decide; the author cannot approve their own work.
    for user in ("rao", "mira", "operator"):
        error = api(user).fail(f"{W(workspace)}/review-packets/{packet}/decide", {"expected_revision": 1, "decision": "approve", "actor": "sen"})
        assert error["code"] == "actor_not_permitted"
    assert api("rao").get(f"{W(workspace)}/research/appraisals")[0]["status"] == "in_review"
    assert [p["packet"]["id"] for p in api("sen").get(f"{W(workspace)}/review-packets")] == [packet]
    assert api("rao").get(f"{W(workspace)}/review-packets") == []


def test_objection_blocks_acceptance_until_successor_and_history_is_kept(api, workspace):
    question, _, appraisal = draft_appraisal(api, workspace)
    first = api("rao").post(f"{W(workspace)}/research/appraisals/{appraisal}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    api("sen").fail(f"{W(workspace)}/review-packets/{first}/decide", {"expected_revision": 1, "decision": "object"}, code="reason_required")
    decide(api, workspace, "sen", first, "object", "Limitations understate the absence of a comparison group.")
    api("sen").fail(f"{W(workspace)}/review-packets/{first}/decide", {"expected_revision": 2, "decision": "approve"}, code="unresolved_objection")
    api("rao").fail(f"{W(workspace)}/research/appraisals/{appraisal}/save", {"expected_revision": 3, "findings": "edit in place"}, code="immutable_version")
    successor = api("rao").post(f"{W(workspace)}/research/appraisals/{appraisal}/revise")["target"]["id"]
    current = next(a for a in api("rao").get(f"{W(workspace)}/research/appraisals") if a["id"] == successor)
    api("rao").post(f"{W(workspace)}/research/appraisals/{successor}/save", {
        "expected_revision": 1, **current["content"], "limitations": "No comparison group; invented single-site data; direction of association unknown.",
        "citations": current["citations"]})
    second = api("rao").post(f"{W(workspace)}/research/appraisals/{successor}/submit", {"expected_revision": 2, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, workspace, "sen", second, "approve", "Limitations now stated plainly.")
    detail = api("rao").get(f"{W(workspace)}/research/questions/{question}")
    assert [(a["version_no"], a["status"]) for a in detail["appraisals"]] == [(1, "changes_requested"), (2, "accepted")]
    history = [(d["decision"], d["rationale"]) for r in detail["reviews"] for d in r["decisions"]]
    assert history == [("object", "Limitations understate the absence of a comparison group."), ("approve", "Limitations now stated plainly.")]


def test_reopened_draft_retains_the_earlier_accepted_version(api, workspace):
    question, _, appraisal = accepted_evidence(api, workspace)
    draft = api("rao").post(f"{W(workspace)}/research/appraisals/{appraisal}/revise")["target"]["id"]
    rows = {a["id"]: a for a in api("rao").get(f"{W(workspace)}/research/appraisals")}
    assert rows[appraisal]["status"] == "accepted" and rows[draft]["status"] == "draft" and rows[draft]["supersedes_id"] == appraisal
    assert [a["id"] for a in api("rao").get(f"{W(workspace)}/research/appraisals?status=accepted")] == [appraisal]
    api("rao").fail(f"{W(workspace)}/research/appraisals/{appraisal}/revise", code="revision_in_progress")


def test_source_amendment_or_withdrawal_creates_dependent_review_work(api, workspace):
    _, source, appraisal = accepted_evidence(api, workspace)
    amended = api("rao").post(f"{W(workspace)}/research/sources/{source}/amend", {
        "expected_revision": 1, "reason": "Authors issued a corrected version of the note.", "media_type": "application/pdf",
        "content_base64": b64(raw("research-caregiver-contact"))})
    assert amended["data"]["dependants_flagged"] == 1
    row = next(a for a in api("rao").get(f"{W(workspace)}/research/appraisals") if a["id"] == appraisal)
    assert row["status"] == "accepted" and row["review_needed"] is True and "amended" in row["review_needed_reason"]
    work = api("rao").get(f"{W(workspace)}/work-items")
    assert [(w["work_kind"], w["target_id"], w["owner_name"]) for w in work] == [("dependent_review", appraisal, "Dr. Rao")]
    sources = {s["id"]: s for s in api("rao").get(f"{W(workspace)}/research/sources")}
    assert sources[source]["status"] == "amended" and sources[amended["target"]["id"]]["version_no"] == 2
    # A new appraisal cannot cite the superseded source version.
    api("rao").post(f"{W(workspace)}/research/appraisals/{appraisal}/revise")
    draft = next(a for a in api("rao").get(f"{W(workspace)}/research/appraisals") if a["status"] == "draft")
    api("rao").fail(f"{W(workspace)}/research/appraisals/{draft['id']}/submit", {"expected_revision": 1, "reviewer_username": "sen"}, code="source_support_not_current")
    withdrawn = api("rao").post(f"{W(workspace)}/research/sources/{amended['target']['id']}/withdraw", {"expected_revision": 1, "reason": "Withdrawn by its authors."})
    assert withdrawn["data"]["dependants_flagged"] == 1 and len(api("rao").get(f"{W(workspace)}/work-items")) == 2


def test_insufficient_evidence_conclusion_produces_no_recommendation(api, workspace):
    from tests.helpers import SCENARIO
    meera = register(api, workspace, "meera")
    origin = {"kind": "case_origin", "note": "Raised while preparing a fictional case", "patient_id": meera}
    q = api("rao").post(f"{W(workspace)}/research/questions", {**SCENARIO["research"]["question_insufficient"], "origin": origin})["target"]["id"]
    api("rao").fail(f"{W(workspace)}/research/questions/{q}/conclude", {"expected_revision": 1, "conclusion": "evidence_accepted", "note": "Looks fine to me"}, code="no_accepted_evidence")
    api("sen").fail(f"{W(workspace)}/research/questions/{q}/conclude", {"expected_revision": 1, "conclusion": "insufficient_evidence", "note": "Not my question"}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/research/questions/{q}/conclude", {"expected_revision": 1, "conclusion": "insufficient_evidence",
                                                                      "note": "No local or imported evidence addresses weekend scheduling."})
    question = api("rao").get(f"{W(workspace)}/research/questions/{q}")["question"]
    assert question["status"] == "concluded" and question["conclusion"] == "insufficient_evidence" and question["origin"]["patient_id"] == meera
    assert api("rao").get(f"{W(workspace)}/protocols") == []
    audit = api("rao").get(f"{W(workspace)}/audit")
    assert {e["target_kind"] for e in audit} <= {"research_question", "patient"}  # nothing else was written
