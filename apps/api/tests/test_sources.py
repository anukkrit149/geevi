"""U3: independent sources, identities, originals and versioned observations."""
import hashlib

from tests.helpers import INPUTS, W, associate, b64, intake, raw, register, upload, verify_all


def test_same_accession_from_different_issuers_stays_distinct(api, workspace):
    meera, arun = register(api, workspace, "meera"), register(api, workspace, "arun")
    intake(api, workspace, meera, "meera-cyto")
    intake(api, workspace, arun, "arun-cyto")
    m_reports = api("rao").get(f"{W(workspace)}/reports?patient_id={meera}")
    a_reports = api("rao").get(f"{W(workspace)}/reports?patient_id={arun}")
    assert m_reports[0]["accession"] == a_reports[0]["accession"] == "CYT-3303"
    assert m_reports[0]["issuer"] != a_reports[0]["issuer"] and m_reports[0]["family_id"] != a_reports[0]["family_id"]
    karyotypes = {o["patient_id"]: o["value_text"] for p in (meera, arun) for o in api("rao").get(f"{W(workspace)}/observations?patient_id={p}") if o["analyte"] == "Karyotype"}
    assert karyotypes == {meera: "46,XX[20]", arun: "46,XY[20]"}


def test_wrong_patient_source_is_quarantined(api, workspace):
    meera, arun = register(api, workspace, "meera"), register(api, workspace, "arun")
    result = upload(api, workspace, meera, "arun-blood-day-2")  # names Arun's identifier
    doc_id = result["target"]["id"]
    assert result["data"]["association_status"] == "quarantined"
    doc = api("mira").get(f"{W(workspace)}/sources/{doc_id}")["document"]
    assert doc["patient_id"] is None and doc["claimed_identity"]["value"] == "GEEVI-DEMO-0002"
    assert api("rao").get(f"{W(workspace)}/observations?patient_id={meera}") == []
    unresolved = api("rao").get(f"{W(workspace)}/patients/{meera}/profile")["unresolved"]
    assert any(u["kind"] == "association" and "quarantined" in u["text"] for u in unresolved)
    # It cannot be forced onto Meera, and findings cannot be reviewed while quarantined.
    error = api("mira").fail(f"{W(workspace)}/sources/{doc_id}/associate", {"expected_revision": 1, "patient_id": meera, "checked": True,
                                                                           "note": "Trying to attach it anyway"}, code="invalid_association")
    assert error["details"]["claimed_identifier"] == "GEEVI-DEMO-0002"
    cand = api("mira").get(f"{W(workspace)}/sources/{doc_id}")["candidates"][0]
    api("mira").fail(f"{W(workspace)}/candidates/{cand['id']}/review", {"expected_revision": 1, "disposition": "verified", "source_inspected": True},
                     code="identity_review_required")
    associate(api, workspace, doc_id, arun)  # the patient it names
    assert api("mira").get(f"{W(workspace)}/sources/{doc_id}")["document"]["patient_id"] == arun


def test_original_bytes_hash_and_region_are_preserved(api, workspace):
    meera = register(api, workspace, "meera")
    doc_id, observations = intake(api, workspace, meera, "meera-marrow")
    content = api("rao").http.get(f"/api/v1{W(workspace)}/sources/{doc_id}/content")
    assert content.status_code == 200 and content.content == raw("meera-marrow")
    assert content.headers["content-type"] == "application/pdf" and "sandbox" in content.headers["content-security-policy"]
    assert content.headers["x-content-sha256"] == INPUTS["meera-marrow"]["sha256"] == hashlib.sha256(content.content).hexdigest()
    bundle = api("rao").get(f"{W(workspace)}/sources/{doc_id}")
    # Multi-specimen report: each finding carries its own part and exact source region.
    by = {(o["analyte"], o["specimen_label"]): o for o in bundle["observations"]}
    assert set(by) == {("Blast percentage", "Part A"), ("Morphology", "Part A"), ("Cellularity", "Part B"), ("Reported diagnosis", "Part B")}
    cell = by[("Cellularity", "Part B")]
    assert cell["exact_wording"] == "Cellularity: 90 %" and cell["value_number"] == "90" and cell["source_ref"]["page"] == 1
    x0, y0, x1, y1 = cell["source_ref"]["region"]
    line = next(line for line in bundle["document"]["pages"][0]["lines"] if line["bbox"] == [x0, y0, x1, y1])
    assert line["text"] == "Cellularity: 90 %"
    assert len({s["id"] for s in bundle["specimens"]}) == 2 and cell["specimen_id"] != by[("Blast percentage", "Part A")]["specimen_id"]
    assert set(observations) == {"Blast percentage", "Morphology", "Cellularity", "Reported diagnosis"}


def test_duplicate_bytes_are_not_stored_twice(api, workspace):
    meera = register(api, workspace, "meera")
    first = upload(api, workspace, meera, "meera-referral")
    error = api("mira").fail(f"{W(workspace)}/sources", {"patient_id": meera, "filename": "copy.pdf", "media_type": "application/pdf",
                                                         "content_base64": b64(raw("meera-referral")), "doc_kind": "referral"}, code="duplicate_source", status=409)
    assert error["target"]["id"] == first["target"]["id"]
    assert len(api("mira").get(f"{W(workspace)}/sources?patient_id={meera}")) == 1


def test_result_states_stay_distinct(api, workspace):
    meera = register(api, workspace, "meera")
    intake(api, workspace, meera, "meera-molecular-preliminary")
    intake(api, workspace, meera, "meera-cyto")
    intake(api, workspace, meera, "meera-referral")
    states = {o["analyte"]: o["result_state"] for o in api("rao").get(f"{W(workspace)}/observations?patient_id={meera}")}
    assert states["NPM1"] == "pending" and states["FLT3-ITD"] == "not_detected" and states["TP53"] == "untested"
    assert states["IDH1"] == "indeterminate" and states["FISH panel"] == "insufficient_sample" and states["Performance status"] == "unreported"
    biology = next(d for d in api("rao").get(f"{W(workspace)}/patients/{meera}/profile")["dimensions"] if d["id"] == "biology")
    text = " ".join(biology["unresolved"])
    for phrase in ("result pending", "not tested", "indeterminate result", "insufficient sample"):
        assert phrase in text


def test_additive_addendum_and_correction_affect_only_their_scope(api, workspace):
    meera = register(api, workspace, "meera")
    _, original = intake(api, workspace, meera, "meera-marrow")
    add_doc, added = intake(api, workspace, meera, "meera-marrow-addendum")
    current = {(o["analyte"], o["specimen_label"]): o for o in api("rao").get(f"{W(workspace)}/observations?patient_id={meera}")}
    assert len(current) == 5 and current[("Morphology", "Part B")]["id"] == added["Morphology"]  # nothing superseded
    assert current[("Morphology", "Part A")]["id"] == original["Morphology"]
    fix_doc, fixed = intake(api, workspace, meera, "meera-marrow-correction")
    history = api("rao").get(f"{W(workspace)}/observations?patient_id={meera}&include_history=true")
    old = next(o for o in history if o["id"] == original["Cellularity"])
    new = next(o for o in history if o["id"] == fixed["Cellularity"])
    assert old["status"] == "superseded" and old["value_text"] == "90 %" and "Corrected by issuer" in old["superseded_reason"]
    assert new["status"] == "current" and new["value_text"] == "80 %" and new["key"] == old["key"] and new["version_no"] == 2 and new["supersedes_id"] == old["id"]
    untouched = [o for o in history if o["id"] in (original["Blast percentage"], original["Morphology"], original["Reported diagnosis"], added["Morphology"])]
    assert all(o["status"] == "current" for o in untouched)
    reports = sorted(api("rao").get(f"{W(workspace)}/reports?patient_id={meera}"), key=lambda r: r["version_no"])
    assert [r["relation_kind"] for r in reports] == ["original", "additive_addendum", "correction"]
    assert reports[2]["predecessor_id"] == reports[1]["id"] and reports[2]["affected_scope"] == ["Part B Cellularity"]


def test_newest_date_alone_never_supersedes(api, workspace):
    """A re-sent accession without a stated relation stays unresolved and supersedes nothing."""
    meera = register(api, workspace, "meera")
    _, original = intake(api, workspace, meera, "meera-marrow")
    # A blood panel is (mis)filed under the marrow accession with no stated relation to it.
    late = upload(api, workspace, meera, "meera-blood-day-6", accession="MAR-3301", issuer="Fictional Northside Pathology")
    associate(api, workspace, late["target"]["id"], meera)
    reports = api("rao").get(f"{W(workspace)}/reports?patient_id={meera}")
    unresolved = next(r for r in reports if r["id"] == late["data"]["report_version_id"])
    assert unresolved["relation_kind"] == "unresolved" and unresolved["predecessor_id"] is None
    assert all(o["status"] == "current" for o in api("rao").get(f"{W(workspace)}/observations?patient_id={meera}") if o["id"] in original.values())
    assert any(u["kind"] == "report_relation" for u in api("rao").get(f"{W(workspace)}/patients/{meera}/profile")["unresolved"])


def test_local_transcription_correction_keeps_report_and_history(api, workspace):
    meera = register(api, workspace, "meera")
    doc_id = upload(api, workspace, meera, "meera-flow")["target"]["id"]
    associate(api, workspace, doc_id, meera)
    cand = next(c for c in api("mira").get(f"{W(workspace)}/sources/{doc_id}")["candidates"] if c["assertion"]["analyte"] == "Myeloid markers")
    assert cand["assertion"]["result_state"] == "untested"  # the layout rule misreads the line
    api("mira").fail(f"{W(workspace)}/candidates/{cand['id']}/review", {"expected_revision": 1, "disposition": "verified"}, code="source_inspection_required")
    api("mira").fail(f"{W(workspace)}/candidates/{cand['id']}/review", {"expected_revision": 1, "disposition": "corrected", "source_inspected": True,
                                                                        "corrected": {"result_state": "reported_value"}}, code="reason_required")
    verify_all(api, workspace, doc_id, corrections={"Myeloid markers": {"result_state": "reported_value"}})
    bundle = api("rao").get(f"{W(workspace)}/sources/{doc_id}")
    obs = next(o for o in bundle["observations"] if o["analyte"] == "Myeloid markers")
    assert obs["result_state"] == "reported_value" and obs["exact_wording"] == "Myeloid markers: CD13 and CD33 expressed; MPO not tested"
    assert obs["normalization"]["rule"] == "local-transcription-correction" and "laboratory report is unchanged" in obs["normalization"]["note"]
    assert bundle["reports"][0]["relation_kind"] == "original" and bundle["reports"][0]["version_no"] == 1
    review = next(r for r in bundle["reviews"] if r["candidate_id"] == cand["id"])
    assert review["disposition"] == "corrected" and review["recorded_by_name"] == "Mira"


def test_expected_input_exists_before_result_and_only_linked_report_fulfils(api, workspace):
    meera, arun = register(api, workspace, "meera"), register(api, workspace, "arun")
    item = api("mira").post(f"{W(workspace)}/expected-inputs", {"patient_id": meera, "artifact": "Final molecular report", "report_type": "molecular",
                                                                "owner_username": "mira", "next_action": "Check with the genetics laboratory on Day 8"})["target"]
    listed = api("rao").get(f"{W(workspace)}/patients/{meera}/expected-inputs")[0]
    assert listed["state"] == "pending" and listed["owner_name"] == "Mira" and listed["upstream_request"] is None  # no order is implied
    # A report arriving does not fulfil it by itself; neither does another patient's or another type's report.
    doc_id, _ = intake(api, workspace, meera, "meera-molecular-preliminary")
    assert api("rao").get(f"{W(workspace)}/patients/{meera}/expected-inputs")[0]["state"] == "pending"
    cyto_doc, _ = intake(api, workspace, meera, "meera-cyto")
    cyto = api("rao").get(f"{W(workspace)}/sources/{cyto_doc}")["reports"][0]
    api("mira").fail(f"{W(workspace)}/expected-inputs/{item['id']}/link-report", {"expected_revision": 1, "report_version_id": cyto["id"]}, code="invalid_association")
    arun_doc, _ = intake(api, workspace, arun, "arun-cyto")
    other = api("rao").get(f"{W(workspace)}/sources/{arun_doc}")["reports"][0]
    api("mira").fail(f"{W(workspace)}/expected-inputs/{item['id']}/link-report", {"expected_revision": 1, "report_version_id": other["id"]}, code="invalid_association")
    molecular = api("rao").get(f"{W(workspace)}/sources/{doc_id}")["reports"][0]
    api("mira").post(f"{W(workspace)}/expected-inputs/{item['id']}/link-report", {"expected_revision": 1, "report_version_id": molecular["id"]})
    done = api("rao").get(f"{W(workspace)}/patients/{meera}/expected-inputs")[0]
    assert done["state"] == "received" and done["fulfilled_report_id"] == molecular["id"] and [h["state"] for h in done["history"]] == ["pending", "received"]


def test_unauthorized_download_and_active_content_upload_fail(api, workspace):
    meera = register(api, workspace, "meera")
    doc_id = upload(api, workspace, meera, "meera-referral")["target"]["id"]
    path = f"/api/v1{W(workspace)}/sources/{doc_id}/content"
    assert api(None).http.get(path).status_code == 401
    assert api("operator").http.get(path).json()["error"]["code"] == "actor_not_permitted"  # no clinical read scope
    html = b"<html><script>alert(1)</script></html>"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for media, data in (("text/html", html), ("image/svg+xml", svg), ("application/pdf", html), ("image/png", svg)):
        api("mira").fail(f"{W(workspace)}/sources", {"patient_id": meera, "filename": "x", "media_type": media, "content_base64": b64(data),
                                                     "doc_kind": "other"}, code="unsupported_media", status=415)
    api("isha").fail(f"{W(workspace)}/sources", {"patient_id": meera, "filename": "x.pdf", "media_type": "application/pdf",
                                                 "content_base64": b64(raw("meera-cyto")), "doc_kind": "cytogenetics"}, code="actor_not_permitted")
    assert len(api("mira").get(f"{W(workspace)}/sources?patient_id={meera}")) == 1


def test_image_only_original_uses_manual_source_linked_entry(api, workspace):
    arun = register(api, workspace, "arun")
    result = upload(api, workspace, arun, "arun-echo-scan")
    doc_id = result["target"]["id"]
    assert result["data"]["candidate_count"] == 0
    doc = api("mira").get(f"{W(workspace)}/sources/{doc_id}")["document"]
    assert doc["extraction_limits"]["text_layer"] is False and "manual" in doc["extraction_limits"]["note"].lower()
    manual = {"page": 1, "region": [0.04, 0.4, 0.5, 0.48], "analyte": "LVEF", "dimension": "fitness", "exact_wording": "LVEF: 55 %",
              "value_text": "55 %", "value_number": "55", "units": "%", "result_state": "reported_value"}
    api("mira").fail(f"{W(workspace)}/sources/{doc_id}/candidates", manual, code="identity_review_required")
    associate(api, workspace, doc_id, arun)
    cand = api("mira").post(f"{W(workspace)}/sources/{doc_id}/candidates", manual)["target"]
    verify_all(api, workspace, doc_id)
    obs = api("rao").get(f"{W(workspace)}/observations?patient_id={arun}")[0]
    assert obs["candidate_id"] == cand["id"] and obs["normalization"]["rule"] == "manual-transcription" and obs["source_ref"]["region"] == manual["region"]
