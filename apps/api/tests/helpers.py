"""Shared journey steps driven through the real HTTP API as the proper development accounts."""
import base64
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "department-journey"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
SCENARIO = json.loads((FIXTURES / "scenario.json").read_text())
INPUTS = {e["id"]: e for e in MANIFEST["inputs"]}
RESEARCH = {e["id"]: e for e in MANIFEST["research"]}


def raw(input_id: str) -> bytes:
    entry = INPUTS.get(input_id) or RESEARCH[input_id]
    return (FIXTURES / entry["file"]).read_bytes()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def W(ws: str) -> str:
    return f"/workspaces/{ws}"


def register(api, ws, key: str) -> str:
    return api("mira").post(f"{W(ws)}/patients", MANIFEST["patients"][key])["target"]["id"]


def upload(api, ws, patient_id, input_id, user="mira", expect=200, **over):
    entry = INPUTS[input_id]
    body = {"patient_id": patient_id, "filename": Path(entry["file"]).name, "media_type": entry["media_type"],
            "content_base64": b64(raw(input_id)), "doc_kind": entry["doc_kind"], "title": entry["title"],
            "received_time": entry["received_time"], "issuer": entry["issuer"], "accession": entry["accession"], **over}
    return api(user).post(f"{W(ws)}/sources", body, expect=expect)


def associate(api, ws, doc_id, patient_id, user="mira"):
    doc = api(user).get(f"{W(ws)}/sources/{doc_id}")["document"]
    return api(user).post(f"{W(ws)}/sources/{doc_id}/associate", {
        "expected_revision": doc["revision"], "patient_id": patient_id, "checked": True,
        "note": "Name, identifier and accession checked against the referral."})


def verify_all(api, ws, doc_id, user="mira", corrections=None):
    """Review every unreviewed candidate; `corrections` maps analyte -> corrected assertion."""
    out = {}
    for cand in api(user).get(f"{W(ws)}/sources/{doc_id}")["candidates"]:
        if cand["status"] != "unreviewed":
            continue
        analyte = cand["assertion"]["analyte"]
        body = {"expected_revision": cand["revision"], "disposition": "verified", "source_inspected": True}
        if corrections and analyte in corrections:
            body.update(disposition="corrected", reason="Transcription corrected against the original wording.", corrected=corrections[analyte])
        out[analyte] = api(user).post(f"{W(ws)}/candidates/{cand['id']}/review", body)["data"]["observation_id"]
    return out


def intake(api, ws, patient_id, input_id, **kw):
    """Receive, associate and source-verify one fixture document. Returns (document id, observation ids)."""
    doc_id = upload(api, ws, patient_id, input_id)["target"]["id"]
    associate(api, ws, doc_id, patient_id)
    return doc_id, verify_all(api, ws, doc_id, **kw)


FLOW_FIX = {"Myeloid markers": {"result_state": "reported_value"}}
MEERA_BASELINE = ["meera-referral", "meera-blood-day-minus-1", "meera-marrow", "meera-flow", "meera-cyto"]
ARUN_BASELINE = ["arun-referral", "arun-blood-day-2", "arun-marrow", "arun-cyto"]


def baseline(api, ws, key="meera"):
    """Register a patient and complete source intake for the baseline documents."""
    pid = register(api, ws, key)
    docs = {}
    for input_id in (MEERA_BASELINE if key == "meera" else ARUN_BASELINE):
        docs[input_id] = intake(api, ws, pid, input_id, corrections=FLOW_FIX if input_id == "meera-flow" else None)
    return pid, docs


# ---- knowledge side (F1/F5) ------------------------------------------------------------------

def decide(api, ws, user, packet_id, decision="approve", rationale=None, **kw):
    packet = next(p for p in api(user).get(f"{W(ws)}/review-packets?mine=false&status=") if p["packet"]["id"] == packet_id)["packet"]
    return api(user).post(f"{W(ws)}/review-packets/{packet_id}/decide",
                          {"expected_revision": packet["revision"], "decision": decision, "rationale": rationale}, **kw)


def add_research_source(api, ws, research_id="research-preparation-audit"):
    entry = RESEARCH[research_id]
    return api("rao").post(f"{W(ws)}/research/sources", {"title": entry["title"], "citation": entry["citation"], "source_label": "synthetic",
                                                         "filename": Path(entry["file"]).name, "media_type": "application/pdf",
                                                         "content_base64": b64(raw(research_id))})["target"]["id"]


def draft_appraisal(api, ws, which="v1", research_id="research-preparation-audit"):
    """Rao opens a question and drafts an appraisal citing a passage. Returns (question, source, appraisal) ids."""
    question = api("rao").post(f"{W(ws)}/research/questions", SCENARIO["research"][f"question_{which}"])["target"]["id"]
    source = add_research_source(api, ws, research_id)
    passages = next(s for s in api("rao").get(f"{W(ws)}/research/sources") if s["id"] == source)["passages"]
    finding = next(p for p in passages if p["text"].startswith("Finding 1"))
    appraisal = api("rao").post(f"{W(ws)}/research/questions/{question}/appraisals", {
        **SCENARIO["research"][f"appraisal_{which}"], "citations": [{"source_id": source, "passage_id": finding["id"]}]})["target"]["id"]
    return question, source, appraisal


def accept_appraisal(api, ws, appraisal_id):
    packet = api("rao").post(f"{W(ws)}/research/appraisals/{appraisal_id}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, ws, "sen", packet)
    return packet


def accepted_evidence(api, ws, which="v1", research_id="research-preparation-audit"):
    question, source, appraisal = draft_appraisal(api, ws, which, research_id)
    accept_appraisal(api, ws, appraisal)
    return question, source, appraisal


def protocol_body(which, evidence):
    spec = SCENARIO["protocol"]
    return {"title": spec["title"], "scope": spec["scope"], "summary": spec[which]["summary"], "requirements": spec[which]["requirements"], "evidence": evidence}


def publish_protocol_v1(api, ws, evidence, **publish):
    pid = api("rao").post(f"{W(ws)}/protocols", protocol_body("v1", evidence))["target"]["id"]
    packet = api("rao").post(f"{W(ws)}/protocols/{pid}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, ws, "sen", packet)
    rev = api("rao").get(f"{W(ws)}/protocols/{pid}")["version"]["revision"]
    api("rao").post(f"{W(ws)}/protocols/{pid}/publish", {"expected_revision": rev, **publish})
    return pid


def publish_protocol_v2(api, ws, v1_id, evidence):
    """Change proposal -> successor draft -> Sen approval -> Rao publication. Returns (v2 id, publish result)."""
    v2 = api("rao").post(f"{W(ws)}/protocols/{v1_id}/revise", {"rationale": "Add caregiver contact confirmation before handoff.", "evidence": evidence})["target"]["id"]
    api("rao").post(f"{W(ws)}/protocols/{v2}/save", {"expected_revision": 1, **protocol_body("v2", evidence)})
    packet = api("rao").post(f"{W(ws)}/protocols/{v2}/submit", {"expected_revision": 2, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, ws, "sen", packet)
    rev = api("rao").get(f"{W(ws)}/protocols/{v2}")["version"]["revision"]
    return v2, api("rao").post(f"{W(ws)}/protocols/{v2}/publish", {"expected_revision": rev})


def sop_body(protocol_id=None, **over):
    spec = SCENARIO["sop"]
    return {"title": spec["title"], "purpose": spec["purpose"], "escalation": spec["escalation"], "steps": spec["steps"],
            "protocol_version_id": protocol_id, **over}


def publish_sop(api, ws, protocol_id=None):
    sid = api("rao").post(f"{W(ws)}/sops", sop_body(protocol_id))["target"]["id"]
    packet = api("rao").post(f"{W(ws)}/sops/{sid}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, ws, "sen", packet)
    rev = api("rao").get(f"{W(ws)}/sops/{sid}")["version"]["revision"]
    api("rao").post(f"{W(ws)}/sops/{sid}/publish", {"expected_revision": rev})
    return sid


def knowledge(api, ws):
    """F1: accepted evidence, published protocol v1 and published SOP v1."""
    question, source, appraisal = accepted_evidence(api, ws)
    protocol = publish_protocol_v1(api, ws, [appraisal])
    return {"question": question, "source": source, "appraisal": appraisal, "protocol": protocol, "sop": publish_sop(api, ws, protocol)}


# ---- patient decisions (F3/F4) ---------------------------------------------------------------

DAY = lambda n: {"value": n, "unit": "day", "anchor": "episode-day-0", "precision": "day", "basis": "fictional relative demonstration day"}  # noqa: E731
OBLIGATION = {"id": "OBL-ROUTINE-REVIEW", "purpose": "Routine follow-up review of the preparation pathway", "due": DAY(14), "owner_username": "mira"}


def assess_and_discuss(api, ws, pid, goals="Wants appointments close to home where possible."):
    api("rao").post(f"{W(ws)}/patients/{pid}/assessments", {"narrative": "Fictional encounter assessment for workflow demonstration.",
                                                            "uncertainty": "Final molecular report outstanding."})
    return api("mira").post(f"{W(ws)}/patients/{pid}/discussions", {"participants": ["Patient", "Mira"], "attributed_to": "patient", "goals": goals,
                                                                   "preferences": "Prefers the satellite clinic for visits."})["target"]["id"]


def accept_applicability(api, ws, pid, protocol_id, **assessments):
    """Rao records criterion-level applicability. Defaults: everything matches; the molecular input is unknown."""
    review = api("rao").post(f"{W(ws)}/patients/{pid}/applicability", {"protocol_version_id": protocol_id})["target"]["id"]
    current = next(a for a in api("rao").get(f"{W(ws)}/patients/{pid}/applicability") if a["id"] == review)
    defaults = {"REQ-MOLECULAR": "unknown", **assessments}
    criteria = [{"requirement_id": c["requirement_id"], "assessment": defaults.get(c["requirement_id"], "match"),
                 "rationale": "Documented at the fictional encounter." if defaults.get(c["requirement_id"], "match") != "match" else "", "supporting": []}
                for c in current["criteria"]]
    api("rao").post(f"{W(ws)}/applicability/{review}/save", {"expected_revision": current["revision"], "criteria": criteria})
    api("rao").post(f"{W(ws)}/applicability/{review}/accept", {"expected_revision": current["revision"] + 1})
    return review


def request_exception(api, ws, pid, protocol_id, which="venue", **over):
    spec = SCENARIO["exceptions"][which]
    body = {"protocol_version_id": protocol_id, "requirement_id": spec["requirement_id"], "exception_type": spec["type"], "departure": spec["departure"],
            "rationale": spec["rationale"], "review_trigger": "Review if the patient's travel circumstances change.", **over}
    return api("rao").post(f"{W(ws)}/patients/{pid}/exceptions", body)["target"]["id"]


def decide_exception(api, ws, user, exception_id, decision="approve", **kw):
    current = next(e for e in api(user).get(f"{W(ws)}/exceptions") if e["id"] == exception_id)
    return api(user).post(f"{W(ws)}/exceptions/{exception_id}/decide", {"expected_revision": current["revision"], "decision": decision,
                                                                        "rationale": "Reviewed against the documented discussion."}, **kw)


def draft_plan(api, ws, pid, applicability_id, exception_ids=(), **over):
    discussion = api("rao").get(f"{W(ws)}/patients/{pid}/discussions")[-1]["id"]
    body = {"applicability_id": applicability_id, "discussion_id": discussion, "exception_ids": list(exception_ids),
            "intent": "Complete case preparation and arrange the planning visit as documented (fictional workflow intent).",
            "alternatives": "Main-campus visit discussed.", "rationale": "Individual arrangement recorded with the patient.",
            "obligations": [OBLIGATION], **over}
    return api("rao").post(f"{W(ws)}/patients/{pid}/plans", body)["target"]["id"], body


def submit_plan(api, ws, plan_id):
    plan = api("rao").get(f"{W(ws)}/plans/{plan_id}")["plan"]
    return api("rao").post(f"{W(ws)}/plans/{plan_id}/submit", {"expected_revision": plan["revision"]})["data"]


def sign_plan(api, ws, plan_id, user="rao", **kw):
    view = api("rao").get(f"{W(ws)}/plans/{plan_id}")
    body = {"expected_revision": view["plan"]["revision"], "packet_id": view["packet"]["id"], "digest": view["packet"]["target_digest"]}
    return api(user).post(f"{W(ws)}/plans/{plan_id}/approve", body, **kw)


def approved_plan(api, ws, pid, applicability_id, exception_ids=()):
    plan_id, _ = draft_plan(api, ws, pid, applicability_id, exception_ids)
    submit_plan(api, ws, plan_id)
    sign_plan(api, ws, plan_id)
    return plan_id


def meera_ready(api, ws, k=None):
    """Meera up to (not including) the plan: sources, assessment, discussion, applicability, approved venue exception."""
    k = k or knowledge(api, ws)
    pid, docs = baseline(api, ws, "meera")
    assess_and_discuss(api, ws, pid)
    applicability = accept_applicability(api, ws, pid, k["protocol"], **{"REQ-VENUE": "difference"})
    venue = request_exception(api, ws, pid, k["protocol"])
    decide_exception(api, ws, "rao", venue)
    return {**k, "meera": pid, "docs": docs, "applicability": applicability, "venue": venue}


def meera_planned(api, ws, k=None):
    s = meera_ready(api, ws, k)
    s["plan"] = approved_plan(api, ws, s["meera"], s["applicability"], [s["venue"]])
    return s


def arun_planned(api, ws, k):
    pid, docs = baseline(api, ws, "arun")
    assess_and_discuss(api, ws, pid, goals="Prefers morning appointments at the main campus.")
    applicability = accept_applicability(api, ws, pid, k["protocol"])
    return {"arun": pid, "arun_docs": docs, "arun_applicability": applicability, "arun_plan": approved_plan(api, ws, pid, applicability)}


def make_tasks(api, ws, plan_id, sop_id, owner="isha"):
    steps = [s["id"] for s in SCENARIO["sop"]["steps"]]
    api("mira").post(f"{W(ws)}/plans/{plan_id}/tasks", {"sop_version_id": sop_id, "owners": {s: owner for s in steps}, "due": {steps[0]: DAY(3)}})
    return {t["sop_step_id"]: t for t in api("mira").get(f"{W(ws)}/tasks") if t["plan_version_id"] == plan_id}


def task_do(api, ws, user, task_id, action, **body):
    task = next(t for t in api(user).get(f"{W(ws)}/tasks") if t["id"] == task_id)
    return api(user).post(f"{W(ws)}/tasks/{task_id}/{action}", {"expected_revision": task["revision"], **body})


def open_impacts(api, ws, pid=None):
    return api("rao").get(f"{W(ws)}/impacts?state=open" + (f"&patient_id={pid}" if pid else ""))


def resolve_impact(api, ws, impact_id, disposition, user="rao", **body):
    impact = api("rao").get(f"{W(ws)}/impacts/{impact_id}")
    return api(user).post(f"{W(ws)}/impacts/{impact_id}/resolve", {"expected_revision": impact["revision"], "disposition": disposition,
                                                                  "rationale": "Reviewed against the patient's documented basis.", **body})
