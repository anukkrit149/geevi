# AML app blueprint: one patient record, three working views

**Current product direction:** [Oncologist workspace: patient care and reviewed knowledge](oncologist-workspace-blueprint.md) supersedes the evidence-first navigation and initial build order below. The revised entry point is a caseload worklist, evolving patient profile and encounter feedback loop, connected to a shared reviewed knowledge library. The main clickable app now demonstrates the initial patient-intake and encounter-review slice; see [the review guide](intake-review-guide.md). The earlier evidence demo remains in `evidence-review.html`.

11 October 2026 · Product proposal using fictional Meera and Arun cases.

This is a screen and data specification, not a deployed app or validated hospital workflow. The accompanying `aml-screen-walkthrough.html` now implements an interactive synthetic evidence-to-handoff demo, with browser-local progress, evidence attachment, applicability review, simulated plan signatures and receiving-team acknowledgement. Its role selector is a demonstration control, not production access control. It has no real patient records, integrations, prescribing or notifications. The earlier read-only storyboard is preserved in `aml-journey-storyboard.html`.

**Expanded product direction:** the subsequent [evidence-to-protocol blueprint](evidence-to-protocol-blueprint.md) adds clinician-owned literature, patient–evidence applicability review, versioned decision sign-off, specialty protocol execution, and separate clinical/family caregiver roles. The updated interactive demo implements example evidence matching, simulated versioned approvals and handoff acknowledgement; specialty protocol execution and clinical integration remain proposals. See [demo usage and verification](workflow-demo-notes.md).

## Product boundary and first outcome

First prove this workflow in one haematology service: **referral accepted → evidence collected → clinician review → approved decision documented → next action assigned → handoff acknowledged**. Requirements are tied to a named decision, not a universal completeness score. The app supports urgent parallel work; it does not require every diagnostic result before every clinical action.

The first release is a coordination layer. Existing laboratory systems remain authoritative for authorized results; the hospital EMR remains authoritative for clinical orders, prescribing, consent and actual administration. The app owns case-preparation tasks and acknowledgements, and links to or captures attributed copies of approved clinical documents. Integration and ownership must be agreed with the hospital before production.

## Navigation by role

| Role | Landing screen | Patient-level navigation | Primary job |
|---|---|---|---|
| Oncologist / haematologist | My reviews: new evidence, decisions awaiting review, amendments, assigned follow-ups | Overview, Evidence, Decisions, Timeline | Interpret evidence, document decisions and assign clinical follow-through |
| Coordinator | Work queue: unassigned, awaiting external work, due/overdue, awaiting acknowledgement | Overview, Evidence, Tasks, Timeline | Obtain records and arrange the next step without making clinical decisions |
| Patient / authorized caregiver | My next step | My care, Visits, Reports, Contact | Understand the agreed next step and act on clear instructions |

Patient/caregiver identity and authorization are separate. Patients see their own record; a caregiver sees only explicitly authorized scope. Hospital users need tenant/site, role and care-team restrictions, enforced server-side in production. Audit both reading and changing sensitive data.

## Screens, data and actions

| Screen | Data displayed and origin | Allowed action / output | First release? |
|---|---|---|---|
| Clinical review inbox | Patient/episode, named decision, assigned clinician, new report/version, unresolved discrepancy, urgency set by staff, time waiting | Open evidence; acknowledge review with a disposition; assign further action | Yes |
| Case overview | Diagnosis status, linked diagnostic reports, current assessment, next decision, pending evidence, attributed approved-plan summary, care team | Navigate to source; record review outcome; link approved decision | Yes |
| Evidence viewer | Original document, extracted candidates, source page/section, specimen and collection date, author/report date, result status/version, verifier | Authorized reviewer confirms/corrects candidate; clinician interprets; coordinator checks identity/receipt only | Yes, manual entry first |
| Decision and handoff | Clinical question, evidence versions considered, decision author/date, signed source in EMR, patient discussion, unresolved items, next action and owner | Record/reference approved decision; supersede with reason; assign next action; capture receiving-team acknowledgement | Yes, no prescription entry |
| Coordinator queue | Case, task, clinical question it supports, assigned owner, external department, due date agreed by team, blocker, last contact, completion evidence | Assign; update operational status; attach receipt evidence; escalate unresolved work | Yes |
| Specimen/report tracker | Test order reference, specimen ID, collection, laboratory receipt, adequacy/status, authorized report, clinical acknowledgement | Record observed status; chase transport/laboratory; link reports and amendments | Yes, user-entered initially |
| Timeline | Timestamped source events, report versions, reviews, decisions and task completions | Filter; open underlying event; retain correction history | Yes, narrow event scope |
| Patient next-step page | Care-team-approved explanation, confirmed next visit/location, preparation, documents to bring, approved contact route | View; confirm attendance or request a callback only if a staffed workflow is available | Limited companion after internal loop works |
| Patient reports | Authorized original reports and separately labelled explanations, source/date, clinical-review state | Read/download according to hospital policy and access rights | Later in first pilot or subsequent release |
| Treatment course | Authoritative signed orders, actual delivery, holds, supportive-care events and subsequent reviews | Read integrated events; route reconciliation tasks | Later; no independent prescribing or clearance |
| Response / transplant workspace | Morphology, count recovery, assay-specific MRD, clinician response category, transplant referral/candidacy/donor information | Track clinician-authored assessment and subsequent tasks | Later |
| Symptom monitoring | Patient-entered symptoms, observation time, staffed escalation queue and disposition | Submit and acknowledge with a defined response process | Later, only with clinical staffing |

A received report is not clinically verified. Acknowledgement requires a disposition: no plan change, further review, new task, revised plan, or another documented outcome. An amendment reopens appropriate review while preserving earlier decisions. A result is not silently hidden until a clinician explains it: original-report availability follows the institution's applicable release policy and patient rights. Draft AI explanations are distinct from authorized source reports.

## Mapping Meera and Arun into the app

Their disease facts and fictional treatment courses come from the [two-patient research](../research/two-aml-patient-workflows.md). The examples below are product scenarios, not treatment rules.

| Moment | Oncologist view | Coordinator view | Patient view |
|---|---|---|---|
| Meera: decision preparation | AML established; NPM1 reported; completed FLT3 result linked; chromosome report awaiting clinical review; fitness assessment attributed; next decision labelled | Obtain any missing source documents; ensure the newly received chromosome report has a review owner | “Your team is reviewing your test results.” Show a confirmed review visit if one exists, otherwise “Visit being arranged” |
| Arun: decision preparation | AML evidence, genetic findings and existing cardiac history; current specialist fitness assessment still awaited; pending evidence is not treated as normal | Track cardiology/fitness assessment and booking; show who accepted referral and what is outstanding | Explain the additional assessment and practical next step using approved wording; no automatic forecast of treatment or prognosis |
| Meera: plan approved | Attributed intensive-treatment strategy with source/version; current orders accessed in EMR; required handoff shown | Arrange the approved admission/handoff and document receiving-team acknowledgement | Approved explanation of hospital treatment and only confirmed arrival/preparation details |
| Arun: plan approved | Attributed lower-intensity strategy; clinician rationale records fitness and disease considerations; monitoring plan linked | Coordinate treatment visit or admission selected by team, monitoring and practical support | Explain that treatment requires close monitoring; do not imply it is automatically outpatient |
| Meera: response review | Morphology, count recovery and NPM1 MRD appear separately; clinician-recorded response and post-remission plan linked | Track ordered response tests and subsequent consolidation appointments | “Your doctor has recorded remission and discussed the next phase.” Never “cured” inferred from a negative MRD result |
| Arun: response review | Serial assessments; clinician-confirmed remission in this fictional case; current benefit/tolerability review and continuing plan | Track ongoing cycles, required reviews and unresolved support tasks | Approved ongoing-treatment explanation and next review; remission does not auto-end the course |
| Either: changed or amended evidence | Prominent “New evidence needs review”; prior decision remains visible and linked to evidence known then | Assigned review task, acknowledgement status and escalation path | Updated information after appropriate release/review; cancelled or changed appointments clearly identified |

## Evidence screen wireframe

```text
Patient identity / episode / role              Next decision: treatment planning

Original report                   Structured candidate facts
[document and source location]    NPM1: reported finding · source page
                                  Specimen / collection / assay / version
                                  Extraction: unverified | verified by ...

Pending or conflicting evidence   Clinician interpretation
[named item + owner]              [authored assessment + date + evidence links]

Review disposition                Next action
[no change / further review / ...] [owner + due date + completion requirement]
```

Keep diagnostic facts, patient fitness, goals, and logistics in separate sections. No AI-derived treatment card, prognosis score or green “safe to treat” badge. Information being complete for one decision does not authorize drug administration.

## Data model and authority

| Entity | Key fields | Authority / editing boundary |
|---|---|---|
| Patient and episode | Local identifiers, identity-match status, diagnosis episode, care team, patient/caregiver permissions | Registration/EMR; coordinator can reconcile within permissions |
| Order and specimen | External order ID, requested test, requesting clinician, specimen ID/site, collection and received times, status source | Ordering/laboratory systems; app tracks attributed operational updates |
| Report and version | Original file/URI, author/lab, specimen links, issue date, version, amendment relationship, authorization status | Issuing laboratory; app never rewrites the original |
| Extracted fact | Value/unit, assay, source location, collection time, detection limit where applicable, candidate/verified/conflicted status, verifier | Candidate extraction separate from human verification |
| Clinical assessment | Diagnosis/risk/fitness/response type, author, date, relevant system/version, evidence versions, uncertainty | Authorized clinician |
| Decision/plan reference | Question, signed EMR reference, plan version, rationale, patient discussion, author, unresolved evidence, supersession | Clinician-authored; app does not convert a plan to drug orders |
| Task | Owner, accepting team, case, dependency, due time, reason, last contact, operational state, completion evidence | Coordinator or clinician according to task type |
| Review acknowledgement | Reviewer, report/plan version, time, disposition, resulting task | Authorized clinical reviewer |
| Visit and handoff | Requested/confirmed/rescheduled/cancelled state, facility/contact, preparation source, receiving-team acknowledgement | Scheduling system/team; patient view uses confirmed state |
| Audit event | Actor, role, timestamp, before/after reference, reason and source event | Append-only audit service; corrections create new events |

Do not combine document status, extraction status, clinical interpretation and task status into one field. “Not ordered,” “pending,” “insufficient sample,” “equivocal” and “not detected” are distinct. A future interface should retain import IDs, timestamps and source versions to prevent duplicate imports or stale data replacing newer information.

## What to build first

Build in dependency order; sprint duration and story points require the actual team's capacity, so none are invented here.

### First vertical slice: a result reaches a decision and an acknowledged handoff

1. **Access and patient identity:** care-team roles, case/episode registration, original document storage, access/audit history.
2. **Evidence and owned tasks:** manual report upload, specimen/status fields, source-linked facts, assignment, receipt tracking and clinical-review queue.
3. **Review and handoff:** clinician disposition, link to signed decision, next action with owner/due date, receiving-team acknowledgement.
4. **Patient companion:** approved next-step summary, confirmed visit, preparation and staffed contact details. Initially read-only; reminders/callback requests require delivery/reply ownership.
5. **Assisted extraction:** only after the manual workflow works, add draft extraction/source highlighting and reviewer corrections. Treat automation accuracy and operational utility as separate evaluations.

The first slice supports both fictional patients through the first approved decision and handoff. It does not need chemotherapy scheduling, radiation, transplant donor management, automated triage or a complete EMR. Later, add existing-system integrations, treatment-event visibility, response/MRD coordination and longitudinal follow-up. Expand only where local workflow evidence supports it.

### Initial backlog and acceptance criteria

| Priority / story | User value | Acceptance criteria |
|---|---|---|
| P0: establish case and access | Coordinator can prepare the correct patient's case | Given a potential duplicate, registration requires reconciliation rather than silent merge. Unauthorized users cannot retrieve case data through API or UI. Record reads/writes are attributable. |
| P0: receive report | Coordinator can stop chasing received documents | Given a matched report, upload preserves original and source metadata. Receipt updates only retrieval status. Missing patient/specimen linkage is visible. Duplicate import does not produce duplicate review tasks. |
| P0: inspect evidence | Clinician can verify the basis of a summary | Every displayed fact opens its source location. Unverified candidates stay labelled. Correction preserves the original and reviewer attribution. Unsupported extraction stays blank/pending rather than fabricated. |
| P0: review and act | Clinician can close the clinical loop | Receipt does not count as review. Reviewer records disposition. Any follow-up task needs an owner; unresolved assignment remains visible. An amended report triggers a new review linked to prior decisions. |
| P0: coordinate handoff | Coordinator can know whether another team accepted work | Given an assigned action, requested, accepted and completed are distinct. Completion requires evidence appropriate to task type. Unacknowledged handoffs stay in the queue. Urgent escalation is configurable by the service and never relies on email delivery alone. |
| P1: patient next step | Patient can understand and prepare | Only their own or authorized dependent's data is accessible. Tentative visits are labelled. Approved instructions show author/date. Missing information is stated clearly. No symptom collection without a staffed response workflow. |
| P1: assisted extraction | Staff can reduce transcription | Extracted candidates have source spans and remain reviewable. Wrong patient/specimen, negation, dates and amended values are included in evaluation. Failure leaves original documents usable; no workflow silently completes from extraction alone. |

All screens must support keyboard navigation, visible focus, readable status labels beyond colour and responsive layouts. Server-side access control, secure document handling, recovery, and audit integrity are production requirements, not demonstrated by the local storyboard.

## Pilot and success measures

Start with synthetic cases, then an institution-authorized shadow evaluation with appropriately handled records. Confirm responsibilities with a haematologist, coordinator, diagnostic staff, IT and patient representative. Acceptance by these roles remains outstanding.

Measure active case-preparation minutes, missing evidence at the named review, report authorization-to-clinical acknowledgement time, unacknowledged handoffs, overdue tasks by reason and incorrect/missing facts with severity and denominators. Track extra data-entry burden too. Set numerical success criteria with the partner hospital after measuring baseline; faster documentation alone does not establish improved outcomes.

## References and limits

- [Two fictional AML journeys](../research/two-aml-patient-workflows.md): underlying clinical examples and sources.
- [Oncology workflow research](../research/oncology-workflow-and-system-opportunities.md): wider process and evidence limitations.
- [NCG medical oncology requirements](https://www.kcdo.in/src/docx/ner-medical-oncology-module-2.0.pdf): separation of protocols, physician orders, nursing records, toxicity and summaries, reviewed in prior research. A requirements specification does not establish implementation in any hospital.

All screen architecture, statuses, backlog and pilot design above are proposals. No clinical recommendation engine, hospital integration, legal compliance, adoption, or commercial demand is established by this artifact.
