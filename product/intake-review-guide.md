# Clinical intake workspace — review guide

11 October 2026. Review-format prototype for Meera and Arun, both fictional cases. Open `http://127.0.0.1:8765/product/aml-screen-walkthrough.html` with `python3 product/serve-demo.py` running from the workspace root.

The main app now begins with an oncologist's patient worklist. The previous PDF-research and evidence-to-sign-off demonstration is preserved at [Research & evidence lab](evidence-review.html), with its own existing case progress.

## What a clinician can review now

1. **My patients / Today:** open Meera or Arun. See the current review state, next action and owner. This is not AI triage or an urgency score.
2. **Patient profile:** load the fictional report bundle. The report contains clearly fabricated diagnosis, molecular findings, report/specimen context, current assessment and prior-treatment wording.
3. **Reports & source review:** inspect the original PDF. Confirm patient identity and specimen/date context. Select a finding to highlight its extracted text location on the actual rendered page. Inspect the surrounding text, then confirm or correct the reviewed value; corrections require a reason and retain the original quotation.
4. **Profile & changes:** verified report wording populates the summary. Unverified findings remain labeled candidates. Biomarkers, condition and prior treatment stay separate. Not detected, not tested, not provided, pending and not reported retain their literal source wording.
5. **Missing information:** review the configured missing/uncertain items. These are limited prototype checks, not an exhaustive disease-specific diagnostic workup. Different source values remain visible for reconciliation rather than automatically overwriting one another. A new result may represent a real longitudinal change; the software does not decide that question.
6. **Scoped profile review:** record exactly what you reviewed and what is unresolved. A partially reviewed profile can receive a narrowly scoped review with its outstanding items retained. This does not establish a final diagnosis, complete trial eligibility or authorization to treat.
7. **Draft an update:** try `Add task: obtain the original molecular report with the specimen date.`, `Record concern: the family has a question for the clinical team.` or `Update next step: arrange a review of the current assessment and goals.` Review the target and before/after proposal, then apply or discard. Unrecognized prompts are rejected rather than interpreted as clinical advice. A prepared proposal does not mutate the chart. A stale proposal or one belonging to another patient cannot be applied.
8. **Course & encounters:** record fictional observations, problems, reasoning and a continue/reassess/modify decision. Sign the encounter after recording the current profile-review scope. Its snapshot includes the reviewed facts and previous plan; its next action becomes an owned task. A planned event does not mean treatment happened.
9. **Clinical care team / Coordinator:** review their responsibilities and task statuses. Receipt, acceptance and completion remain different. Clinical care staff can read source reports; clinical interpretation/sign-off is assigned to the oncologist in this simplified demo. Patient/family see a restricted companion, with no clinical approval controls.
10. **Review history:** inspect earlier signed scopes and events. Export a JSON review packet if useful for the review discussion. This contains case data, quotations, source hashes, coordinates and history; it does not bundle original PDF/image bytes.

## Scans and images

Import a PNG/JPEG image or try the fictional scanned report. The original is displayed with fit/zoom/panning. Use **Mark a region** and drag a rectangle, or **Region coordinates** for a keyboard-accessible percentage rectangle. Add a clinician note. The annotation retains its document fingerprint, page, normalized coordinates, author and time.

Blue regions are explicitly clinician annotations. Amber regions are text extraction locations. Neither is an AI lesion detection. A source marker is not a clinical interpretation or diagnosis. Image-only inputs generate no machine findings; they require manual review or a separately validated OCR workflow. If a report contains no supported labels, its original remains reviewable and no missing finding is inferred normal.

This viewer does not implement DICOM series, window/level, calibrated measurements, comparison studies, radiology/pathology model inference or diagnostic display validation. Use original specialist image systems for diagnostic interpretation. The image sample is a rasterized fictional report, not a fabricated clinical scan presented as real imagery.

## What is real, simulated and absent

| Capability | Current implementation |
|---|---|
| Original report upload | Real browser-local PDF, PNG and JPEG import; SHA-256 fingerprinting and local original-file persistence |
| PDF text extraction | Real PDF.js text extraction and source-item coordinates, with limited labelled-field parsing |
| Field interpretation | Clinician-entered verification/correction; not an AI clinical assessment |
| Summary | Template composition of verified report wording, with links to each source |
| Scan review | Original display and human-authored region notes; no OCR or machine interpretation |
| Chat | Deterministic command-to-proposal parser for tasks, concerns and next-step text; no general LLM connected |
| Reviews and history | Working local state transitions, preserved snapshots, attribution and simulated role checks |
| Medical-grade accuracy | Not established. These fixtures and tests validate prototype behavior, not clinical performance |
| EHR integration | None. No external write-back, prescribing, pharmacy, scheduling, delivery, billing or patient-identity integration |

Document limits: PDFs ≤15 MB, ≤100 pages and ≤300,000 extracted characters; images ≤10 MB, ≤12,000 pixels on either axis and ≤40 million pixels total. Corrupt or password-protected PDFs return errors. Missing originals require re-importing the identical file. PDF text boxes come from item geometry and can be approximate for rotated text, unusual fonts or complex layout; exact extracted quotations and visual review remain necessary.

The narrow parser recognizes the named fields in `IntakeModel.labels`; it does not claim coverage for arbitrary external reports. It does not normalize variants, units, tumour percentages, assay sensitivity or biomarkers into clinical eligibility rules. Multiline or tabular findings need manual review. Specimen, method and date appear as source-linked context fields, but this prototype does not establish complete analyte-to-specimen/assay relational linkage. That must be implemented and validated before structured results are used clinically.

## AI implementation path to review with the team

1. Preserve the original report and establish patient, episode, document version and specimen identity before chart association.
2. Extract text and geometry; route image-only/low-quality pages to an evaluated OCR system. Keep OCR uncertainty and the original image visible.
3. Use a schema-constrained clinical extraction model to propose only what the source supports: reported diagnosis, marker/variant, result, unit, specimen, dates, assay/method, status and exact supporting passage/region. Source text is data, not model instructions.
4. Check quotes/coordinates and typed values independently. Detect negation, duplicates, amendments, discrepant values and unsupported assertions. Abstain rather than filling missing facts from medical assumptions.
5. Present a source-linked draft with uncertainty and omissions. Use structured clinician correction and scoped review; retain rejected candidates and reasons for error analysis.
6. Build summaries only from attributed records. Chat produces explicit versioned changes rather than silently rewriting facts, original reports or clinical orders.
7. Integrate approved results into the authoritative patient record through an agreed interface and reconciliation policy. Avoid duplicated entry or conflicting local/upstream plans.

A future diagnostic-support capability is a separate intended use from transcribing a report's reported diagnosis. It would need separately validated clinical reasoning, input completeness/context, uncertainty handling and clinician workflow. This prototype does not implement it.

## What “high accuracy” needs to mean

Do not label the product medical-grade because the UI has signatures or because a model has a high aggregate score. Before relying on it, evaluate representative institution-authorized material against independently adjudicated reference annotations. Separate development and evaluation sets and include unseen layouts, external laboratories, scan quality, tables, language variation and amendments.

Measure patient/specimen association errors; field-level precision and recall; clinically important omissions; biomarker/variant identity, value, units and negation; date/method/context linkage; source-region correctness; unsupported generated claims; conflict/abstention behavior; reviewer correction burden; and errors remaining after clinician review. Evaluate clinical significance and subgroup/document-type performance, not just one overall percentage.

For images, evaluate the actual diagnostic task separately if one is later introduced. Report transcription performance does not validate lesion detection, radiology interpretation or diagnosis. For the combined human-AI workflow, measure whether reviewers notice failures and whether assisted preparation saves active time without increasing residual errors.

Clinical owners must define acceptance thresholds and failure procedures for the intended use. Independent clinical validation, production privacy/access/audit controls and deployment governance remain outstanding. Primary-source grounding is in [AI intake validation](../research/ai-intake-validation.md).

## Review questions for the oncologist

- Does the profile contain the information needed at the first visit, and which information is disease/decision-specific?
- Are specimen, collection date, result status and source context clear enough to avoid using the wrong or stale finding?
- Does clicking a finding take you to the right place quickly enough? Which report layouts or image tools are essential?
- Which checks can trained staff prepare, and which need specialist interpretation? Where would scoped review reduce repeated work?
- Does the encounter capture what matters for the next decision, including a justified no-change decision?
- Which existing system owns the approved chart and orders, and how should reviewed information return to it?
- Compared with your current process, what saves time, what adds clicks and what error would be unacceptable?

## Verification and local storage

Run `node --test product/tests/*.test.cjs`. `tests/intake-model.test.cjs` checks provenance, unknown states, identity/role gates, immutable history, chat proposals, encounter transitions, conflicts and annotation bounds. `tests/browser-intake-check.js` exercises the new patient paths through UI forms. The 37-assertion patient-flow script and the six-assertion `tests/browser-intake-source-check.js` passed. The source script covers reload persistence, image-region review and clinical-role restrictions after the patient-flow script. The earlier browser scripts should now be run at `evidence-review.html`; their 66 workflow assertions and four PDF-error checks also passed after the shared reader changes. The complete model suite currently passes 33 tests. Desktop/mobile layouts and an actual file-input wrong-patient review attempt were checked. These tests do not establish clinical extraction accuracy.

The new workspace uses localStorage key `casebook-intake-v1`; PDFs are retained in IndexedDB `casebook-pdf-library`, and image bytes in `casebook-intake-images`. The earlier evidence demo uses its previous separate case store. Resetting one case does not delete original files or the other case. Clear this site's browser data to remove retained originals and records. Storage failure is reported; export the packet before closing if changes are only held in memory.

These are not tamper-proof clinical records or secure multi-user roles. No real patient data, external messages or treatment orders are involved.

## Workspace navigation and six-dimensional profiles

The homepage is now patient-independent. Choose **My patients**, then explicitly open Meera or Arun. Profile, sources, course, updates and history are tabs inside that case, not global destinations with an implicit selected patient.

Profiles group source-linked findings into disease biology, disease extent, patient fitness, treatment history, current condition, and patient priorities/access. Each dimension separates verified wording, unverified candidates, original reports and missing-information prompts. The additional synthetic context PDFs demonstrate extent, functional assessment and documented preferences. Importing them never verifies them automatically.

Each new signed encounter retains all six dimensions, source identities, verification statuses, missing flags and optional clinician assessment notes. Compare the current profile with any retained encounter. A new source is an addition; a corrected transcription is a correction; verification is a review change. None alone means clinical improvement. Earlier encounters without full snapshots show comparison unavailable; history is not reconstructed from current information.

Optional dimension notes in the encounter form do not change extracted facts. A plan change still requires a fresh scoped profile review. Missing information remains in signed snapshots. The checks are not exhaustive diagnostic requirements.

## Independent research lab

`evidence-review.html` now starts with research questions, not patients. Upload PDFs, inspect original candidate passages, record an appraisal and limitations, and simulate a scoped library review. The extraction is limited keyword matching; no general AI, live literature search, complete systematic review or automatic clinical eligibility assessment is implemented.

After library review, explicitly choose Meera or Arun for an applicability comparison against their current saved six-dimensional profile. For each source criterion, select a verified patient fact and record Matches, Differs, Unknown or Not applicable with reasoning. Missing values remain Unknown; study outcomes are never individual predictions. A separate applicability signature snapshots both patient and source versions. Changed evidence or patient revisions require a new review.

The earlier plan/handoff prototype remains at `patient-evidence-review.html`, with its prior browser storage preserved. It uses separate fictional records and is explicitly labelled as an earlier demo; it is not synchronized with the new clinical profiles or research lab. This prototype does not provide real clinical signatures, secure authentication or a production audit trail.

Validation: run the model tests with `node --test product/tests/*.test.cjs`. Browser scripts run in order: `browser-intake-check.js`, `browser-intake-source-check.js`, `browser-dimensions-check.js` on the clinical route, then `browser-research-lab-check.js` on the research route. Use a test browser, since these scripts reset the fictional case progress. Earlier workflow/PDF tests now use `patient-evidence-review.html`.

## Research-linked protocol approval and care-team handoff

From a current signed applicability review in the research lab, choose **Propose a patient plan change**. The link opens that same patient’s **Evidence & protocol** tab and selects the actual retained review. Existing signed reviews also appear in the patient’s review selector; stale or other-patient reviews cannot authorize a draft.

The oncologist writes a proposed protocol, rationale/alternatives, unresolved questions and required actions, monitoring instructions, review timing, receiving team and requested task. Saving leaves the current patient plan unchanged. The review screen shows before/after text, the signed applicability assessment, study passages/results, patient source passages and limitations. Original research PDF pages remain accessible in the patient workspace.

A current scoped profile review and explicit approval of the exact saved draft are required to change the plan. Unsaved edits block signing. Approval creates the next plan version and retains the previous plan, profile scope, source/applicability snapshots and review identity/time. A new proposal does not automatically replace an existing approval.

Handoff is a separate action available to the oncologist or coordinator. It sends the fixed, approved packet to its named team **within this browser only**. Switch to Clinical care team to read the same packet and acknowledge its next action. This does not send an external message, create drug orders or record treatment administration. Family views do not expose these draft or signature controls.

Patient/context changes, reopened research or newer applicability reviews require fresh review before another handoff/acknowledgement. Earlier approvals and recorded acknowledgements are retained. The current packet and historical packets can be exported as JSON. This is still a fictional-data prototype with simulated roles/signatures, not secure clinical authorization.

Additional validation: `protocol-model.test.cjs` covers role boundaries, stale context, immutable snapshots and repeat approval history. After the clinical and research fixtures are prepared, run `browser-protocol-prepare.js` on the research route; it follows the actual patient-plan link. Then run `browser-protocol-check.js` on the resulting clinical route to check draft, approval, coordinator handoff and care-team acknowledgement.
