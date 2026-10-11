"""Prepare a fictional walkthrough through authenticated HTTP commands, never database injection.

This simulates development actors. It does not establish qualified source review, independent
clinical appraisal, institutional approval or treatment delivery. Credentials are never printed.
The ignored journal resumes a partially completed run and retains command receipts.

Run with uv run --project apps/api python scripts/prepare-oncologist-demo.py --origin URL
--credentials /absolute/path/to/ignored-credentials.json --journal .geevi-local/demo-journal.json
"""
import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from tests import helpers as h


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    args.journal.parent.mkdir(parents=True, exist_ok=True)
    journal = json.loads(args.journal.read_text()) if args.journal.exists() else {"origin": args.origin, "commands": {}, "stages": {}}
    if journal["origin"] != args.origin:
        raise SystemExit("The journal belongs to a different server; choose a new journal path.")
    def persist():
        temporary = args.journal.with_suffix(".tmp")
        temporary.write_text(json.dumps(journal, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(args.journal)
    def stage(name, run):
        if name not in journal["stages"]:
            journal["stages"][name] = run()
            persist()
        return journal["stages"][name]
    passwords = json.loads(args.credentials.read_text())
    class Actor:
        def __init__(self, username):
            self.username = username
            self.http = httpx.Client(base_url=args.origin, timeout=90, headers={"Origin": args.origin})
            response = self.http.post("/api/v1/session", json={"username": username, "password": passwords[username]})
            if response.status_code != 200:
                raise SystemExit(f"Sign-in failed for development actor {username}: HTTP {response.status_code}")
            self.http.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        def get(self, path):
            response = self.http.get("/api/v1" + path)
            if response.status_code != 200:
                raise RuntimeError(f"Read failed: {path}: HTTP {response.status_code}")
            return response.json()
        def post(self, path, body=None, **kw):
            body = body or {}
            stable = {k: v for k, v in body.items() if k != "expected_revision"}
            key = hashlib.sha256(json.dumps([self.username, path, stable], sort_keys=True).encode()).hexdigest()
            saved = journal["commands"].setdefault(key, {"id": str(uuid.uuid4()), "body": body})
            if "result" in saved:
                return saved["result"]
            persist()  # freeze exact payload and command ID before sending, including unknown outcomes
            response = self.http.post("/api/v1" + path, json={"command_id": saved["id"], **saved["body"]})
            if response.status_code != kw.get("expect", 200):
                error = response.json().get("error", {})
                raise RuntimeError(f"Command failed: {path}: HTTP {response.status_code}, {error.get('code', 'unknown')}: {error.get('message', '')}")
            saved["result"] = response.json()
            persist()
            return saved["result"]
    actors = {name: Actor(name) for name in ("rao", "sen", "mira", "isha", "operator")}
    api = actors.__getitem__
    if "workspace_id" not in journal:
        name = "Oncologist walkthrough (fictional; simulated reviews)"
        existing = next((w for w in api("operator").get("/session")["workspaces"] if w["name"] == name), None)
        ws = existing["id"] if existing else api("operator").post("/dev/workspaces", {"name": name, "load": "none"})["workspace_id"]
        journal["workspace_id"] = ws
        persist()
    ws = journal["workspace_id"]
    base = h.W(ws)
    knowledge = stage("shared_knowledge", lambda: h.knowledge(api, ws))
    stage("conclude_shared_question", lambda: api("rao").post(f"{base}/research/questions/{knowledge['question']}/conclude", {
        "expected_revision": api("rao").get(f"{base}/research/questions/{knowledge['question']}")["question"]["revision"],
        "conclusion": "evidence_accepted", "note": "Simulated reviewer accepted the bounded, citation-linked starter appraisal for the fictional case-review workflow. Full-text appraisal and current-evidence review remain outstanding; no treatment recommendation is made."}))
    for reference in ("viale-a-2020", "beat-aml-2018"):
        stage(reference, lambda reference=reference: api("rao").post(f"{base}/research/reference-pack/{reference}/import"))
    meera = stage("meera", lambda: h.meera_planned(api, ws, knowledge))
    arun, _ = stage("arun_baseline", lambda: h.baseline(api, ws, "arun"))
    for source in ("arun-treatment-summary", "arun-response-assessment"):
        stage(source, lambda source=source: h.intake(api, ws, arun, source))
    stage("arun_assessment", lambda: api("rao").post(f"{base}/patients/{arun}/assessments", {
        "narrative": "Fictional follow-up assessment: AML reported on the diagnostic marrow, with one azacitidine/venetoclax cycle documented. Post-cycle marrow reports 8% blasts versus 34% on the diagnostic specimen. This is a recorded change in marrow findings; a formal remission category is not assigned. Febrile neutropenia and a treatment interruption are reported in the discharge summary. The next treatment decision requires clinician review.",
        "uncertainty": "MRD was not tested; current blood-count recovery, full molecular characterization and a formal fitness assessment are not supplied. No next-cycle prescription is inferred.",
        "dimension_notes": {
            "biology": "AML is reported by the diagnostic marrow source. Molecular classification remains incomplete in this chart.",
            "extent": "Marrow blast measurements: 34% at diagnosis and 8% after cycle one. Extramedullary disease assessment is not reported. This is an AML burden description, not a solid-tumor stage.",
            "fitness": "Hypertension is reported. Formal performance status, current organ assessment and transplant assessment are not documented.",
            "history": "Azacitidine plus venetoclax is documented as received in the fictional treatment summary; the administration and dose chart is not supplied. Febrile neutropenia and treatment interruption were recorded.",
            "current": "Fatigue and no fever at discharge are reported on Day 35. These are dated observations, not a current symptom check.",
            "priorities": "Lives alone; daughter assists by arrangement. Confirm support and travel preferences before the next visit."}}))
    stage("arun_discussion", lambda: api("mira").post(f"{base}/patients/{arun}/discussions", {
        "participants": ["Arun (fictional patient)", "Daughter (fictional caregiver)", "Mira"], "attributed_to": "patient",
        "goals": "Understand the response to the first cycle and the reason for the next review; involve his daughter in planning.",
        "preferences": "Morning appointments at the main campus; confirm transport and a written explanation of next steps."}))
    applicability = stage("arun_applicability", lambda: h.accept_applicability(api, ws, arun, knowledge["protocol"]))
    arun_plan = stage("arun_plan", lambda: h.draft_plan(api, ws, arun, applicability, intent="Review the post-cycle marrow, reported complications, recovery and patient goals before making the next treatment decision (fictional workflow plan).",
        alternatives="Review now with incomplete information or obtain outstanding investigations before an additional treatment decision; no regimen selection is made.",
        rationale="Recorded residual blasts, treatment interruption and incomplete MRD/fitness information require a documented review; trial results are contextual evidence, not this patient's outcome.",
        obligations=[{"id": "OBL-RESPONSE-REVIEW", "purpose": "Review response, count recovery and treatment-related problems with the patient", "due": h.DAY(42), "owner_username": "mira"}]))[0]
    stage("arun_submit", lambda: h.submit_plan(api, ws, arun_plan))
    stage("arun_sign", lambda: h.sign_plan(api, ws, arun_plan))
    tasks = stage("meera_tasks", lambda: h.make_tasks(api, ws, meera["plan"], knowledge["sop"]))
    task = tasks["STEP-CONFIRM-VENUE"]
    stage("send_handoff", lambda: h.task_do(api, ws, "mira", task["id"], "send"))
    stage("accept_handoff", lambda: h.task_do(api, ws, "isha", task["id"], "accept"))
    stage("complete_handoff", lambda: h.task_do(api, ws, "isha", task["id"], "complete", evidence="Fictional phone contact recorded: patient and sister confirmed the satellite venue and appointment time."))
    stage("meera_care", lambda: api("isha").post(f"{base}/patients/{meera['meera']}/care-events", {
        "status": "performed", "actual_time": h.DAY(3), "plan_version_id": meera["plan"],
        "narrative": "Fictional preparation visit recorded by Isha. Reports and missing molecular information were discussed; this is not evidence of chemotherapy administration."}))
    obligation = api("mira").get(f"{base}/follow-ups?patient_id={arun}")[0]
    stage("arun_scheduled_review", lambda: api("mira").post(f"{base}/follow-ups/{obligation['id']}/schedule", {"expected_revision": obligation["revision"], "scheduled_time": h.DAY(42)}))
    stage("arun_encounter_decision", lambda: api("rao").post(f"{base}/follow-ups/{obligation['id']}/decide", {
        "expected_revision": api("rao").get(f"{base}/follow-ups?patient_id={arun}")[0]["revision"],
        "decision": "more_information", "actual_time": h.DAY(42), "rationale": "Fictional review: response measurements and recorded complication discussed. Additional recovery and molecular information is needed before the next treatment decision.",
        "next": {"purpose": "Review outstanding recovery and molecular information; document the next individual decision", "due": h.DAY(49), "owner_username": "mira"}}))
    stage("arun_expected", lambda: api("mira").post(f"{base}/expected-inputs", {"patient_id": arun, "artifact": "Current blood count and treating-team response assessment", "report_type": "blood_panel", "owner_username": "mira", "next_action": "Obtain the recorded recovery results before the Day 49 review."}))
    stage("arun_question", lambda: api("rao").post(f"{base}/research/questions", {
        "title": "Response and harms after the documented first cycle: what evidence applies?", "question": "How do response definitions, adverse events and trial population limits inform the review of this fictional treated AML case?", "scope": "Response assessment, harms and individual applicability; distinguish trial outcomes from patient observations.",
        "intended_use": "An oncologist-led research question to inform case review; no automatic regimen selection.", "origin": {"kind": "case_question", "patient_id": arun}}))
    concern = stage("arun_concern", lambda: api("mira").post(f"{base}/patients/{arun}/concerns", {
        "narrative": "Fictional patient asks what the lower blast measurement means and whether treatment will continue; a clinician explanation is still required.", "attributed_to": "patient", "owner_username": "rao"}))["target"]["id"]
    stage("arun_concern_review", lambda: api("rao").post(f"{base}/concerns/{concern}/review", {"expected_revision": api("rao").get(f"{base}/concerns?patient_id={arun}")[0]["revision"], "narrative": "Question reviewed and retained for the next clinician discussion; no response or resolution is claimed.", "close": False}))
    result = {"workspace_id": ws, "arun_url": f"{args.origin}/w/{ws}/patients/{arun}", "meera_url": f"{args.origin}/w/{ws}/patients/{meera['meera']}", "research_url": f"{args.origin}/w/{ws}/research", "simulated_approvals": True}
    journal["result"] = result
    persist()
    print(json.dumps(result, indent=2))
    for actor in actors.values():
        actor.http.close()


if __name__ == "__main__":
    main()
