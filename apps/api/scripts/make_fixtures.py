"""Author the fictional department-journey source pack (U4).

Patient documents are invented for workflow demonstration: no real patient, study subject or laboratory.
Research briefs are original, attributed summaries of published sources, with access and appraisal limits.
Neither pack is a clinical recommendation. Patient values are placeholders, not clinical guidance.
The gold annotations are written from the authoring specification below (the intended assertions),
independently of the runtime extractor, and are read only by tests.

Run:  uv run --project apps/api python apps/api/scripts/make_fixtures.py
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "fixtures" / "department-journey"
# Runtime copy packaged with the API for hosts that deploy apps/api on its own. Inputs only, never gold.
PACKAGED = Path(__file__).resolve().parents[1] / "app" / "demo_data"
BANNER = "FICTIONAL DEMONSTRATION DOCUMENT - NOT A REAL PATIENT RECORD - NOT CLINICALLY VALIDATED"
MRN = "geevi-demo-mrn"
PATIENTS = {
    "meera": {"display_name": "Meera (fictional)", "identifiers": [{"system": MRN, "value": "GEEVI-DEMO-0001"}],
              "summary": "Fictional adult referred with a new AML presentation.", "episode_title": "New AML presentation (fictional)"},
    "arun": {"display_name": "Arun (fictional)", "identifiers": [{"system": MRN, "value": "GEEVI-DEMO-0002"}],
             "summary": "Fictional AML case with a documented first treatment cycle and subsequent response assessment.", "episode_title": "AML treatment and response review (fictional)"},
}
NORTH_LAB, NORTH_PATH, EAST = "Fictional Northside Laboratory", "Fictional Northside Pathology", "Fictional Eastbank Genetics"


def a(analyte, value, state="reported_value", part=None, line=None, units=None, ref=None):
    """One authored assertion: the wording printed on the report and its intended reading (gold)."""
    return {"analyte": analyte, "value_text": value, "result_state": state, "specimen_label": part, "units": units,
            "reference_range": ref, "line": line or f"{analyte}: {value}"}


def row(analyte, value, units, ref):
    return {"analyte": analyte, "value_text": value, "result_state": "reported_value", "specimen_label": None, "units": units,
            "reference_range": ref, "row": [analyte, value, units, ref]}


def doc(id_, patient, kind, title, issuer, accession, stage, *, header=(), parts=(), sections=(), received_day=0, relation=None,
        affects=None, expected=None, media="application/pdf", note=None):
    return {"id": id_, "patient": patient, "doc_kind": kind, "title": title, "issuer": issuer, "accession": accession, "stage": stage,
            "header": list(header), "parts": list(parts), "sections": list(sections), "received_day": received_day,
            "relation": relation, "affects": affects, "expected": expected or {}, "media_type": media, "note": note}


SPECS = [
    doc("meera-referral", "meera", "referral", "Referral letter", "Fictional Lakeside Clinic", "REF-0101", "baseline",
        header=[("Reported by", "Dr. Fictional Referrer"), ("Issued", "Day 0")],
        sections=[("REFERRAL DETAILS", [
            a("Reason for referral", "Abnormal blood count with circulating blasts reported by the referring clinic"),
            a("Presenting symptoms", "Fatigue and easy bruising for about three weeks"),
            a("Prior treatment", "None reported"),
            a("Performance status", "Not recorded in this referral", "unreported"),
            a("Home support", "Lives with spouse; sister available to accompany visits")])]),
    doc("meera-blood-day-minus-1", "meera", "blood_panel", "Blood count panel", NORTH_LAB, "HEM-2201", "baseline", received_day=0,
        header=[("Collected", "Day -1"), ("Issued", "Day -1"), ("Method", "Automated analyser (fictional)")],
        sections=[("RESULTS", [row("Hemoglobin", "8.4", "g/dL", "12.0-15.5"), row("White cell count", "38.2", "x10^9/L", "4.0-11.0"),
                               row("Platelets", "41", "x10^9/L", "150-400"), row("Peripheral blasts", "55", "%", "0-1")])]),
    doc("meera-marrow", "meera", "marrow", "Bone marrow morphology report", NORTH_PATH, "MAR-3301", "baseline", received_day=2,
        header=[("Reported by", "Dr. Fictional Pathologist"), ("Issued", "Day 2"), ("Report status", "Final")],
        parts=[("A", "Bone marrow aspirate, left posterior iliac crest. Collected Day 1"),
               ("B", "Bone marrow trephine biopsy, left posterior iliac crest. Collected Day 1")],
        sections=[("Part A findings", [a("Blast percentage", "62 % of nucleated cells (500-cell differential)", part="Part A"),
                                       a("Morphology", "Blasts with fine chromatin; granules seen in occasional cells", part="Part A")]),
                  ("Part B findings", [a("Cellularity", "90 %", part="Part B")]),
                  ("Summary", [a("Reported diagnosis", "Acute myeloid leukaemia; cytogenetic and molecular classification to follow", "pending", part="Part B")])]),
    doc("meera-flow", "meera", "flow", "Flow cytometry report", NORTH_PATH, "FLO-3302", "baseline", received_day=2,
        header=[("Issued", "Day 2"), ("Panel", "Acute leukaemia screening panel (fictional)"), ("Limitations", "Limited panel; MPO not tested")],
        parts=[("A", "Bone marrow aspirate. Collected Day 1")],
        sections=[("FINDINGS", [a("Blast immunophenotype", "CD34 positive, CD117 positive, HLA-DR positive", "detected", part="Part A"),
                                a("Myeloid markers", "CD13 and CD33 expressed; MPO not tested", "reported_value", part="Part A"),
                                a("Lymphoid markers", "Not detected on the blast population", "not_detected", part="Part A")])],
        note="The layout rule reads 'MPO not tested' as untested for the whole line; the reviewer must correct it. Gold records the intended reading."),
    doc("meera-cyto", "meera", "cytogenetics", "Cytogenetics report", NORTH_PATH, "CYT-3303", "baseline", received_day=5,
        header=[("Issued", "Day 5"), ("Method", "G-banded karyotype (fictional)")],
        parts=[("A", "Bone marrow aspirate. Collected Day 1")],
        sections=[("RESULTS", [a("Karyotype", "46,XX[20]", part="Part A"), a("Metaphases analysed", "20", part="Part A"),
                               a("FISH panel", "Not performed - insufficient sample", "insufficient_sample", part="Part A")])]),
    doc("meera-molecular-preliminary", "meera", "molecular", "Molecular panel - preliminary report", EAST, "MOL-7781", "late", received_day=7,
        header=[("Issued", "Day 4"), ("Report status", "Preliminary"), ("Panel", "Myeloid gene panel (fictional)"),
                ("Limitations", "Preliminary; final report to follow")],
        parts=[("A", "Bone marrow aspirate. Collected Day 1")],
        sections=[("RESULTS", [a("NPM1", "Pending - analysis in progress", "pending", part="Part A"),
                               a("FLT3-ITD", "Not detected", "not_detected", part="Part A"),
                               a("TP53", "Not tested on this panel", "untested", part="Part A"),
                               a("IDH1", "Indeterminate - low coverage", "indeterminate", part="Part A")])],
        note="Arrives after the first profile snapshot although it describes Day 1 material (late-arriving report)."),
    doc("meera-marrow-addendum", "meera", "marrow", "Bone marrow report - addendum", NORTH_PATH, "MAR-3301", "addendum", received_day=6,
        header=[("Issued", "Day 6"), ("Report status", "Amended")], relation="Addendum (additive) to accession MAR-3301",
        sections=[("Part B findings", [a("Morphology", "No increase in reticulin fibrosis on the trephine section", part="Part B")])],
        expected={"relation_kind": "additive_addendum", "supersedes": []}),
    doc("meera-marrow-correction", "meera", "marrow", "Bone marrow report - corrected", NORTH_PATH, "MAR-3301", "correction", received_day=9,
        header=[("Issued", "Day 9"), ("Report status", "Corrected")], relation="Correction of accession MAR-3301",
        affects="Part B Cellularity",
        sections=[("Part B findings", [a("Cellularity", "80 %", part="Part B")])],
        expected={"relation_kind": "correction", "supersedes": [{"analyte": "Cellularity", "specimen_label": "Part B", "previous_value": "90 %"}]}),
    doc("meera-blood-day-6", "meera", "blood_panel", "Blood count panel", NORTH_LAB, "HEM-2290", "followup", received_day=6,
        header=[("Collected", "Day 6"), ("Issued", "Day 6"), ("Method", "Automated analyser (fictional)")],
        sections=[("RESULTS", [row("Hemoglobin", "7.9", "g/dL", "12.0-15.5"), row("White cell count", "21.4", "x10^9/L", "4.0-11.0"),
                               row("Platelets", "33", "x10^9/L", "150-400")])]),
    doc("arun-referral", "arun", "referral", "Referral letter", "Fictional Lakeside Clinic", "REF-0102", "baseline",
        header=[("Reported by", "Dr. Fictional Referrer"), ("Issued", "Day 0")],
        sections=[("REFERRAL DETAILS", [
            a("Reason for referral", "Low blood counts with blasts reported on a routine check"),
            a("Prior treatment", "None reported"),
            a("Comorbidities", "Long-standing hypertension as stated by the referrer"),
            a("Home support", "Lives alone; daughter can attend by arrangement")])]),
    doc("arun-blood-day-2", "arun", "blood_panel", "Blood count panel", NORTH_LAB, "HEM-2207", "baseline", received_day=2,
        header=[("Collected", "Day 2"), ("Issued", "Day 2")],
        sections=[("RESULTS", [row("Hemoglobin", "9.1", "g/dL", "13.0-17.0"), row("Platelets", "58", "x10^9/L", "150-400")])],
        expected={"wrong_patient_if_uploaded_to": "meera"}),
    doc("arun-marrow", "arun", "marrow", "Bone marrow morphology report", NORTH_PATH, "MAR-3310", "baseline", received_day=3,
        header=[("Issued", "Day 3"), ("Report status", "Final")],
        parts=[("A", "Bone marrow aspirate. Collected Day 2")],
        sections=[("Part A findings", [a("Blast percentage", "34 % of nucleated cells", part="Part A"),
                                       a("Reported diagnosis", "Acute myeloid leukaemia", part="Part A")])]),
    doc("arun-cyto", "arun", "cytogenetics", "Cytogenetics report", EAST, "CYT-3303", "baseline", received_day=6,
        header=[("Issued", "Day 6")], parts=[("A", "Bone marrow aspirate. Collected Day 2")],
        sections=[("RESULTS", [a("Karyotype", "46,XY[20]", part="Part A")])],
        note="Deliberately the same accession number as Meera's cytogenetics from a different issuer: identities must stay distinct."),
    doc("arun-echo-scan", "arun", "organ_assessment", "External echocardiogram (scanned image)", "Fictional Riverside Cardiology", "ECH-5510",
        "baseline", received_day=4, media="image/png",
        sections=[("SCANNED REPORT", [a("LVEF", "55 % (as printed on the scanned page)", line="LVEF: 55 %")])],
        expected={"candidates": 0, "manual_entry_required": True},
        note="Image-only original: no machine findings are extracted; a reviewer transcribes with a marked region."),
    doc("arun-treatment-summary", "arun", "treatment_summary", "Treatment course and discharge summary", "Fictional Northside Oncology", "ONC-4410", "treatment", received_day=35,
        header=[("Author", "Dr. Fictional Treating Oncologist"), ("Clinical date", "Day 35"), ("Issued", "Day 35"), ("Report status", "Final")],
        sections=[("TREATMENT COURSE", [
            a("Treatment received", "Azacitidine plus venetoclax; first cycle documented in this fictional discharge summary"),
            a("Treatment period", "Day 8 to Day 35; dose and administration records are not supplied"),
            a("Treatment intent", "Disease-directed treatment, as stated by the treating team"),
            a("Treatment complications", "Febrile neutropenia on Day 20; admitted and treated; fever resolved before discharge"),
            a("Treatment modification", "Venetoclax interrupted during the admission, according to the discharge note; restart decision not supplied")]),
                  ("DISCHARGE STATUS", [a("Current symptoms", "Fatigue; no fever at discharge, as recorded on Day 35")])],
        note="Fictional recorded treatment history, not a prescription. Complications are reported events, not adjudicated causality."),
    doc("arun-response-assessment", "arun", "response_assessment", "Post-cycle marrow and response review", NORTH_PATH, "MAR-3380", "response", received_day=38,
        header=[("Author", "Dr. Fictional Pathologist"), ("Issued", "Day 38"), ("Report status", "Final")],
        parts=[("A", "Bone marrow aspirate. Collected Day 36")],
        sections=[("POST-CYCLE FINDINGS", [
            a("Blast percentage", "8 % of nucleated cells (500-cell differential)", part="Part A"),
            a("Measurable residual disease", "Not available; assay not performed on this sample", "untested", part="Part A"),
            a("Extramedullary assessment", "Not reported in this marrow report", "unreported", part="Part A")]),
                  ("RESPONSE REVIEW", [
            a("Reported response", "Residual marrow blasts reported; formal remission category not assigned in this source", part="Part A"),
            a("Response assessment date", "Day 36; after the documented first cycle", part="Part A")])],
        note="Do not infer complete remission, molecular response or an AML stage. Formal response and next treatment remain clinician decisions."),
]

# Original, attributed summaries of verified publications; no fabricated research studies.
REFERENCE_CATALOG = json.loads((Path(__file__).resolve().parents[1] / "app" / "reference_catalog.json").read_text())
RESEARCH = [
    {"id": r["id"], "file": f"research-{r['id']}.pdf", "label": "public_reference", "citation": r["citation"],
     "title": r["title"], "reference": r,
     "lines": [f"Source type: {r['source_type']}", f"Publication date: {r['publication_date']}",
               f"Citation: {r['citation']}", f"Question: {r['question']}", f"Population: {r['population']}",
               f"Intervention: {r['intervention']}", f"Comparator: {r['comparator']}", f"Outcomes: {r['outcomes']}",
               f"Finding 1: {r['findings']}", f"Limitations: {r['limitations']}", f"Applicability: {r['applicability']}",
               f"Reuse and access: {r['license_note']}",
               "Original Geevi evidence brief, not the original article or a treatment recommendation.",
               f"Sources verified: {REFERENCE_CATALOG['verified_on']}. Full-text appraisal and a current literature review remain necessary."]}
    for r in REFERENCE_CATALOG["sources"]
]

NOTE = "Fictional workflow requirement for software demonstration. Contains no clinical eligibility, dosing or therapy content; unvalidated."
REQUIREMENTS_V1 = [
    {"id": "REQ-IDENTITY", "kind": "identity", "text": "Patient identity and source-document association are reviewed for every baseline document.",
     "gate": "plan_approval", "waiver": {"allowed": False}, "watch": ["reports/*"], "note": NOTE},
    {"id": "REQ-CONTEXT", "kind": "context", "text": "Baseline source reports (referral, blood panel, marrow, flow, cytogenetics) are received and source-verified.",
     "gate": "plan_approval", "waiver": {"allowed": False}, "watch": ["reports/*", "assessment"], "note": NOTE},
    {"id": "REQ-DISCUSSION", "kind": "discussion", "text": "Patient goals and preferences are discussed and documented by an authorised team member.",
     "gate": "plan_approval", "waiver": {"allowed": False}, "watch": ["discussion"], "note": NOTE},
    {"id": "REQ-VENUE", "kind": "operational", "text": "The preparation visit takes place at the main-campus day unit.",
     "branch": {"default": "Main-campus day unit", "alternate": "Satellite clinic appointment (requires an approved operational exception)"},
     "gate": "plan_approval", "waiver": {"allowed": True, "exception_type": "operational"}, "watch": ["discussion"], "note": NOTE},
    {"id": "REQ-MOLECULAR", "kind": "clinical_input", "text": "The final molecular report is received and source-verified before the treatment-planning visit is scheduled.",
     "gate": "step:STEP-PLANNING-VISIT", "waiver": {"allowed": True, "exception_type": "clinical"}, "watch": ["reports/molecular"], "note": NOTE},
]
REQUIREMENTS_V2 = REQUIREMENTS_V1 + [
    {"id": "REQ-TRIAL-CONTEXT", "kind": "context", "text": "Patient-specific fitness, comorbidity, prior treatment and support context are documented before interpreting trial applicability.",
     "gate": "plan_approval", "waiver": {"allowed": False}, "watch": ["discussion"], "note": NOTE},
]
SCENARIO = {
    "label": "fictional", "validation_status": "Clinical content unvalidated; workflow demonstration only.",
    "time_anchor": "Day 0 = referral received. Relative days illustrate workflow only, not recommended clinical timing.",
    "patients": PATIENTS,
    "research": {
    "question_v1": {
        "title": "ELN 2022 AML recommendations — evidence brief",
        "question": "Which diagnostic, genetic-risk and response-assessment information should be reviewed before an AML case is discussed under a departmental pathway?",
        "scope": "AML departmental evidence review and individual applicability.",
        "intended_use": "Inform a reviewed case-readiness pathway; no automatic treatment recommendation."
    },
    "appraisal_v1": {
        "population": "Adults with AML; this is an expert recommendations document, not a randomized patient cohort.",
        "intervention": "Not applicable: recommendations and classification framework.",
        "comparator": "Not applicable: no experimental treatment comparison.",
        "outcome": "Updated disease and genetic-risk classification Genomic diagnostics and measurable residual disease assessment Revised response criteria and management recommendations",
        "timepoint": "As reported in the dated publication; check the source version.",
        "study_design": "Expert-panel recommendations",
        "findings": "The 2022 panel update addresses advances in molecular classification, genomic diagnostics, measurable residual disease and AML therapies. Its abstract identifies revisions to genetic-risk classification and response criteria; it is a reference for documenting the framework used in a case assessment, not an automatic classifier.",
        "uncertainty": "Bounded abstract/source-record appraisal. Full methods and current evidence have not been comprehensively reviewed.",
        "limitations": "The PubMed citation and abstract were verified. The publisher full-text page returned a security-verification 403, so detailed tables and workup rules were not independently reviewed in this research pass. Published in 2022. This brief does not establish that the source is the latest guideline or that one risk framework applies to every treatment context. A recommendations document does not supply an individual patient's diagnosis, fitness assessment or treatment decision."
    },
    "question_v2": {
        "title": "VIALE-A — randomized-trial appraisal brief",
        "question": "In previously untreated AML unsuitable for standard induction, what benefits, harms and applicability limits were reported for azacitidine plus venetoclax compared with azacitidine plus placebo?",
        "scope": "AML departmental evidence review and individual applicability.",
        "intended_use": "Inform a reviewed case-readiness pathway; no automatic treatment recommendation."
    },
    "appraisal_v2": {
        "population": "Original 2020 intention-to-treat analysis: 431 patients, 286 combination and 145 control; median age 76. Patients were previously untreated and considered ineligible for standard induction because of age 75 or older, coexisting conditions, or both.",
        "intervention": "Azacitidine plus venetoclax, described for evidence appraisal only; no dosing instructions are included.",
        "comparator": "Azacitidine plus placebo.",
        "outcome": "Primary endpoint in the original publication: overall survival Complete remission and composite complete remission Adverse events and serious adverse events",
        "timepoint": "As reported in the dated publication; check the source version.",
        "study_design": "Phase 3 randomized controlled trial",
        "findings": "At median follow-up 20.5 months, median overall survival was 14.7 versus 9.6 months; hazard ratio for death 0.66, 95% confidence interval 0.52–0.85. Composite complete remission was 66.4% versus 28.3%. Grade 3 or higher febrile neutropenia occurred in 42% versus 19%; serious adverse events in 83% versus 73%. Benefits and harms should be appraised together.",
        "uncertainty": "Bounded abstract/source-record appraisal. Full methods and current evidence have not been comprehensively reviewed.",
        "limitations": "The original publication's abstract and trial identifier were verified; the full paper and supplements were not appraised in this pass. The study population was unsuitable for standard induction. Results cannot be generalized automatically to all newly diagnosed AML, an individual molecular subgroup, or a patient without a documented fitness assessment. Funded by AbbVie and Genentech. The brief is a starter appraisal, not a systematic review or current treatment recommendation. The current registry lists 443 actual enrollment, a later 2021 data cutoff and last update posted2026-06-11. These are distinct from the original 2020 paper's 431-person analysis; denominators and versions must not be merged."
    },
    "question_insufficient": {
        "title": "Can an ex vivo assay establish an individual clinical benefit?",
        "question": "Does research assay evidence establish clinical benefit for this individual, and what evidence is still missing?",
        "scope": "Research measurement versus clinical decision.",
        "intended_use": "Document insufficient evidence; do not infer treatment selection from a research assay."
    }
},
    "protocol": {"title": "AML case review and follow-up pathway (fictional workflow protocol)",
                 "scope": "Case preparation for AML referrals and follow-up planning reviews in the fictional service. Review disease findings, any treatment received, response, harms and patient goals before the next planning visit. This operational pathway does not define drug treatment or clinical eligibility.",
                 "v1": {"requirements": REQUIREMENTS_V1, "summary": "Initial pathway."},
                 "v2": {"requirements": REQUIREMENTS_V2, "summary": "Adds individual-context review before interpreting trial evidence; no regimen or eligibility is inferred."}},
    "sop": {"title": "Case preparation and handoff SOP (fictional)", "purpose": "Role-owned operational steps for preparing a new case and handing work to the care team. Steps create task specifications, not clinical orders.",
            "escalation": "Fictional AML coordinator desk",
            "steps": [
                {"id": "STEP-CONFIRM-VENUE", "title": "Confirm appointment venue and time with the patient", "role": "Care team", "expected_evidence": "Confirmation note naming who was contacted"},
                {"id": "STEP-PREP-VISIT", "title": "Carry out the preparation visit checklist", "role": "Care team", "expected_evidence": "Attributed care record for the visit", "depends_on": ["STEP-CONFIRM-VENUE"]},
                {"id": "STEP-PLANNING-VISIT", "title": "Schedule the treatment-planning visit", "role": "Care team", "expected_evidence": "Scheduled planning visit", "requires": ["REQ-MOLECULAR"]},
                {"id": "STEP-FOLLOWUP", "title": "Arrange the routine follow-up review", "role": "Coordinator", "expected_evidence": "Scheduled follow-up obligation"}]},
    "exceptions": {
        "venue": {"type": "operational", "requirement_id": "REQ-VENUE", "departure": "Hold the preparation visit at the satellite clinic nearer the patient's home.",
                  "rationale": "Patient preference documented in the discussion: long travel to the main campus; no change to any medical treatment rule."},
        "molecular": {"type": "clinical", "requirement_id": "REQ-MOLECULAR", "departure": "Schedule the treatment-planning visit before the final molecular report is available.",
                      "rationale": "Requested for review; requires both the treating clinician and the independent reviewer under the fictional policy."}},
    "public_references_note": "Public standards and datasets are listed separately in references/public-references.json and are never joined to a fictional chart.",
}
PUBLIC_REFERENCES = [
    {"title": "HL7 mCODE implementation guide", "url": "https://hl7.org/fhir/us/mcode/", "use": "Representation boundary only; no conformance claim."},
    {"title": "HL7 FHIR R4 DiagnosticReport", "url": "https://hl7.org/fhir/R4/diagnosticreport.html", "use": "Report/observation separation; no conformance claim."},
    {"title": "Beat AML 2.0 public workbook (see research_oncology_datasets/dataset-guide.md)", "url": None,
     "use": "Informs patient/specimen/assay/missingness structure only. No subject is imported or joined to Meera or Arun."},
    {"title": "GDC pathology report sample (lung; see research_oncology_datasets/samples/README.md)", "url": None,
     "use": "Informs report sections and multi-specimen handling only. Not an AML reference; not imported."},
]


def _header_lines(spec: dict) -> list[str]:
    patient = PATIENTS[spec["patient"]]
    lines = [f"Patient: {patient['display_name']}", f"Patient ID: {patient['identifiers'][0]['value']}",
             f"Accession: {spec['accession']}", f"Report type: {spec['title']}"]
    lines += [f"{k}: {v}" for k, v in spec["header"]]
    if spec["relation"]:
        lines.append(f"Relation: {spec['relation']}")
    if spec["affects"]:
        lines.append(f"Affects: {spec['affects']}")
    lines += [f"Part {label}: {text}" for label, text in spec["parts"]]
    return lines


def render_pdf(spec: dict) -> bytes:
    import textwrap

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    c.setTitle(spec["title"])
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 8)
    c.drawString(50, y, BANNER)
    y -= 26
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, y, spec["issuer"])
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(50, y, f"Laboratory: {spec['issuer']}")
    y -= 22
    c.setFont("Helvetica", 10)
    for line in _header_lines(spec):
        c.drawString(50, y, line)
        y -= 15
    for heading, items in spec["sections"]:
        y -= 12
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, heading)
        y -= 18
        c.setFont("Helvetica", 10)
        if items and "row" in items[0]:
            c.setFont("Helvetica-Oblique", 9)
            for x, label in zip((50, 230, 320, 420), ("Test", "Result", "Units", "Reference"), strict=True):
                c.drawString(x, y, label)
            y -= 15
            c.setFont("Helvetica", 10)
        for item in items:
            if "row" in item:
                for x, cell in zip((50, 230, 320, 420), item["row"], strict=True):
                    c.drawString(x, y, cell)
            else:
                lines = textwrap.wrap(item["line"], width=80, break_long_words=False, break_on_hyphens=False)
                for index, line in enumerate(lines):
                    if index:
                        y -= 14
                    c.drawString(62 if index == 0 else 82, y, line)
            y -= 16
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 40, "Invented content for software workflow demonstration only. " + BANNER.split(" - ")[0].title() + ".")
    c.showPage()
    c.save()
    return buf.getvalue()


def render_research_pdf(item: dict) -> bytes:
    """Paginated original brief; never relabel a summary as the publisher's original."""
    import textwrap

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    c.setTitle(item["title"])
    page = 0
    def new_page():
        nonlocal page
        if page:
            c.showPage()
        page += 1
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, A4[1] - 42, "GEEVI EVIDENCE BRIEF - PUBLISHED SOURCE - ATTRIBUTED SUMMARY")
        c.setFont("Helvetica", 8)
        c.drawString(50, 30, f"Not the original publication. Not a treatment recommendation. Page {page}")
        return A4[1] - 70
    y = new_page()
    for paragraph in [item["title"], *item["lines"]]:
        paragraph = paragraph.replace("—", "-").replace("–", "-").replace("’", "'").replace("≥", ">=")
        for line in textwrap.wrap(paragraph, width=92, break_long_words=True):
            if y < 62:
                y = new_page()
            c.setFont("Helvetica", 10)
            c.drawString(50, y, line)
            y -= 14
        y -= 12
    c.showPage()
    c.save()
    return buf.getvalue()


def render_png(spec: dict) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("L", (900, 520), 244)
    draw = ImageDraw.Draw(image)
    # Use Pillow's bundled bitmap font: FreeType's default font rasterizes differently
    # on macOS and Linux, which changes the source hash despite identical authored text.
    font = ImageFont.load_default_imagefont()
    patient = PATIENTS[spec["patient"]]
    lines = [BANNER, "", spec["issuer"], f"Patient: {patient['display_name']}   Patient ID: {patient['identifiers'][0]['value']}",
             f"Accession: {spec['accession']}   Report: {spec['title']}", ""]
    lines += [item["line"] for _, items in spec["sections"] for item in items]
    lines += ["", "(Scanned image: there is no text layer. Transcribe manually against a marked region.)"]
    for index, line in enumerate(lines):
        draw.text((40, 36 + index * 34), line, fill=20, font=font)
    buf = io.BytesIO()
    # Stored deflate blocks also avoid platform-specific compressor output.
    image.save(buf, format="PNG", optimize=False, compress_level=0)
    return buf.getvalue()


def render(spec: dict) -> bytes:
    return render_png(spec) if spec["media_type"] == "image/png" else render_pdf(spec)


def gold_for(spec: dict) -> dict:
    assertions = [{k: item.get(k) for k in ("analyte", "value_text", "result_state", "specimen_label", "units", "reference_range")}
                  for _, items in spec["sections"] for item in items]
    return {"input": spec["id"], "label": "fictional", "purpose": "test-only expected output; never read by the runtime",
            "claimed_patient_identifier": PATIENTS[spec["patient"]]["identifiers"][0]["value"],
            "assertions": assertions, "expected": spec["expected"], "note": spec["note"]}


def build(out: Path = OUT) -> dict:
    (out / "inputs").mkdir(parents=True, exist_ok=True)
    (out / "gold").mkdir(exist_ok=True)
    (out / "references").mkdir(exist_ok=True)
    manifest = {"schema": "geevi-fixture-manifest/1", "label": "fictional", "time_anchor": SCENARIO["time_anchor"],
                "patients": PATIENTS, "inputs": [], "research": []}
    for spec in SPECS:
        data = render(spec)
        ext = "png" if spec["media_type"] == "image/png" else "pdf"
        (out / "inputs" / f"{spec['id']}.{ext}").write_bytes(data)
        (out / "gold" / f"{spec['id']}.json").write_text(json.dumps(gold_for(spec), indent=2) + "\n")
        manifest["inputs"].append({
            "id": spec["id"], "file": f"inputs/{spec['id']}.{ext}", "media_type": spec["media_type"], "sha256": hashlib.sha256(data).hexdigest(),
            "length": len(data), "patient": spec["patient"], "doc_kind": spec["doc_kind"], "title": spec["title"], "issuer": spec["issuer"],
            "accession": spec["accession"], "stage": spec["stage"], "label": "fictional",
            "received_time": {"value": spec["received_day"], "unit": "day", "anchor": "episode-day-0", "precision": "day",
                              "basis": "fictional relative demonstration day"}})
    for item in RESEARCH:
        data = render_research_pdf(item)
        (out / "inputs" / item["file"]).write_bytes(data)
        manifest["research"].append({"id": item["id"], "file": f"inputs/{item['file']}", "media_type": "application/pdf",
                                     "sha256": hashlib.sha256(data).hexdigest(), "length": len(data), "citation": item["citation"],
                                     "title": item["title"], "label": item["label"], "reference": item["reference"]})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "scenario.json").write_text(json.dumps(SCENARIO, indent=2) + "\n")
    (out / "references" / "public-references.json").write_text(json.dumps({"label": "public_reference", "references": PUBLIC_REFERENCES}, indent=2) + "\n")
    return manifest


def package(source: Path = OUT, target: Path = PACKAGED) -> None:
    import shutil
    shutil.rmtree(target, ignore_errors=True)
    (target / "inputs").mkdir(parents=True)
    for name in ("manifest.json", "scenario.json"):
        shutil.copyfile(source / name, target / name)
    for item in sorted((source / "inputs").iterdir()):
        shutil.copyfile(item, target / "inputs" / item.name)


if __name__ == "__main__":
    result = build()
    package()
    print(f"wrote {len(result['inputs'])} source inputs and {len(result['research'])} research notes to {OUT}")
    print(f"packaged the runtime copy (inputs, manifest, scenario) in {PACKAGED}")
