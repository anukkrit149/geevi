"""U3: longitudinal profile, trends and knowledge-cutoff snapshots."""
from tests.helpers import W, baseline, intake, register


def test_later_specimen_does_not_overwrite_earlier_data(api, workspace):
    meera = register(api, workspace, "meera")
    intake(api, workspace, meera, "meera-blood-day-minus-1")
    intake(api, workspace, meera, "meera-blood-day-6")
    profile = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")
    trend = next(t for t in profile["trends"] if t["analyte"] == "Hemoglobin")
    assert [(p["value_text"], p["effective_time"]["value"]) for p in trend["points"]] == [("8.4", -1), ("7.9", 6)]
    current = next(d for d in profile["dimensions"] if d["id"] == "current")
    assert sorted(o["value_text"] for o in current["observations"] if o["analyte"] == "Hemoglobin") == ["7.9", "8.4"]
    assert all(o["units"] == "g/dL" and o["reference_range"] == "12.0-15.5" for o in current["observations"] if o["analyte"] == "Hemoglobin")


def test_late_arriving_report_cannot_leak_into_prior_knowledge_snapshot(api, workspace):
    meera, _ = baseline(api, workspace, "meera")
    before = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")
    cutoff = before["knowledge_cutoff_seq"]
    # The molecular report describes Day 1 material but arrives now.
    intake(api, workspace, meera, "meera-molecular-preliminary")
    now = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")
    then = api("rao").get(f"{W(workspace)}/patients/{meera}/profile?as_of_seq={cutoff}")
    analytes = lambda p: {o["analyte"] for d in p["dimensions"] for o in d["observations"]}  # noqa: E731
    assert "NPM1" in analytes(now) and "NPM1" not in analytes(then) and analytes(then) == analytes(before)
    assert then["historical"] is True and then["knowledge_cutoff_seq"] == cutoff and now["historical"] is False
    npm1 = next(o for d in now["dimensions"] for o in d["observations"] if o["analyte"] == "NPM1")
    assert npm1["effective_time"]["value"] == 1 and npm1["recorded_seq"] > cutoff  # clinical time earlier than knowledge time


def test_correction_changes_current_profile_but_not_the_earlier_view(api, workspace):
    meera, _ = baseline(api, workspace, "meera")
    cutoff = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")["knowledge_cutoff_seq"]
    intake(api, workspace, meera, "meera-marrow-correction")
    value = lambda p: next(o["value_text"] for d in p["dimensions"] for o in d["observations"] if o["analyte"] == "Cellularity")  # noqa: E731
    assert value(api("rao").get(f"{W(workspace)}/patients/{meera}/profile")) == "80 %"
    assert value(api("rao").get(f"{W(workspace)}/patients/{meera}/profile?as_of_seq={cutoff}")) == "90 %"


def test_assessment_and_discussion_are_attributed_and_separate_from_observations(api, workspace):
    meera, docs = baseline(api, workspace, "meera")
    evidence = [docs["meera-marrow"][1]["Blast percentage"]]
    api("mira").fail(f"{W(workspace)}/patients/{meera}/assessments", {"narrative": "Coordinator attempting an assessment"}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/patients/{meera}/assessments", {
        "narrative": "Fictional encounter assessment recorded for workflow demonstration.", "evidence": evidence,
        "dimension_notes": {"fitness": "Functional assessment discussed at the encounter; formal score not yet recorded."},
        "uncertainty": "Final molecular classification outstanding."})
    api("mira").post(f"{W(workspace)}/patients/{meera}/discussions", {
        "participants": ["Meera (patient)", "Sister (caregiver)", "Mira"], "attributed_to": "patient",
        "goals": "Wants appointments near home where possible.", "preferences": "Prefers the satellite clinic for visits."})
    profile = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")
    assert profile["assessment"]["recorded_by_name"] == "Dr. Rao" and profile["assessment"]["evidence"] == evidence
    assert profile["discussion"]["attributed_to"] == "patient" and profile["discussion"]["recorded_by_name"] == "Mira"
    fitness = next(d for d in profile["dimensions"] if d["id"] == "fitness")
    assert "formal score not yet recorded" in fitness["clinician_note"] and all(o["analyte"] != "assessment" for o in fitness["observations"])
    extent = next(d for d in profile["dimensions"] if d["id"] == "extent")
    assert extent["observations"] == [] and "not assumed normal" in extent["unresolved"][0]
    assert "not clinical eligibility rules" in profile["validation_notice"]
