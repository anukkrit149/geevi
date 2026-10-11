# Complete oncology journey: implementation plan

Planning version 1 · 11 October 2026 · Status: proposed implementation specification; no application code changed.

This earlier plan is preserved as supporting context. The [consolidated implementation plan](../../docs/plans/2026-10-11-1137-feat-oncology-department-journey-plan.md) is now the implementation authority and supplies concrete units, files, command guards and verification. Use its [coding-agent handoff](../../docs/plans/oncology-coding-agent-handoff.md) for execution.

## Outcome and scope

Extend the existing Casebook prototype into one connected, reviewable journey: a fictional patient enters the service; separately sourced reports build a longitudinal profile; the treating clinician applies a published departmental protocol; an exception receives the appropriate review; the care team accepts tasks; actual care and concerns are recorded; follow-up closes the loop; a research finding results in a governed protocol revision and targeted patient review.

Retain Meera as the main fictional AML patient and Arun as a second case that proves a shared protocol is reusable without copying decisions or approvals between patients. This is a continuity choice for the current prototype, not a conclusion that AML is the best first clinical or commercial market. No drug, dose, diagnostic eligibility threshold or treatment recommendation is invented in this plan. Clinical content and which facts may block a decision are authored and approved by the partner service.

The first implementation deliverable is a complete fictional demonstration with explicit simulated roles. A separately gated pilot milestone adds real authentication, shared persistence, institutional data handling and integration. Demo completion does not imply clinical deployment readiness.

The literature/research workflow covers evidence appraisal and protocol change. Cohort analysis and prospective study management are later capabilities, supported by the data model but outside the first journey. Medication prescribing, administration clearance, clinical AI triage and a full replacement hospital record system are outside the first deliverable.

Senior oncologists can lead research and protocol improvement with protected time, while designated clinicians remain responsible for individual care and exceptions. The staffing goal is to spread reviewed expertise; the product must not assume that following a template removes patient-specific clinical judgment or that the most experienced clinician can disengage from clinical governance.

## Product decisions made now

1. Keep the existing source viewer, attributed facts, original wording, six-dimensional profile and versioned snapshots.
2. Separate a departmental protocol from a patient plan, an operating procedure and a research-study protocol.
3. Use one linked workflow and stable identifiers across patient and research screens; retire ambiguous links to the separate legacy demo from the primary navigation.
4. Make source documents realistic and granular; the patient profile is a derived view, not the raw document schema.
5. A published protocol does not update an active patient plan automatically.
6. Routine care can reuse approved evidence and a published protocol. Fresh literature appraisal is not mandatory for every encounter or operational edit.
7. Approval, actual work and patient communication are separate events. A displayed task or scheduled session is not proof of completion or delivery.
8. Every unresolved dependency or alert has an accountable owner and a defined next action. A notification is not itself a response.
9. Preserve the current small application for the fictional demonstration. No framework rewrite is required to validate this workflow. Introduce explicit domain modules and storage boundaries so a shared backend can replace the local adapter later.

## The complete demonstration story

Dates below use relative day labels solely to show order. They do not recommend clinical timing.

| Step | Actor and action | Resulting record | What the demonstration proves |
|---|---|---|---|
| 1. Publish the starting pathway | Evidence lead attaches selected sources; reviewer appraises relevance/limitations; designated approvers publish service protocol v1 | Evidence versions, individual reviews, decision, effective protocol version | Evidence acceptance and protocol publication are separate approvals |
| 2. Register the episode | Coordinator opens Meera's referral and creates the service episode | Patient, episode, team ownership and next-review task | Patient identity is checked before attaching external files |
| 3. Receive independent documents | Coordinator imports referral, blood results, marrow report, flow report and molecular/cytogenetic reports as separate sources | Documents, report versions, specimens, candidate observations | Facts from different dates and specimens are not collapsed |
| 4. Prepare the case | Trained reviewer verifies source transcription; clinician reviews interpretation and missingness | Scoped profile review, resolved/unresolved observations and owned requests | Source verification does not itself establish diagnosis or plan approval |
| 5. Apply protocol v1 | Treating oncologist compares current patient facts/goals with pathway requirements | Applicability assessment bound to patient facts and protocol v1 | Matches, differences and unknowns remain distinguishable |
| 6. Request and resolve an exception | A fictional documented patient preference conflicts with a proposed operational arrangement; clinician requests an alternate arrangement and the designated owner reviews it | Typed exception, rationale, evidence/patient scope, decision and review date | Patient-specific deviation does not edit the shared protocol; clinical exceptions can require different approvers |
| 7. Approve the patient plan | Treating clinician reviews the final plan, patient discussion and current dependencies | Immutable patient plan v1 and discussion/consent reference where applicable | Approval covers an exact version and retains unresolved items explicitly |
| 8. Hand off work | Coordinator routes role-owned tasks; receiving staff accept or return them with reasons | Assignment, acknowledgement, due time, dependency and completion evidence | Sending and accepting work are distinct states |
| 9. Record actual care | Care team records what was done, partly done, deferred or not confirmed, and attaches source records | Care event linked to the plan/order reference used | Planned, ordered, reported and verified delivery remain distinct |
| 10. Review a concern | A fictional patient concern is received; assigned staff triage through the service process, document response and escalate if required | Concern, owner, response, escalation and clinical review | A report is not silently treated as a diagnosis or adverse-event grade |
| 11. Complete follow-up | New results and assessment arrive; clinician records a justified continue/no-change decision or a reviewed revision | Encounter review, next tasks, follow-up appointment status | Only affected clinical material needs renewed review; unchanged evidence is reused |
| 12. Improve the shared protocol | A new publication or recurring process question creates a research request; reviewers assess an amendment and publish v2 | Research request, evidence appraisal, change proposal, protocol v2 | New knowledge passes through designated review |
| 13. Review affected patients | Meera and Arun appear in an impact queue because their plans reference v1; clinician reviews each separately | Per-case disposition: stay on v1 with reason, adopt v2 through new plan, or seek more review | No automatic plan migration and no transfer of patient-specific approval |
| 14. Close the episode loop | All due actions have a completion, cancellation, transfer or explicit unresolved status; care continues through a named owner | Follow-up summary and reproducible audit packet | Closing a task cannot falsely declare the patient clinically discharged |

The main exception above is deliberately non-prescriptive. Also demonstrate a clinical exception request as pending designated clinical review, without inventing its medical resolution. A wrong-patient source and a material report amendment are negative branches, not additional patient journeys.

## Roles and responsibility

| Role | May do | Must not be able to do by default |
|---|---|---|
| Coordinator | Associate verified identity, collect reports, assign permitted tasks, schedule/track, record attributed external communication | Diagnose, reinterpret results, approve clinical exceptions or publish protocols |
| Source reviewer | Verify transcription within assigned scope, annotate ambiguity and reconcile extraction errors | Treat transcription approval as clinical interpretation |
| Treating oncologist | Interpret the case, assess applicability, record patient discussion, approve an individual plan, manage/escalate exceptions | Silently edit published departmental content or another actor's signed record |
| Evidence researcher | Create questions, retrieve sources, propose structured evidence appraisal and protocol changes | Publish a clinical pathway merely by approving an article for the library |
| Protocol lead and assigned reviewers | Review within named scope; approve/reject/request revisions; publish according to service policy | Approve on behalf of a missing required reviewer or override unresolved conflict by changing status alone |
| Care team member | Accept work, document their action/observation, return tasks, raise concerns | Change the patient plan or equate a scheduled action with actual care |
| Patient/caregiver, later pilot | View approved next steps and submit observations within authorized scope | See internal draft reasoning by default, sign clinician decisions or edit clinical findings |
| Administrator | Manage accounts, access and configuration | Gain clinical approval authority solely from administrative access |

An individual may hold several authorized roles, but each decision records the role and scope used. The demo review policy requires an independent clinical reviewer for pathway publication; additional discipline reviews are configurable and service-approved. Real authentication and institutional authority are required before those controls can be relied on clinically.

## Screens and primary actions

| Screen | Essential content and action | Acceptance signal |
|---|---|---|
| Today / team work | Decision due, missing input, owner, due time, latest change, overdue/returned work | Every row opens its exact case/task; urgency is attributed, not guessed |
| Patient decision summary | Current plan/version, protocol/version, goals, changes, blockers and next decision | Clinician can understand what needs attention before opening all sources |
| Documents and results | Document type/status/version, specimen, dates, source, atomic results, conflicts and original viewer | Finding opens the correct page/region and source version |
| Profile and timeline | Six dimensions derived from dated facts, encounters and assessments | A historical view shows what was known then, without later facts leaking in |
| Pathway applicability | Protocol scope, referenced requirements, patient facts, unknowns and deviations | No percentage score conceals an unresolved required criterion |
| Plan review and exceptions | Before/after plan, alternatives, exception disposition, patient discussion and current approvals | Unsaved/stale changes cannot be signed |
| Care and follow-up | Owned tasks, receipt, care events, concerns, responses and next review | Completion includes evidence; partial/deferred/unknown states remain visible |
| Research questions and evidence | Question, intended use, search/import sources, study details, limitations, assignments and decisions | Source appraisal is reusable without implying patient approval |
| Department protocol library | Published and previous versions, scope, required reviews, change proposal and effective date | Publishing v2 preserves v1 and creates a review queue |
| Protocol impact queue | Affected patient-plan references, review reason, owner, due date and disposition | One patient's resolution does not close another's task |
| History/export | Actor, action, timestamp, exact source/plan/protocol versions and superseding links | Reviewer can reconstruct a decision without relying on current mutable values |

## Domain and lifecycle rules

The data dictionary and report contracts are detailed in [report-and-data-specification.md](report-and-data-specification.md). The implementation must use stable internal IDs, explicit version IDs, authorized transitions and idempotent commands; screen navigation alone must not mutate records.

| Object | Lifecycle | Essential guard |
|---|---|---|
| Source document/report | Received → identity reviewed → processed; source status independently preliminary/final/amended/corrected/withdrawn | Source-issued status is never inferred from local review completion |
| Extracted fact | Candidate → verified/corrected/rejected; may be unresolved/conflicted | Preserve source wording and a reason for correction; do not overwrite history |
| Evidence appraisal | Draft → assigned → in review → changes requested/resolved → accepted or rejected; later superseded/withdrawn | Each required reviewer signs their scope against an evidence version |
| Department protocol | Draft → in review → approved → published/effective → superseded/withdrawn | Required reviews resolved; scoped content/version frozen; publication authority checked |
| Patient plan | Draft → review requested → approved → active/held/completed/superseded according to clinician disposition | Current necessary facts, protocol reference and exception decisions; treatment status only changed by authorized clinical action |
| Exception | Proposed → awaiting review → approved/rejected/needs information → resolved/expired | Type, patient/protocol scope, approver, reason and expiry/review trigger required |
| Task | Assigned → accepted → in progress → completed; alternatives returned/blocked/cancelled | Owner and result evidence; blocked or cancelled is not completed |
| Care event | Planned → documented as performed/partial/deferred/not performed/unknown; source verification separate | Actual event records actual time/source and the plan/order version used |
| Follow-up/concern | Received → acknowledged → assessed/routed → action taken → reviewed/closed | Named responsible service and visible unresolved/escalation state |
| Impact review | Open → assigned → reviewed → disposition recorded | Exact changed evidence/protocol and affected patient reference; no automatic plan rewrite |

Approval timestamps, effective dates and clinical-event dates are different fields. A protocol can be approved but not yet effective. Superseding is not deletion. Withdrawal opens clinical review/escalation according to policy and does not itself issue an instruction to stop therapy.

## Review dependencies and exceptions

Replace the current single broad case revision check with explicit dependency scopes. Every review records the relevant patient observations, source versions, evidence versions, protocol version and decision scope. A dependency index finds affected reviews when something changes. Show why a review needs attention.

| Change | Required behavior |
|---|---|
| Task reassigned or administrative due date changed | Update task audit and notifications; do not invalidate unrelated clinical/evidence approval |
| Source transcription corrected | Preserve old value; recompute affected profile views; flag only decisions dependent on that fact |
| New result from a new specimen/timepoint | Add longitudinal observation; do not label it an error solely because it differs |
| Lab issues amendment to the same report | Link source versions; retain the original; generate targeted impact review |
| New clinical assessment or patient preference | Clinician determines plan impact; patient-specific review may be needed, unchanged paper appraisal is reused |
| Routine follow-up with no material change | Record scoped continuation and next actions; do not demand a new paper review |
| Published evidence/protocol update | Reopen affected applicability/impact review where relevant; preserve active plan until authorized disposition |
| Identity mismatch, corrupted original, or authorization failure | Block the affected association/write; create a resolvable error with no cross-patient leakage |

Not every discrepancy is an exception. Distinguish a missing fact, an operational barrier, a patient preference, a clinical deviation and a research-study deviation. The first demo must show each category with its appropriate owner. Whether a clinical requirement is waivable is authored in the approved pathway; the software must not invent a waiver policy. Emergency care follows the institution's process independently of research queues.

## Technical implementation boundaries

For the fictional demonstration, retain existing browser routes and source-view components, with a shared versioned local store and export/migration support. Move logic out of views into explicit services: documents/results, evidence reviews, department protocols, applicability/patient plans, exceptions, tasks/care/follow-up and audit. Use a common store adapter so later server persistence does not change domain rules.

For a service pilot, use a modular application backend with a relational database, controlled original-document storage, a durable job queue, authenticated roles and append-only decision/event history. Adopt transactional version checks for approvals and an outbox/idempotency pattern for integration deliveries. Model-generated output enters as a draft; approval state transitions are application logic, not model decisions. This is a proposed architecture; exact hosting/vendor choices depend on the hospital and are not needed to prove the fictional workflow.

Agree system ownership before integration: the app may own its evidence/protocol reviews and local decisions; the hospital system remains authoritative for patient identity, signed orders, administration and clinical feeds unless an explicit integration contract changes that. Imported events retain upstream IDs and freshness. Failed write-back stays pending and visible; it must not appear delivered. Standards mapping is described in the data specification and is not a claim of current conformance.

## Migration and preservation

### Implementation map for the existing app

Names of proposed new modules below are planning suggestions; none was created in this task. Keep existing public routes working while moving responsibilities behind stable interfaces.

| Existing area | Planned change | New responsibility to isolate |
|---|---|---|
| `pdf-reader.js`, `pdf-workspace.js`, `pdf-evidence.js` | Retain original display, source geometry and provenance; label keyword extraction limits; add report/specimen-aware candidate associations | Document/report ingestion and extraction adapters, independent of clinical approval |
| `intake-model.js` | Evolve flat facts into versioned observations and explicit source/specimen/assay relations; replace broad revision invalidation | Document/result model, review-dependency service and shared store adapter |
| `profile-dimensions.js`, `dimension-view.js` | Render the same six dimensions from structured timed records; keep current and historical projections separate | Profile projection and change classification |
| `research-lab.js` | Separate evidence state from views; add reviewer assignments, disagreement, appraisal and change proposals | Evidence-review model and protocol-change proposal model |
| New departmental protocol area | Add shared library, reviewer policy, versioned publication and impact queue | `department-protocol-model` and corresponding views; distinct from patient plan |
| `protocol-model.js`, `protocol-view.js` | Continue patient-specific plan responsibility; reference shared protocol versions, scoped applicability and exceptions | Patient-plan and exception services; no automatic paper-review requirement for every edit |
| `session-model.js`, `session-view.js` | Preserve attribution and historical plan references; separate planned care, actual events, concerns and follow-up | Task/handoff, care-event and follow-up models |
| `intake-app.js`, main HTML and navigation | Show decision summary, role-owned work and links into the common store; remove ambiguity around the older demo | Lightweight routing/view composition; keep domain state transitions out of click handlers |
| Fixtures and fixture generator | Replace bundled summaries with a manifested multi-document episode and varied source layouts | Separate input documents, gold annotations and expected workflow scenario |
| Existing tests and review guide | Update stale test setup to use lawful transitions; add meaningful new domain/integration/journey cases | Acceptance-matrix coverage and clear demo/pilot status |

The first implementation review should confirm module boundaries against the then-current code; this plan does not authorize deleting current history or merging incompatible legacy stores.

- Inventory current local stores and original-file stores; offer a versioned export before migration.
- Migrate Meera/Arun facts with provenance intact. Old free-text plans become legacy patient-plan records, not retroactively published departmental templates.
- Mark legacy decisions missing protocol/reviewer context as legacy/unmapped. Do not fabricate approvals or backfill signatures.
- Keep older snapshots read-only and preserve links to source hashes. Originals with missing bytes require explicit recovery, not a substituted file.
- Provide idempotent schema migration, rollback through preserved export, failure reporting and a test for interrupted migration.
- Reconcile the current guide and stale protocol-model test setup during implementation. Test failures must not be fixed by removing the protective approval gate.

## Work packages and exit gates

| Package | Work | Depends on | Done when |
|---|---|---|---|
| P0 Baseline and domain contract | Snapshot current demo; map terminology; freeze approved scope; agree role and review policy for fictional data | This plan | No unresolved terminology between shared protocol, individual plan, SOP and study |
| P1 Document/data realism | Implement source/specimen/report/result/version objects; curate realistic synthetic episode fixtures and gold annotations | P0, dataset inspection | Sources are separate; dates and specimen links are inspectable; contradictions/unknowns behave correctly |
| P2 Evidence and shared protocol | Named appraisals/reviews, proposal diff, publish/effective/supersede, evidence dependency links | P1 | One published protocol serves both fictional patients without sharing their decisions |
| P3 Individual application and exceptions | Applicability, individualized plan, patient discussion, scoped exception lifecycle and approval | P2 | Main journey can approve the exact plan; prohibited/stale routes fail visibly |
| P4 Team execution and follow-up | Role-specific demo views, owner/due dates, acceptance/return, event attribution, concerns and response | P3 | No open action disappears; actual care is independent of planned care |
| P5 Research change and impact | New evidence review, protocol v2, affected-case queue, per-patient adoption/stay/escalate | P4 | Versions remain reproducible; each case resolves independently |
| P6 Integrated review and validation | Negative branches, migration, error recovery, accessibility and clinical-workflow walkthrough | P1–P5 | Acceptance matrix passes and unresolved clinical/content assumptions are visible |
| P7 Institutional pilot foundation | Real accounts, shared backend, data permissions, authoritative integration, audit/backup/recovery | Demonstrated workflow plus institution/design partner | Institution-authorized pilot and agreed quality/workload measures; no demo claims passed off as validation |

P0–P6 define the requested complete fictional journey. P7 is a distinct deployment gate. Build one vertical path through the packages, then add negative/exception branches; do not build disconnected modules with no demonstrable patient journey.

## Verification and clinical-workflow validation

Use [acceptance-matrix.md](acceptance-matrix.md) as the implementation checklist. Evaluate state transitions and invariants through meaningful model/integration tests, then role-based browser journeys using explicitly fictional fixtures. Verify reload/persistence, export/reimport, stale concurrent edits, blocked actions, source amendments and recovery from unavailable originals. Do not use these software checks as evidence of clinical extraction accuracy.

For extraction, separately evaluate a held-out authorized corpus with independent reference annotation: patient/specimen association, value/unit/negation, dates/status, source support, clinically relevant omissions, conflicts and errors remaining after review. Split by patient and source institution/layout where feasible to reduce leakage. Synthetic records test coverage and control logic, not clinical accuracy.

For workflow discovery, compare total staff time, duplicate entry, missed/late handoffs, review burden and residual information errors against the current service. The service defines acceptable clinical criteria and staffing response times before a real pilot. No percentage benefit or timeline is assumed in this plan.

## Decisions requiring the service before real use

The software structure is specified; clinical policy is deliberately not guessed. Before clinical deployment, name the responsible service and pathway owner, clinical eligibility/monitoring content, non-waivable requirements, required reviewers, exception and urgent-response authority, authoritative systems, legal/ethical data-use basis, research purpose and acceptance thresholds. These are not blockers to building a fictional demonstration, but they are blockers to claiming an approved clinical workflow.

## Plan artifacts

- [Report and data specification](report-and-data-specification.md)
- [Acceptance matrix](acceptance-matrix.md)
- [Workflow audit and detailed review](workflow-review.md)
- [Dataset and source recommendation](../../research_oncology_datasets/dataset-guide.md)
- [Prior product/clinical research](../../research_oncologic_fit/research_report.md)

No code, fixtures, database schema or application configuration was implemented in this planning task.
