# Oncologist demonstration and UX review

Prepared 11 October 2026. Based on the user's screenshot and feedback, direct inspection of Geevi, its implementation plan, and the linked primary sources. No oncologist interviews or usability sessions have been conducted; the flow below is a design hypothesis to test with the clinician.

Geevi can demonstrate a department's evidence-to-care workflow: a coherent chart, attributable findings and interpretation, shared protocols, individual applicability and exceptions, signed decisions, handoffs and follow-up. Clinical effectiveness, diagnostic accuracy, treatment selection and research productivity remain unvalidated. This is not yet a chemotherapy prescribing system, EHR or cohort-analysis product.

## Start with two clinical stories

Use the **Oncologist walkthrough (fictional; simulated reviews)** workspace. The preparation script runs authenticated commands through the HTTP API under development actors. It simulates reviews; these are not qualified clinical appraisals or institutional signatures. It preserves the existing workspace.

- **Meera:** newly referred AML case. Multiple source reports, incomplete molecular information, an attributed clinical assessment, patient preferences, a shared protocol, an operational venue exception, an approved individual preparation plan, an accepted/completed handoff and a recorded preparation visit. Scheduling the treatment-planning step remains subject to the documented molecular requirement or a reviewed clinical exception.
- **Arun:** documented treatment and response review. Diagnostic marrow reports 34% blasts; a separate later specimen reports 8%. A fictional treatment summary records azacitidine plus venetoclax, febrile neutropenia and a treatment interruption. MRD was not tested. No remission category or next-cycle prescription is inferred. The clinician reviews missing information, records a follow-up decision and assigns the next obligation. A patient question remains open until the clinician actually responds.

All patient documents, dates, outcomes and development-actor actions are fictional. Published-study outcomes are real cited summaries and are never joined into a patient chart as that patient's results. Relative demonstration days are not recommended clinical timing.

## Natural journey to demonstrate

| Clinician question | Screen and action | Information and decision boundary |
|---|---|---|
| Who is this patient, and what decision is due? | Patients → Clinical overview | Name/identifier, episode, attributed assessment and uncertainty, goals, current individual plan, pending investigations and next follow-up |
| How extensive is the disease? | Disease and recorded burden → source report | Marrow/specimen measurements, molecular context and unknown assessments. AML burden is not a solid-tumor stage; classifications are clinician judgments |
| What treatment was received, and what happened? | Treatment received and recorded outcomes | Treatment course, period, response measurements, reported complications and modifications, with dates and original-source links. A proposed plan is not proof of administration |
| Which research question does this case raise? | Case-linked Research | Disease setting, prior treatment, clinical fitness, comparator, outcome, harms, response/MRD and applicability. The patient link stays inside the workspace |
| How deeply was the evidence examined? | Published evidence pack → original source → appraisal | Citation/date, study design/population, comparison, denominators, endpoints, benefit and harm, limitations, access status and critical-appraisal gaps |
| Can the department use this in its pathway? | Appraisal → independent review → protocol/SOP | Evidence acceptance, publication and individual plan approval are separate decisions. The review is attributable and versions are preserved |
| Does the shared pathway fit this patient? | Plan & decisions | Criterion-level judgments, patient discussion, exceptions with rationale and review triggers, frozen assessment/source findings and individual rationale before signing |
| Was the work done, and what follows? | Care & follow-up | Named owners, handoff acceptance, actual care versus appointments, actual encounter date, unresolved patient concerns and the next duty |
| What did we know at the previous decision? | Record history | Earlier captured versions and their recorded time. Later-arriving reports do not rewrite the earlier view |

Report association and candidate verification belong under **Reports** and the coordinator's **Today** worklist. The clinical overview no longer leads with an unresolved-task count or knowledge-cutoff selector. Report-review work has not disappeared; it has moved to its appropriate context.

## Research documentation and depth

The fabricated research notes were replaced by **original, attributed Geevi evidence briefs**, not copies of copyrighted journal papers. They include citations, questions, populations, comparisons, endpoints, findings, limitations, applicability and access/reuse notes. Full-paper and current-literature appraisal must still be done by the oncologist.

| Reference | Useful for | Depth in this starter pack |
|---|---|---|
| [ELN 2022 recommendations](https://pubmed.ncbi.nlm.nih.gov/35797463/) | AML diagnosis/classification, genetic risk and response framework | Citation and abstract verified. Publisher full text was blocked; detailed tables and workup rules were not appraised. This is not asserted to be the latest guideline |
| [VIALE-A original 2020 analysis](https://pubmed.ncbi.nlm.nih.gov/32786187/) and [trial record](https://clinicaltrials.gov/study/NCT02993523) | Treatment-outcome and harm appraisal for the studied population | Original 431-person analysis kept distinct from the current registry's 443 enrollment. Abstract and trial-record context verified; full methods/supplements not critically appraised. Registry was active, not recruiting when checked |
| [Beat AML 2018](https://www.nature.com/articles/s41586-018-0623-z) | Research dataset structure, patient–specimen–assay relationships and genomic provenance | Abstract/data availability and repository metadata verified. Ex vivo assay associations do not establish an individual's clinical benefit. No participant-level records were imported |

Related research areas in the patient journey: classification/genomics; fitness and treatment applicability; response and MRD; comparative benefits and harms; assay and specimen methods. The library provides bounded keyword filtering and links to PubMed/ClinicalTrials.gov. It does not conduct a systematic review, match trials automatically, or infer eligibility.

## Dataset structure to take forward

A [proposed research schema](../research_oncologist_demo/proposed-research-schema.json) is saved alongside the source catalog. It contains field definitions, not real participant records or a reproduction of the dataset dictionary.

Start with public metadata and dictionaries from [Beat AML's original dbGaP release](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001657.v1.p1) and [Vizome](https://www.vizome.org/additional_figures_BeatAML.html). The original accession is superseded; record the exact release and terms before any ingestion. Individual-level dbGaP data require authorized access. Public accessibility does not establish unrestricted redistribution rights.

Model a separate research area with: dataset/accession/release and permission; participant or subject key; specimen key and collection time; assay, method and quality; molecular result; ex vivo measurement; clinical annotation; analysis population, endpoint, denominator and provenance. Distinguish multiple specimens per participant and missing assays. Do not register research participants as care patients or turn laboratory sensitivity measurements into treatment recommendations.

Use [mCODE STU4](https://hl7.org/fhir/us/mcode/) as a representation reference for patient, disease, health assessment, genomics, treatments and outcomes. These are design prompts, not a required clinical checklist or an interoperability-conformance claim. Current Geevi preserves specimens, source versions, missing-result states and clinician interpretation. Structured demographics, staging/risk/response framework identifiers, medication administration, toxicity grading and longitudinal patient-reported outcomes need a clinician-led data-model extension before routine clinical use.

## Implementation delivered

Patient search; case-linked research; reader-accessible evidence documents/passages and originals; reference import with correct provenance; deeper appraisal display; linked protocol evidence; patient context and rationale in the signing review; exception revision/withdrawal; concern review without forced closure; follow-up creation/transfer/cancellation and explicit actual encounter date; treatment/response report types and a longitudinal fictional example. Cancelling an authored follow-up duty triggers review of the affected plan while preserving its signature.

The shared protocol in the walkthrough is a **fictional case-review and follow-up workflow**. It does not define a therapeutic regimen, drug order or automatically derive rules from an abstract. Senior departmental authors can steward the evidence and protocol, while treating clinicians remain responsible for individual decisions. The demo's Rao development actor holds both authoring and treating grants; institutional staffing and grants remain to be validated.

## Moderated clinician validation plan

Invite 5–8 oncologists across the research-lead and treating roles, plus coordinators for report/handoff tasks. This is a proposed study; no results or success rates are claimed. Use fictional data. Let participants think aloud without teaching the interface first.

1. In Arun's chart, explain the disease burden, treatment received, reported response and harms. Identify what remains unknown and open a source supporting one statement.
2. Identify the next clinical decision and who owns the follow-up. Explain how a scheduled appointment differs from an actual encounter.
3. Find evidence relevant to the uncertainty. State the trial population, comparison, benefits/harms and what was not appraised. Explain why the trial result is not Arun's individual outcome.
4. Propose an appraisal and departmental change. Have a second participant object/approve, then explain what publication does and what still requires a patient decision.
5. Assess protocol applicability and an exception. Read the patient context and rationale before signing; explain how a new report triggers review.
6. Respond to the open patient concern and record an actual follow-up decision with a new obligation. Verify that mere acknowledgement does not close the duty.

Record completion without assistance, navigation detours, source-retrieval time, clinical misinterpretations, missed ownership and uncertainty, and confusion between evidence/plan/administration. Treat confusion about a patient's actual treatment/outcome, unsupported clinical inference, missing follow-up ownership or approval meaning as a release-blocking design finding for a clinical pilot. Ask the clinician which chart fields, disease-specific classifications, treatment/response terminology and research-search sources they need. Adapt the model and flow to those findings before claiming effectiveness.

## Reproduce the walkthrough

Run `uv run --project apps/api python scripts/prepare-oncologist-demo.py --origin <demo-origin> --credentials <ignored-credentials-file> --journal .geevi-local/oncologist-journal.json`. Use a distinct journal per server; a journal retains exact command IDs/results and resumes the same workspace. Credentials and journals are excluded from Git. The script is local demonstration tooling; do not run it with clinical accounts or real patient data.
