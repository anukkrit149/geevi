# Oncologist demo: patient profile and planning workspace

Reviewed 11 October 2026. Scope: current Next.js patient views, profile projection, demonstration scenario, and the original journey requirements. This is a product and information-structure review, not a clinical endorsement or treatment recommendation.

## Conclusion

Geevi can demonstrate a useful **case-preparation and departmental knowledge workflow**. Its strongest existing behavior is keeping source-verified observations, clinical interpretation, patient discussion, and signed decisions separate. The current patient page does not yet make the oncologist's planning task sufficiently obvious: it opens with technical history controls and many evidence cards, while assessment and patient goals appear much later. The original fictional research documents describe invented operational audits, which cannot demonstrate authentic oncology research appraisal.

The demo should open on a clear question: **“What do we know about this patient, what remains uncertain, and what decision must the team make next?”** It should then show how the doctor consults real research, reviews its applicability, contributes a department proposal, and records the individual patient's plan.

## Research method and primary sources

Used gstack `/browse` with a separate `BROWSE_STATE_FILE`, direct navigation to official HL7 pages and the PubMed record of the original ELN recommendations. No general search was needed; six direct primary-document visits were enough. Verified the published guide and cited record on the review date. Did not consult secondary summaries or assert the ELN 2022 document is a complete current guideline review.

| Source | Verified information used | Credibility and limits |
|---|---|---|
| [HL7 mCODE current published guide](https://hl7.org/fhir/us/mcode/) | Version 4.0.0, STU4; six data groups: patient, disease, assessment, genomics, treatment, outcomes | Official interoperability specification. It defines representation patterns; it is not a clinical checklist or a treatment guideline. |
| [mCODE disease characterization](https://hl7.org/fhir/us/mcode/group-disease.html) | Separate diagnosis status from encounter disease assessment; record risk/classification system and value with contributing observations | Supports the information model. Does not prescribe an AML classification or auto-assign risk. |
| [mCODE health assessment](https://hl7.org/fhir/us/mcode/group-assessment.html) | Comorbidities, dated performance assessments, laboratory results and relevant vital signs | Supports displaying health context and changes over time; does not establish treatment fitness automatically. |
| [mCODE genomics](https://hl7.org/fhir/us/mcode/group-genomics.html) | Genomics report, variant and region-studied are separate; test type and specimen context matter; reported negative genes are explicit | Supports avoiding an undifferentiated “negative molecular panel.” It does not determine clinical significance for Geevi. |
| [mCODE treatments](https://hl7.org/fhir/us/mcode/group-treatment.html) | Requests and actual administration are separate resources | Supports the app's separation of planned work and actual care. It is not a prescribing workflow specification. |
| [Döhner et al., ELN 2022 recommendations, PubMed](https://pubmed.ncbi.nlm.nih.gov/35797463/) | AML disease classification, genomic diagnostics, measurable residual disease, genetic risk and response criteria are distinct topics | Original expert-panel publication, Blood 140(12):1345–1377; DOI 10.1182/blood.2022016867. Abstract verified, detailed full text not used for clinical rules. |

Relevant short quotes:

> “mCODE does not define a specific set of information that must be collected for each cancer patient.” — [mCODE overview](https://hl7.org/fhir/us/mcode/)

> “The staging or risk assessment system, method, or protocol used” — [mCODE disease characterization](https://hl7.org/fhir/us/mcode/group-disease.html)

> “multiple instances may exist for a single patient.” — [mCODE performance assessments](https://hl7.org/fhir/us/mcode/group-assessment.html)

> “revised ELN genetic risk classification, revised response criteria” — [ELN 2022 abstract](https://pubmed.ncbi.nlm.nih.gov/35797463/)

## What the oncologist should see first

This proposed organization is a product inference from the standards and current code, not a mandatory mCODE dataset.

| Screen element | Useful content | Ownership and uncertainty |
|---|---|---|
| Patient and episode header | Patient name, namespaced identifier, age/date-of-birth if documented, episode title, responsible clinician/team | Demographics and identity association are verified records. Do not invent an exact age from “adult.” |
| Case summary | Reason for referral; documented diagnosis and current clinical status; date and diagnostic/classification edition where stated | Label source-reported diagnosis separately from the treating oncologist's assessment. A laboratory finding alone must not become an app-generated diagnosis. |
| Decision needed | A short clinician-authored question, for example “Review new presentation with final molecular report pending; agree the next planning action” | Show author, date, relevant uncertainty and the supporting profile. A preparation pathway is not a treatment recommendation. |
| Evidence snapshot | Marrow/pathology, flow, cytogenetics and molecular results; specimen, method and date; key repeated blood results | Each result links to the original source and verification state. Pending, untested, unreported and not detected remain visibly different. |
| Patient context | Documented function/performance status, relevant organ/comorbidity context, prior therapy and response, current symptoms | Show “not documented” when absent. Do not assume no prior treatment, normal function or fitness. |
| Patient goals | What matters to the patient, documented preferences, participants and practical access constraints | Keep patient-attributed discussion separate from clinician interpretation and from laboratory facts. |
| Plan and departmental knowledge | Current individual plan, disposition, exact shared protocol version and linked evidence/appraisal | A newly published protocol opens a patient impact review; it does not silently change the signed plan. |
| Next action | One prominent owned next action, missing information, review-needed reason and due follow-up | Distinguish coordinator verification work, clinician decision work, accepted handoff, scheduled care and actual care. |

Use a compact case summary above the six existing dimensions. Keep the source grids and complete timeline available below or as details. Move technical cutoff sequence and long digests out of the first scan while preserving historical review access.

## Current source-level findings

| Finding | Current code evidence | Minimum useful change |
|---|---|---|
| Clinical orientation comes late | `ProfileTimeline.tsx` renders Knowledge cutoff, six dimensions, trends, unresolved inputs, then Clinical assessment and Patient discussion | Add a top case-summary/planning section with assessment, goals, pending inputs and links to Decisions and Care. |
| Clinician can express only one structured dimension in the form | `ProfileTimeline.tsx` submits `dimension_notes` only for `fitness`; `services/profile.py` already projects all six dimensions | Expose optional notes for disease biology/classification, extent or disease-specific risk, fitness, prior therapy, current condition, and priorities. Retain the distinction between these notes and verified results. |
| No patient search | `PatientList.tsx` presents the complete list without a query input | Search by name and identifier; display issuer namespace. Useful immediately during a live demo. |
| Header omits clinical episode title | `PatientFrame.tsx` displays identity plus episode status/responsible team, although the episode has a title | Show episode title and team so “new AML presentation” is visible without opening another screen. |
| Trend display hides specimen context | The profile API returns `specimen_label` for each point, but the trend table renders only day/value in one arrow sequence per analyte | Include specimen label and result state; avoid implying different specimens or methods are interchangeable longitudinal measurements. Do not automatically select a preferred result. |
| Raw report details dominate the page | Each six-dimensional card lists every verified observation with provenance | Add concise summaries and make expanded source detail secondary. Preserve original-source links in both views. |
| Genuine oncology evidence is absent from seeded research | `scenario.json` calls both audit documents invented and says effects are unknown | Replace research-library seed citations with verified original publications/standards and clearly authored summaries. Retain fictional patient records as a separate labelled clinical simulation. |

Already valuable: explicit source verification, immutable originals, specimens and report relationships, distinct missing-result states, dated repeated observations, clinical assessment versions, patient discussion, expected inputs with owner/next action, historical profile snapshots, and a multi-lane timeline. These should remain.

## What the oncologist will search for

The demo should distinguish three search intentions rather than putting all text into one generic search box.

1. **Find the person or case:** name, identifier, episode title, assigned team, cases awaiting a clinician decision or follow-up. Patient identifiers remain namespaced and authorization scoped.
2. **Understand the patient's evidence:** marrow/pathology report, a named molecular finding, cytogenetics, test method/specimen/date, a pending report, previous treatment, a correction, or the evidence used for the current plan. “What changed since my last review?” is often more useful than another full document list.
3. **Investigate the clinical question:** disease setting, diagnostic/classification question, biomarker or method, patient population, treatment exposure, comparison, endpoint and follow-up duration. Search terms come from the clinician's stated question, with no need to send patient identifiers to an external service.

For this AML demo, suitable **research questions for a clinician to refine** include: how diagnostic and genetic-risk frameworks differ; what a genomic study population represents; how assay/specimen and treatment history affect applicability; and how response or measurable residual disease endpoints were defined. These are not proposed treatment choices. The 2022 ELN record supplies a genuine starting reference, not an automatically adopted local policy.

For minimum functionality, in-app patient and research-library filtering plus a clearly marked PubMed search link are sufficient. An external PubMed search is not an in-app systematic search or an automatically completed appraisal. Save the actual query, source citation, search date and clinician-authored applicability/limitations when a source is brought into the research workspace.

## A useful clinician demo sequence

1. Find Meera by identifier and open the case summary. State the decision question, patient goals and missing molecular information.
2. Open one original report from a displayed finding. Show specimen/date, source wording and source-verification history; distinguish that from the oncologist's interpretation.
3. Open the research workspace on a real, verified oncology reference. Inspect the actual citation and source access, then the authored appraisal: question, population, methods, outcomes, uncertainty and applicability to the department.
4. Show a department proposal and named independent review. Explain that accepting the appraisal does not publish a protocol or approve this patient.
5. Return to Meera. Show the exact departmental protocol, criterion-level applicability, patient preference, unresolved exception and the individual planning decision.
6. Show the accepted care-team task and scheduled follow-up. Record actual care only through an attributed care record. The profile then shows the next owned obligation.
7. Show a new result or changed protocol opening a review-needed item while preserving the previous signed decision.

Do not start the demo by making the oncologist verify every source candidate. A reviewed fictional case may demonstrate a prepared state, provided its synthetic provenance and demonstration history are explicit. Keep a separate unreviewed case available to show the coordinator's intake task.

## Replacing fixtures with proper research documentation

Replace **invented research audit papers** with a research library containing real citation metadata, a source URL/DOI, verified access status, a short authored summary and an appraisal draft. Use actual study design/population/endpoints from the accessed source; “not assessed” is better than fabricated numbers. Do not copy a complete copyrighted paper into the app unless reuse is permitted. A bibliography entry with a source link and carefully scoped summary is a proper research document.

Keep **patient simulation documents** synthetic, but make their format research-informed: issuer, patient identifier, accession, specimen, collection/report dates, report status, method, findings, limitations and explicit amendments. Real cohort rows, unrelated study-subject reports or lung-cancer examples must not be passed off as Meera's AML chart. Public datasets inform the schema and a separate research/reference workspace. They are not a source of a coherent individual patient journey unless that use and all joins are valid and authorized.

## Effectiveness claim and clinician validation

The app can plausibly help a department prepare a case, retain evidence provenance, coordinate missing inputs, review shared knowledge, and document patient-specific follow-through. This review does not show that it improves outcomes or recommends appropriate treatment. It is not yet a longitudinal oncology research database merely because it has an appraisal form.

During the demo, measure whether the oncologist can find the decision question and missing information quickly, locate the original evidence, explain the current shared-protocol version, distinguish paper appraisal from patient approval, and identify who owns the next action. Ask them which summary fields and classification editions they actually use, what planning steps cannot wait for a complete report pack, and whether the proposed independent-review roles match their department. Those answers determine the next clinical workflow revision.
