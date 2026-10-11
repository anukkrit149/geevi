"""U7/AE5: currency is scoped. Unrelated writes survive and stale nothing; relevant ones block the signature."""
from tests.helpers import (
    DAY,
    W,
    draft_plan,
    intake,
    make_tasks,
    meera_planned,
    meera_ready,
    sign_plan,
    submit_plan,
    task_do,
)


def test_unrelated_task_update_in_another_session_does_not_stale_an_open_plan(api, workspace):
    s = meera_planned(api, workspace)
    tasks = make_tasks(api, workspace, s["plan"], s["sop"])
    # "Tab 1": Rao has a successor plan frozen for signature.
    successor, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]], intent="Successor plan open in another tab (fictional).")
    frozen = submit_plan(api, workspace, successor)
    seq_before = api("rao").get("/session")["workspaces"]
    # "Tab 2": unrelated writes advance the workspace sequence: task edits, a note, a concern, a scheduled event.
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "update", due=DAY(4), note="Moved by a day")
    task_do(api, workspace, "mira", tasks["STEP-CONFIRM-VENUE"]["id"], "send")
    task_do(api, workspace, "isha", tasks["STEP-CONFIRM-VENUE"]["id"], "accept")
    api("isha").post(f"{W(workspace)}/notes", {"text": "Clinic room B is closed on Friday."})
    api("mira").post(f"{W(workspace)}/patients/{s['meera']}/concerns", {"narrative": "Caregiver asked about parking at the clinic.", "attributed_to": "caregiver",
                                                                        "owner_username": "isha"})
    api("isha").post(f"{W(workspace)}/patients/{s['meera']}/planned-events", {"event_type": "preparation_visit", "description": "Preparation visit", "scheduled_time": DAY(3)})
    view = api("rao").get(f"{W(workspace)}/plans/{successor}")
    assert view["packet_changes"] == [] and view["packet"]["target_digest"] == frozen["digest"]
    seq_after = api("rao").get("/session")["workspaces"]
    advanced = [(a["sequence"], b["sequence"]) for a, b in zip(seq_before, seq_after, strict=True) if a["id"] == workspace][0]
    assert advanced[1] >= advanced[0] + 6  # the workspace moved on...
    sign_plan(api, workspace, successor)  # ...and the signature is still current
    task = next(t for t in api("mira").get(f"{W(workspace)}/tasks") if t["sop_step_id"] == "STEP-CONFIRM-VENUE")
    assert task["status"] == "accepted" and task["due"]["value"] == 4 and task["note"] == "Moved by a day"  # nothing was lost


def test_each_relevant_scope_change_is_explained_and_only_relevant_scopes_count(api, workspace):
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    submit_plan(api, workspace, plan_id)
    api("rao").post(f"{W(workspace)}/patients/{s['meera']}/assessments", {"narrative": "Updated fictional assessment after reviewing the film."})
    error = sign_plan(api, workspace, plan_id, expect=409)["error"]
    change = error["details"]["changes"][0]
    assert change["scope"].endswith("/assessment") and change["last_change"]["actor"] == "Dr. Rao" and change["current_revision"] == change["frozen_revision"] + 1
    assert len(error["details"]["changes"]) == 1
    rev = api("rao").get(f"{W(workspace)}/plans/{plan_id}")["plan"]["revision"]
    api("rao").post(f"{W(workspace)}/plans/{plan_id}/reopen", {"expected_revision": rev})
    submit_plan(api, workspace, plan_id)
    # Another patient's new report is a different scope and never stales Meera's packet.
    from tests.helpers import baseline
    baseline(api, workspace, "arun")
    sign_plan(api, workspace, plan_id)


def test_correction_of_a_pinned_fact_blocks_a_frozen_successor_until_reviewed(api, workspace):
    s = meera_ready(api, workspace)
    plan_id, _ = draft_plan(api, workspace, s["meera"], s["applicability"], [s["venue"]])
    submit_plan(api, workspace, plan_id)
    intake(api, workspace, s["meera"], "meera-marrow-correction")
    error = sign_plan(api, workspace, plan_id, expect=409)["error"]
    reads = [c for c in error["details"]["changes"] if "read" in c]
    assert len(reads) == 1 and "Cellularity is no longer current: Corrected by issuer report version 2" in reads[0]["reason"]
