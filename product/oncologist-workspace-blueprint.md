# Oncologist workspace: patient care and reviewed knowledge

11 October 2026 · Revised product direction following the user's clarification.

This supersedes the evidence-first landing screen and evidence-first build order in the earlier blueprints. It is a product specification, not a validated clinical workflow or complete EHR implementation. The main clickable app now demonstrates the caseload, report/profile preparation, source verification, guided chat proposals and encounter review described in [the intake review guide](intake-review-guide.md). The earlier evidence-review flow remains in `evidence-review.html`. These are local demonstrations, not a full EHR or validated AI system.

## Problem and product promise

An oncologist is responsible for many patients, each with a changing profile, a treatment course, pending work and decisions due at different times. Reconstructing the case from reports at every encounter and following up each dependency consumes attention. Separately, the oncologist needs to turn relevant research into reviewed, reusable knowledge without re-reading and approving the same paper for every patient.

The proposed product promise is: **See what needs your attention across patients, understand what changed in each case, decide and delegate the next step, and use reviewed knowledge when the decision needs it.** Reduced effort and better follow-through are hypotheses to validate with a service, not established benefits.

Two connected workflows:

1. **Patient care:** intake → verified current profile → patient-specific plan → planned and actual care events → observed outcomes and problems → clinician review → next plan version and assigned work.
2. **Knowledge:** clinical question or new publication → research request/intake → source extraction and appraisal → assigned reviews → resolution/approval for a defined scope → reusable evidence/protocol proposal → patient-specific applicability review.

The shared connections are the clinical question, evidence version, protocol version, patient plan version and review task. Research does not need to be the entry point for every routine visit.

## Starting from the oncologist's day

The landing page is **My patients / Today**. Its organizing question is “What needs my decision, and what can the team progress?”

A worklist row contains patient identity, diagnosis/context, course and current phase, next appointment or review, last relevant update, pending decision, blocker, owner and due time. Show staff-assigned urgency and reason; do not infer that the most incomplete record is the most urgent.

Useful queues are new patients awaiting profiling, reviews due, changes requiring attention, planned next events with unresolved preparation, and delegated work awaiting acknowledgement. Provide filters by care team, pathway and responsible clinician. The all-patients view remains available; stable cases are not silently hidden by an algorithm.

The coordinator prepares records and chases dependencies; clinicians interpret and decide; the receiving team records its work and observations. The interface should reduce repeated entry rather than make the oncologist operate every stage personally.

## Patient workspace and profiling

Patient profiling is an evolving, source-linked record, not a one-time questionnaire or inferred treatment recommendation.

| Profile section | Data and attribution |
|---|---|
| Identity and episode | Correct patient/episode, responsible team, relevant history and source identifiers |
| Disease characterization | Clinician-confirmed diagnosis/subtype, staging or disease-specific risk system where applicable, pathology and molecular findings, source report/version |
| Current condition | Dated functional/organ assessments, relevant comorbidities, medicines and allergies; unrecorded values stay unknown |
| Treatment context | Prior therapies, current phase, treatment intent/goals recorded by the clinician, patient preferences and discussion references |
| Reports and changes | Original document, specimen/observation and issue dates, extracted fact, verification status, amendments and conflicts |
| Practical context | Available support, access or scheduling constraints relevant to coordination; distinct from biological eligibility |

Requirements depend on the disease, decision and service. Do not require a universal report bundle or silently treat old assessments as current. Receipt, extraction verification and clinical interpretation have different statuses.

At an encounter, emphasize **what changed since the last reviewed decision**, with a route to the complete record and sources. Resolve a conflicting or corrected fact with attribution; preserve what the earlier decision used.

## Protocol template, patient plan and actual care

Keep these separate:

| Object | Meaning | How it changes |
|---|---|---|
| Shared protocol/pathway template | A versioned service-approved workflow for a defined use, with required inputs, roles, review points, branches and supporting evidence | Proposed revision undergoes the service's designated review and adoption process |
| Patient-specific plan | The clinician's application of a template to this patient's current facts and goals, including justified deviations and signed order references | Clinician reviews new information and approves a new patient plan version where appropriate |
| Care event | A planned cycle/session/procedure/review and a separate account of what actually happened | Authorized team documents actual delivery, non-delivery, observations and deviations with source/time |

The app can structure protocol parameters for the clinician to review, but matching facts does not authorize a regimen or dose. Existing authoritative ordering and administration systems remain the source of actual orders until an integration and expanded intended use are validated.

Medical oncology can group events by cycle and day. Surgical oncology needs preoperative, operative and postoperative phases; radiation has planning, quality review and fraction events. Reuse the longitudinal record and review/task pattern, not one universal session form. Begin with one service's pathway.

## The encounter feedback loop

For each relevant encounter, collect a structured account of what happened and what needs a decision. “Session” can be a treatment event or clinical review; scheduled review points are pathway-specific.

1. **Prepare:** show the last approved plan, changes since review, relevant current results, outstanding requirements and who owns them.
2. **Record actual events:** identify what was delivered or not delivered, by whom, when and under which order/plan version. A scheduled event is not proof of delivery.
3. **Capture observations:** source-linked response assessments when due, tolerability/adverse events, symptoms/function and patient concerns. Keep patient-reported observations separate from professional assessment.
4. **Capture workflow issues:** missing results, delays, coordination problems and practical barriers. Do not confuse operational failure with a treatment-effect finding.
5. **Review:** display the observations alongside the previous decision and relevant reviewed knowledge. The clinician records continue unchanged, request information/review, modify the patient plan, propose a different approach or another explicit disposition.
6. **Act:** identify what changed, the rationale, required approval, next review and tasks with owners. “No change” is a valid documented decision; every visit need not create a modified protocol.
7. **Close the loop:** assigned, accepted and completed work remain distinct. The next encounter starts from the reviewed state plus subsequent changes.

Do not require re-signing every unchanged fact. A scoped review can cover identified versions and changes. Material amendments create an impact-review task; they do not silently inherit old signatures or automatically stop existing treatment.

## Knowledge workspace

The knowledge workflow begins with a question or update, not just a PDF upload.

Example questions should be authored by the team: what uncertainty needs resolving, in which disease/setting, by when, and for which patient or shared protocol? A coordinator/researcher can prepare a source bundle; authorized clinical reviewers own interpretation and adoption.

Proposed screens:

- **Questions and research requests:** question, scope, requesting clinician, optional linked case/protocol, owner, due date, accepted/completed state and response bundle.
- **Research inbox:** submitted papers/guidelines and candidate updates, provenance, duplicate/version detection, whether a review is assigned and why the item is relevant.
- **Review room:** original source and exact passages; study population, intervention/comparator, endpoints/results, uncertainty and limitations; separate extraction verification and clinical appraisal; named reviewer questions and disagreement resolution.
- **Reviewed library:** searchable evidence cards with version, approved scope, reviewers, limitations, effective/review dates and superseded/retracted status when established. Personal notes and service-approved items are distinct.
- **Protocol proposals:** evidence linked to a specific proposed change, affected template version, required discipline reviews and adoption decision.

A requested review is not a completed review. Multiple reviews remain individually attributable; unresolved required reviews or disagreement cannot silently become approval. The service defines which roles and review scopes are required; the software should not invent a universal committee structure.

**Reuse the source review.** Verify extraction and appraise an evidence version centrally, then reuse that work across cases. For Meera or Arun, the clinician reviews the *patient-specific applicability*, not the identical source text from scratch. A changed source/version reopens the affected source review and creates linked impact-review tasks.

To stay current, the product can later collect updates from selected primary sources and produce a relevance queue. Initially support manually submitted updates and explicit review dates. “Latest” alone is not sufficient for adoption. New evidence identifies candidate affected protocols/cases for review; it does not rewrite plans automatically. No recurring monitoring service is configured by this proposal.

## Two feedback loops, different authority

**Patient loop:** observations → clinical assessment → patient-specific decision → next care event.

**Shared knowledge loop:** recurring questions/observations or new publications → research/appraisal → governed evidence/protocol proposal → approved new library/template version → case impact review where relevant.

One patient's experience can prompt a research question. It does not establish treatment efficacy or justify silently changing the shared protocol. Institutional outcome analysis needs defined cohorts, endpoints, follow-up, missingness and appropriate analytical governance; that is a later capability.

## Revised app navigation

| Screen | Main action | Primary user |
|---|---|---|
| My patients / Today | Prioritize reviews and see owned work across the caseload | Oncologist |
| Patient overview | Review current profile and changes with source access | Oncologist; coordinator within scope |
| Treatment course | See template, current patient plan, event timeline, actual versus planned care and next decision | Clinical team |
| Encounter review | Review observations and problems; record disposition and any revised plan | Oncologist and requested reviewers |
| Team tasks | Prepare cases, arrange care, accept work and close dependencies with evidence | Coordinator and clinical team |
| Knowledge | Request research, assign reviews and reuse reviewed evidence | Oncologist, designated research/review roles |
| Protocol library | Inspect approved templates and review proposed revisions | Clinicians and designated governance owners |

Patient and authorized family retain a separate companion: approved explanations, confirmed appointments, support tasks and a staffed route for concerns where provided. Their observations can inform a clinical review, but do not constitute clinical assessment or sign-off.

## Initial build order

Build **one connected daily-work slice**, with both care and knowledge represented:

1. Caseload worklist, case ownership and tasks.
2. Source-linked patient profile and longitudinal changes.
3. One versioned pathway template, patient-specific plan and encounter timeline.
4. Encounter review, explicit next decision, scoped sign-off and accepted handoff.
5. A small shared evidence library, a research-request queue and named reviews; case-specific applicability links back to this library.

The existing PDF viewer and matching components belong inside step 5 and within relevant case decisions. Do not make every visit repeat the attachment → extraction → signature wizard. Reuse its version/snapshot logic within the care loop.

Defer broad automated research discovery, predictive recommendations, institutional outcome modeling and full specialty coverage until the daily workflow is demonstrated. Avoid independent prescribing or delivery clearance in the initial prototype.

## Next clickable demonstration

Use the two fictional cases to show a workday rather than a paper-review exercise:

1. The oncologist opens the worklist and sees Meera's next review and Arun's unresolved assessment, with owners and reasons.
2. Opening Meera shows her current profile, plan and changes since her prior visit. The clinician reviews a synthetic encounter, records a disposition and delegates a next step.
3. Opening Arun shows the outstanding assessment and task status. When the fictional report arrives, a review item appears with its changes; the clinician records the next patient-specific decision.
4. A question from either case becomes a research request. A source bundle receives two requested, individually tracked reviews where this demo policy requires them.
5. A resolved review makes a scoped evidence card reusable in the library. The clinician assesses its relevance separately for each case.
6. A proposed template change stays pending until its designated approval. Existing patient plans retain their original versions and show any assigned impact review.

All encounter observations must be explicitly fictional. Do not fabricate actual treatment success, clinical findings or personalized drug instructions for the existing cases.

## Acceptance and learning

The next prototype should demonstrate that every displayed queue item opens the relevant case and decision; a report amendment appears as a change; actual care is distinct from planned care; no-change reviews and plan modifications both work; each next action has an owner; and a library review can be reused without transferring a patient-specific approval.

Measure preparation/review time per encounter, repeated data-entry effort, time spent reconstructing history, overdue review/task reasons, unacknowledged work, time from a research request to a reviewed answer, and inappropriate/stale/missing information encountered. Compare with the service's actual baseline. Do not infer improved outcomes from faster clicks or more approvals.

Clinical-workflow grounding and sources are recorded separately in [the supporting research note](../research/oncologist-workspace-feedback-loops.md). Screen organization, backlog, metrics and productivity claims here are proposed design choices requiring clinician/coordinator validation.
