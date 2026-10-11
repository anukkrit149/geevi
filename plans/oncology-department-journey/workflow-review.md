# Workflow review and complete fictional episode plan

This is the detailed planning-review memo. The integrated [implementation plan](implementation-plan.md) is the authoritative build sequence and demonstration script; it resolves small scenario variations in this memo, including which fictional patient carries the primary exception.

Date: 11 October 2026. Planning only. This memo owns no application changes, tests, fixtures, data imports or external actions. It reuses the prior [current prototype audit](/Users/anukkrit/Documents/ChatGPT/healthcare/research_oncologic_fit/findings_prototype.md) and the unchanged app snapshot. The new direct inspection was limited to the five existing PDF fixtures, their context generator and known schema/label code. No web research or repeated tests were performed.

## Decision proposed now

Build one connected **fictional AML department journey** around an institution-owned assessment/decision/follow-through protocol. It must demonstrate routine care, a patient-specific exception, actual-versus-reported events, follow-up and a reviewed evidence update. Do not put specific drug choices, doses, clinical thresholds or assumed assessment intervals into this plan. A clinical service must supply those rules and their authority before a later live pilot.

The first shared protocol should be a **care workflow template** with review points, required information categories, responsibilities, handoffs and exception handling. Keep its clinical content explicitly unvalidated in a synthetic demonstration. The patient plan should reference one template version and its approved patient-specific decisions. A department SOP, patient plan, medication order and actual delivery record are separate objects.

The key improvement over the current app is **reuse with accountable adaptation**: clinicians reuse department-approved knowledge, document how it applies to this patient, and request expert review where the patient's situation falls outside its approved scope. Senior clinicians govern evidence and complex decisions; their involvement is not removed from individual cases by the software.

## Named demonstration roles

All names below are invented identities for the demonstration, not actual clinicians or a proposed real sign-off policy. The service determines the live role/scope matrix.

| Fictional identity | Demonstration responsibility | Boundaries |
|---|---|---|
| Dr. Rao, treating oncologist | Owns Meera's and Arun's decisions, current clinical assessment, patient discussion and case impact review | Cannot claim another professional performed or signed care merely by recording a received report |
| Dr. Sen, department clinical lead | Owns protocol clinical scope, appraises disputed evidence, approves adoption and designated exceptions | Source approval does not authorize treatment for every patient |
| Dr. Iyer, diagnostic specialist | Reviews diagnostic/specimen/result ambiguity and the diagnostic section of the template | Does not become the author of an imported external laboratory report |
| Dr. Das, evidence reviewer | Reviews source methods, populations, outcomes, limitations and conflicting evidence | Evidence appraisal is distinct from institutional adoption and patient selection |
| K. Malik, pharmacy reviewer | Reviews medication-order interfaces and medicine-workflow responsibilities where relevant | No drug/dose content is invented; real prescribing/dispensing remains in the authoritative system |
| P. Shah, nursing/care-team lead | Reviews delivery/monitoring workflow, accepts owned handoffs and documents actual team work within role | A task acknowledgement is not administration confirmation |
| A. Roy, coordinator | Associates records, resolves administrative identity issues, manages documents/tasks/due dates and dependencies | Cannot turn candidate transcription into clinical interpretation or approve patient exceptions |
| Meera/Arun and an explicitly authorized supporter | Express goals, preferences and reported concerns; receive approved practical instructions | Supporter access and patient decision authority remain separately recorded |
| Department data/research steward | Owns permitted research reuse, data dictionary, cohort/extract approvals and missingness review when that later scope is enabled | A clinical chart's existence does not establish permission for all research uses |

A single person can hold more than one role only if the institution's configured policy permits it. Role occupancy and approval authority must be recorded at the event time. A configurable independence requirement must not be satisfied by one person switching UI roles.

## The complete demonstration journey

Relative event order below is a script, not a clinical schedule. Dates and deadlines in fixtures should be realistic and internally consistent, but no interval is a recommended treatment or follow-up interval. Every clinical fact and paper used for the synthetic demo remains visibly synthetic; actual clinical adoption is outside this plan.

| Step | What happens and who acts | Resulting object/state and visible proof |
|---|---|---|
| 1. Define the department question | Dr. Sen asks how the department will prepare and review a newly referred AML case, make a patient-specific plan, receive feedback and handle uncertainty. A. Roy assigns evidence/review work. | `ResearchQuestion RQ-001`; population/setting and unresolved questions; requester, owner, due date; no patient selected by default |
| 2. Prepare the source bundle | Dr. Das adds source versions and their provenance; extracts candidate passages and records evidence methods/limitations. A conflicting or limited source is deliberately included. | `EvidenceItem` versions; exact passages; extraction review distinct from appraisal; duplicate/version/retraction status explicit |
| 3. Obtain named reviews | Dr. Das submits appraisal, Dr. Iyer reviews diagnostic scope, P. Shah reviews care handoff, K. Malik reviews the ordering interface. Dr. Sen resolves a recorded disagreement or requests a revision. | Separate review assignments and decisions; outstanding required review visibly blocks adoption; nothing is approved because a reviewer was merely invited |
| 4. Adopt shared protocol v1 | Dr. Sen approves the exact reviewed template version for the defined synthetic demonstration scope. It contains workflow nodes, required information/review points, owners, dependencies and exception rules. | `ProtocolTemplate AML-WORKFLOW v1`, explicit effective status, approval packet, review date/trigger, source versions, required role matrix; no patient-specific approval yet |
| 5. Open Meera's episode | A. Roy creates an episode, reconciles fictional identifiers and imports a multi-document pack. One molecular report is pending; one file is a duplicate; one wrong-patient attachment is caught before association. | `Patient` and `Episode`; document registry, provisional association/quarantine, missing dependency task; the worklist shows next owner and due time |
| 6. Prepare and assess Meera's profile | An authorized reviewer checks extraction against original sources; Dr. Rao interprets the current clinical picture. Patient priorities/access are collected in a separately attributed discussion note. | Verified **reported results** and a separate clinician assessment; six-dimensional summary points back to each source; missing results remain pending rather than normal |
| 7. Apply v1 to Meera | Dr. Rao reviews the template's applicability to the verified episode, patient goals and current assessment. The workflow branch requiring a pending result remains unresolved, while preparatory tasks can proceed within configured scope. | `ApplicabilityReview AR-M1` and `PatientPlan PP-M1`; explicit review scope, unresolved items, decision and owned next steps; no forced rereading of unchanged source papers |
| 8. Open Arun and request an exception | Arun's separate pack includes a documented access/preference issue and unresolved clinical assessment. Dr. Rao proposes a **workflow exception** to the standard review arrangement, such as an alternative review modality. If clinical timing or scope changes, it is flagged for the configured clinical reviewer. No regimen choice is implied. | `Exception EX-A1` references the exact template node, reason, relevant patient facts/preferences, proposed deviation, boundaries, expiry/review trigger and required reviewers; patient plan remains a draft until required approval |
| 9. Review the exception | Dr. Sen approves, declines or requests changes with reasoning; P. Shah confirms operational feasibility where required. Dr. Rao discusses and records the agreed patient plan. | Approved exception becomes an explicit part of `PP-A1`; declined exception does not alter the template; the department protocol remains v1 |
| 10. Handoff patient work | Dr. Rao approves a version-bound packet; A. Roy assigns preparation and coordination tasks; P. Shah accepts or returns the packet with a specific unresolved issue. Resolved receipt is then recorded. | Distinct `Task`, `Handoff`, `Acknowledgement`; assigned, accepted, blocked and completed states; original author versus transcriber attribution; version shown at every handoff |
| 11. Record actual care and feedback | The care team records what actually happened in the authoritative care system. The prototype receives either a cited authoritative record or a clearly attributed team report. One event is reported partly completed or deferred, one outcome is not assessed, and one symptom is patient-reported. | `PlannedEvent` and `CareEvent/ReportedObservation` remain separate; plan/order reference, actual time and provenance; an unverified report is not relabelled administration; pending clinician-review task |
| 12. Review and follow up | Dr. Rao assesses response/tolerability information and uncertainty. Meera demonstrates a justified continue-unchanged decision; Arun demonstrates further assessment or a proposed case change. Follow-up has an owner, due time, dependencies and a completion/closure criterion. | `EncounterDecision` and optionally next patient plan version; scoped review; patient-friendly approved next-step explanation; no-change is first-class; clinically significant delay routes to reassessment |
| 13. Evidence changes | A new source/addendum or reviewed external update raises `RQ-002`. Reviewers identify the precise workflow implication and revise the relevant template node. v2 is approved with an effective policy; v1 remains retained. | `EvidenceUpdate`, named appraisals, `ProtocolTemplate v2`, adoption reason, predecessor link and machine-readable changed scope; source addition alone does not change patient plans |
| 14. Review existing-case impact | The system finds candidate affected cases by v1/node/fact dependencies; Dr. Rao confirms impact. Meera may continue v1 with documented no-change rationale; Arun may move to a new plan referencing v2 after clinical review. An unrelated operational task change creates no new evidence-review requirement. | One `ImpactReview` per affected case; review owner/deadline, change/continue/not-applicable/unresolved disposition; old approvals and historical events retain the versions used at the time |
| 15. Close the episode and seed research | The team confirms follow-up disposition, remaining responsibilities and data completeness. A repeated observation can become a research question. If a later research scope is approved, a steward creates a specified cohort extract with endpoint definitions and missingness. | Episode closed/transferred/follow-up status with unresolved work assigned; research proposal separate from clinical care; no inferred efficacy claim or automatic protocol change |

The script should show the department protocol library, worklist, patient evidence/changes, decision/exception, team inbox, care feedback, follow-up and evidence-impact review as one connected navigation story. It must not require a clinician to start in a paper-upload wizard for every routine visit.

## Object model and lifecycle decisions

| Object | Required lifecycle | Non-interchangeable concepts |
|---|---|---|
| Source document | received → identity/episode association pending → associated or quarantined → available; source may be preliminary/final/corrected/amended as declared by issuer | Imported/available is not source-authenticated, extraction-verified or clinically interpreted; issuer status is separate from review status |
| Result assertion | candidate → source-verified or rejected; corrected transcription adds a version; amended laboratory result supersedes by explicit relation | Patient-level summary is a projection, not the authoritative result; same marker on another specimen/date is a different observation |
| Clinical assessment | draft → clinician reviewed/signed for scope → amended/superseded | Interpretation of reports is separate from quoted findings; a new assessment does not overwrite source text |
| Research question | proposed → accepted/assigned → investigating → answer submitted → reviewed/closed; reopened on defined new evidence | Closed question may still conclude insufficient evidence; closed is not a protocol adoption |
| Evidence item/version | received → extraction reviewed → appraised; separate adopted-use statuses and superseded/retracted/withdrawn flags | Extraction quality, study quality, patient applicability and institutional adoption each have their own disposition |
| Review assignment | requested → accepted → in progress → submitted → resolved/changes requested/withdrawn | Request, completion and approval are different; required reviewers and exact version/scope are retained |
| Protocol template version | draft → review → changes requested or approved → scheduled/active → superseded/retired/withdrawn | Approval and activation may differ; existing patient plans are not rewritten on activation; urgent withdrawal triggers service-defined impact review |
| Patient applicability | draft → scoped review signed → relevant changes require reassessment | It can reuse current department evidence review; it is not trial eligibility or authorization to administer |
| Patient plan version | draft → required review complete → approved → effective → superseded/cancelled | Draft leaves current effective plan intact; approved text is not a medication order, scheduling event or administration record |
| Patient exception | proposed → reviewers assigned → approved/declined/changes requested → incorporated into plan → reviewed/expired/closed | A patient's exception does not revise the shared template; a lapsed exception requires review, not an autonomous treatment directive |
| Team task | assigned → accepted → in progress → blocked/completed; completion verified/closed if that task type requires it; cancelled with reason | Completed requires its defined evidence; acceptance and completion are distinct; reassignment retains history |
| Handoff | prepared → sent through configured channel → delivered if verifiable → acknowledged/returned → resolved | UI click is not verified delivery; acknowledgement is not task completion or administration |
| Planned care event | proposed → scheduled → rescheduled/cancelled/linked to actual event | Scheduling does not assert performance |
| Actual care/feedback | received as authoritative record or attributed report → reconciled as appropriate → clinically reviewed | Distinguish delivered/not delivered/partial/unconfirmed, professional assessment and patient-reported concern; unknown outcome stays unknown |
| Impact review | candidate affected → assigned → reviewed → change/no change/not applicable/more information → resolved | Automated dependency matching nominates a case; accountable clinical review decides the effect |

Every durable transition records object ID/version, actor identity and role, timestamp, reason/scope, source versions and previous state. Required review policy is versioned too. Correcting a mistaken event appends a correction; it does not erase the original event.

## Dependency scope and invalidation

Replace the single broad patient-revision gate with an explicit review dependency set. A signed decision records the exact result/assessment/patient-goal versions used, template version/node, evidence approval versions where relevant, reviewer policy version and unresolved conditions. The UI separately records ordinary worklist/task changes. New data is classified by defined policy and a responsible reviewer; the classifier must not silently decide clinical irrelevance.

| Change | Expected system response | What must not happen |
|---|---|---|
| Task assignee, receipt acknowledgement, administrative note | Refresh task/handoff state and audit; keep clinical review current unless the task changes a clinical dependency | Requiring a full research applicability signature because a coordinator accepted work |
| Appointment/logistics change within an approved operational scope | Update the task/event and notify the owner as configured | Assume every timing change is harmless; a delay beyond the service's defined scope must create clinical reassessment |
| New unrelated source or corrected typography | Retain source/version; classify relationship to current decision; no automatic global invalidation | Silently overwriting historical source or declaring unrelatedness without the configured review |
| Newly received pending result used by current decision | Add source-specific candidate; assign review for affected decision nodes | Automatically mark candidate normal, confirm eligibility or apply a revised plan |
| Corrected/amended result, changed specimen association or identity | Quarantine/reconcile association; make affected facts and decisions visibly require review; preserve prior snapshots | Reusing a signature as if it covered the amended value or silently removing old evidence |
| New specimen with same marker | Create separate observation with its specimen/time/method, compare in context | Label as a transcription correction or choose newest value solely by date |
| New patient symptom, response or tolerability report | Create attributed observation and clinical-review task with institution-defined urgency; separate review status from current order authority | Turn a patient report into a graded clinical finding or allow stale software state to dictate care |
| Patient goal/access change | Determine whether the current decision's goals, feasibility or consent discussion are affected; route scoped review | Treat preferences as merely administrative, or as automatic therapy selection |
| New literature source | Enter evidence queue; assess credibility, relevance and impact; current template stays effective until an authorized decision | Automatically reapprove/rewrite a protocol because a paper is newer |
| Evidence retraction/correction affecting a used source | Flag source, enumerate dependent templates/plans, assign priority impact review under service policy | Treat the entire system as invalid or autonomously cancel patient care |
| New template v2 | Identify candidate affected cases by scope/node/version; individual review outcome determines plan changes | Upgrade all patient plans in bulk or rewrite historical events |
| Routine continuation within current template and unchanged relevant clinical basis | Record encounter assessment and continuation scope without duplicating unchanged evidence appraisal | Force research recertification for every visit or imply no assessment is needed |
| Patient-specific exception | Invoke exception policy and named required review, then bind to patient plan version | Require a new paper for every justified exception or let exceptions bypass all clinical authority |

An affected review status is **“review needed for this decision scope”**, not “treatment must stop.” Urgent clinical decisions follow the service's explicit exception/escalation policy and remain attributed; software must not hide record entry because retrospective evidence review is incomplete. A historical care event may be recorded against the version actually referenced even if that version is now superseded or flagged.

## Cannot-bypass invariants

1. No cross-patient or cross-episode association through reused display names, fixture IDs or browser-selected patient state. Ambiguous identity is quarantined until resolved.
2. No extracted candidate becomes a verified fact or interpreted diagnosis without the designated review and original supporting source. Machine output stays attributable and correctable.
3. Source transcription, clinical diagnosis/interpretation, study appraisal, institutional adoption, patient decision, consent/permission, order and administration remain distinct records.
4. Missing, pending, not tested, not detected, not reported, specimen inadequate and indeterminate are not interchangeable; language and result availability are retained.
5. A report-level specimen/method/date is not copied onto every result unless source structure actually supports that relationship.
6. Required review assignment completion and exact approved version are checked on the server in a future production system; UI hiding alone is insufficient. A simulated role/signature never migrates into a real credentialed approval.
7. Saving a draft, submitting research or proposing a template revision never changes an effective patient plan. Approval binds an exact version with no unseen attachments or future edits.
8. An amended source/decision preserves what was known at each historical approval. No retroactive “current” reconstruction of prior facts.
9. A shared template cannot replace case-specific applicability and exception reasoning. One patient's outcome/exception cannot automatically change the shared protocol.
10. Acknowledgement, execution and clinical assessment each have their own author/time/source. Transcribing a received message never manufactures the sender's digital signature.
11. No planned session becomes actual delivery by default. A reported event is labelled reported until reconciled to the required authority.
12. Patient-facing instructions come from the approved patient scope, not draft research or unreviewed extracted facts. A concern-submission feature requires a defined recipient and service response process.
13. Restore/import preserves provenance and labels incomplete evidence; absent original bytes cannot be silently reconstructed or treated as source-inspected.
14. Research cohort membership and data reuse obey a separately defined purpose and authority; operational care access is not unrestricted research permission.
15. Source verification/workflow tests do not establish clinical accuracy, medical benefit or safety. Each intended use needs separately defined acceptance criteria.

## Audit of current synthetic document assumptions

Direct PDF text extraction inspected [Meera intake](/Users/anukkrit/Documents/ChatGPT/healthcare/product/fixtures/meera-intake.pdf), [Arun intake](/Users/anukkrit/Documents/ChatGPT/healthcare/product/fixtures/arun-intake.pdf), both profile-context PDFs and [synthetic research](/Users/anukkrit/Documents/ChatGPT/healthcare/product/fixtures/synthetic-research.pdf). Existing artifacts remain unchanged.

| Current fixture/model | Specific problem for the next workflow | Planning consequence |
|---|---|---|
| Intake PDF page 1 combines reported AML diagnosis, one marrow specimen, generic “illustrative molecular panel”, NPM1, FLT3-ITD, TP53 and karyotype | It compresses separate laboratory disciplines and methods into one uniform labelled block. The molecular panel wording does not establish which assay produced each result or whether the karyotype is an independent report. | Split primary reports or model explicit component reports with their own lab/accession, specimen, method, status, dates, findings and author. An integrated clinical summary can still exist, but must cite those underlying reports. |
| Both cases use `BM-001` | The shared synthetic identifier has no issuer namespace and gives poor test coverage. Reused local numbers across different real issuers are not automatically errors. | Use a unique internal specimen ID and retain external aliases as `issuing organization + identifier system + value`; accession identifiers need the same scoping. Never join by specimen display text alone. |
| Intake PDF page 2 contains prior treatment, performance status, LVEF absence and current fitness/condition | A clinical note is bundled as if part of a diagnostic report; author/encounter/effective assessment time are absent | Separate a treating-clinician assessment/history note and any independent organ-assessment report; a note saying LVEF unavailable is not an echocardiography result. |
| Context PDF mixes extent, functional and organ assessment, preferences and transport/cost | It is useful as an explicitly synthetic summary, but gives one source/date to different actors and observations; some content may duplicate/appear in tension with the intake summary | Separate clinic assessment and patient discussion/social-support notes, retaining the individual observation time, reporter and author; do not “resolve” by whichever was imported last. |
| One `Report date`, `Collected`, `Specimen`, `Method` stored as ordinary context facts | Current model is primarily `document → flat fact list`; it does not establish result-to-specimen/assay/collection/report-version relationships | Add structured observations and source-specific reference relations; six dimensions become a view over records, not the primary storage schema. |
| Markers are free text such as “Mutation detected”, “Not tested”, “Complex findings” | Missing analyte/variant identity, units and method/report-specific interpretation make automated comparison unsafe; not reported differs from assay-negative | Retain literal text and add only source-supported normalized fields with validation/provenance; never invent unreported variant detail or infer a negative panel. |
| “Karyotype: Report pending” in one case, “Complex findings” in the other | Pending final report and reported interpretation are not interchangeable structured chromosome findings | Create a pending test/work item first; on receipt add the actual report, its status and findings. Keep diagnostic classification to the clinician assessment. |
| Label parser matches `Label: value` lines | It succeeds on hand-authored fixture formatting, not necessarily realistic narratives, tables, footnotes, multi-column reports, scanned addenda or result panels | Design diversity and negative cases deliberately; evaluate unseen layouts separately. Preserve exact location and abstain when relation/reading order is unclear. |
| Synthetic paper has invented age/fitness inclusion criteria and fabricated remission counts without uncertainty/randomization/safety | Good workflow test of source limitations, but no evidentiary basis for a clinical protocol or personal prediction | Keep in the synthetic demo with unmistakable provenance; obtain clinician-selected licensed/authorized real references for an actual review workflow. Do not export its numbers as clinical evidence. |

Code evidence for these constraints: [label parser and flat facts](/Users/anukkrit/Documents/ChatGPT/healthcare/product/intake-model.js:6), [report attachment and identity](/Users/anukkrit/Documents/ChatGPT/healthcare/product/intake-model.js:13), [dimension source context projection](/Users/anukkrit/Documents/ChatGPT/healthcare/product/profile-dimensions.js:22), [context fixture generator](/Users/anukkrit/Documents/ChatGPT/healthcare/product/scripts/make-profile-fixtures.py:9). Page observations above came from actual fixture extraction, not a claim that every authentic AML report must have one universal format.

## Recommended multi-document episode pack

Create this only in a later implementation phase. It is a demonstration data plan, not an AML diagnostic checklist. A clinical partner chooses which documents/tests are appropriate for the actual scenario. Do not invent unavailable documents in a live case to make the pack look complete.

| Synthetic document/artifact | Provenance and relationships to demonstrate | Useful variant/edge case |
|---|---|---|
| Referral and episode registration | Referring author/service, referral reason, local/external identifiers, episode date, source attachments | Similar patient name; episode linked correctly; referral impression remains distinct from confirmed diagnosis |
| Initial clinic/history note | Encounter, author, effective date, reported symptoms/history/prior care, medicines/allergies when supplied, goals and planned investigations | Patient-reported history versus documented prior treatment; absent history is unknown |
| Serial laboratory reports | Ordering/reporting organization, accession, specimen type/collection time, analyte, value/unit/reference context, report status | Result table with units; repeated tests at different dates; amended value; no invented “normal” result |
| Marrow morphology/histopathology report | Specimen/accession, procedure/sample, collection/receipt/issue times, adequacy, methods, reported findings and signed interpretation as separate sections | Preliminary report then final/addendum; interpretation cites pending ancillary studies |
| Flow-cytometry report | Its own report/version/assay and linked specimen or aliquot, analyte/panel findings and issued interpretation | A different collection/aliquot; limited sample or indeterminate wording preserved |
| Cytogenetics report | Separate method/accession, specimen, result expression/interpretation, status, result/issue dates | Pending request becomes a final report; report amendment adds new information rather than silently editing old fact |
| Molecular assay report | Panel/assay/version, laboratory, specimen, source-supported variant/result, assay-specific limitations/coverage where actually present | Not detected within a named assay versus not tested or not reported; result from a later specimen |
| Functional/organ assessment note or report | Actual measurement/assessment author and date, source-supported value/method and clinician assessment | A missing report creates a task; lack of LVEF in a molecular report never counts as an organ assessment |
| Patient goals and practical support note | Reporter versus recorder, patient authorization, preferences, transport/cost/family participation, observation time | Preference later changes; routine transport update versus a clinically significant access delay |
| Multidisciplinary/clinical decision note | Decision participants, attendance versus approval, options/uncertainty, evidence/template version, patient discussion, intended next step | Unresolved disagreement or a patient-specific workflow exception requiring a named reviewer |
| Approved plan and order reference | Patient plan version, template and exception references, approving clinician, authoritative system/order ID | No medication values fabricated; plan remains distinct from actual order and administration |
| Care-team/administration/encounter source | Actual or reported event time, actor/source, performed/not performed/partial, linked order/plan, observations and deviations | Late report for older plan version; unconfirmed delivery stays unconfirmed |
| Follow-up and assessment note | Assessment due/done/not assessed, relevant results, symptoms/function, next decision and task | No-change decision; missing follow-up; transfer with an explicit receiving owner |
| Evidence update and template governance packet | Real or clearly synthetic publication identity/version, reviewed source passages, reviewer dispositions, protocol diff and adoption scope | Correction/retraction flag, conflicting paper, v2 affecting one case but not another |

Use one manifest per synthetic episode: patient/episode IDs; document IDs and hashes; versions and predecessor/addendum links; organizations/authors/roles; report dates and observation times; specimen and assay IDs; expected extracted assertions and their source locations; intended correct/unknown/conflicting states; clinical interpretations authored separately; expected review/impact relationships. Keep ground-truth annotations separate from input documents. Maintain a separate manifest for department evidence and governance so it can apply to both patients.

Minimum result relationship to model: `Patient → Episode → Order/request (when available) → Specimen/aliquot → Assay/performance → Result assertion → Source document/version/location`. A result can reference several supporting passages; a document can describe multiple specimens or assays. A clinician assessment references selected results plus history/goals, retains uncertainty, and is never stored as if it were a laboratory result. Support event/effective time, collection time, report issue time, source receipt time and review time independently.

Keep the following state axes separate rather than one “verified result” flag:

| Axis | Example states/fields | Meaning |
|---|---|---|
| Source/report lifecycle | preliminary, final, corrected, amended, cancelled, status not provided; issuer version/addendum identifier | What the issuing source says about its report, independent of this app's reviewer |
| Source availability | not received, received, original unavailable, unreadable, quarantined | Whether the supporting material is available and associated; no inference that a missing report means a test was never done |
| Test/performance status | planned/ordered, pending, completed, explicitly not performed, cancelled, unknown | Only source-supported information about whether an assay was performed; not reported is not not performed |
| Result content/status | numeric/text result; detected/not detected, indeterminate, insufficient/failed result where explicitly stated; not reported | What was actually reported, with units/limits/context where present; no invented negative finding |
| Specimen/assay adequacy | adequate, limited, inadequate, not stated, plus original wording | Technical qualifications tied to that specimen/assay; not a general judgment about the patient |
| Extraction/review lifecycle | candidate, source inspected, source-verified, corrected transcription, excluded; reviewer/reason/version | This app's treatment of a proposed transcription; it cannot change the issuer's final/preliminary status |
| Clinical interpretation | unassessed, assessed with uncertainty, signed for scope, reassessment needed | A clinician's separate interpretation and decision applicability, never implied by source verification |

Use a unique internal specimen/assay/report ID plus preserved issuer-scoped external identifiers and aliases. Do not collapse collection event, specimen, aliquot, assay and result into a single “sample” string. Unknown source relationships remain unknown and carry the review task needed to resolve them.

Authentic public/de-identified examples and synthetic episode packs remain separate provenance classes. Use authorized real examples to understand layout and test extraction in their genuine context. Do not paste reports from unrelated actual patients or datasets into one synthetic patient journey or imply a fabricated cross-dataset linkage. If an authorized format is used to create a synthetic template, replace content coherently, label it synthetic, and record which structural reference informed it; the source format is not evidence for the fictional patient's findings.

## Restore and migration plan

1. Take an explicit export of current fictional state and original PDF/image bytes before any later schema migration. Current JSON review export does not bundle original bytes; localStorage and IndexedDB must be accounted for separately.
2. Introduce stable IDs and a schema version for patients, episodes, documents, specimens, assertions, templates and approvals. Current short IDs (`D1`, `F1`, two fixed case names) are local identities, not globally safe keys. Reset/reimport must not accidentally reconnect an old review to a different object with the same ID.
3. Preserve the older `patient-evidence-review` demo as a separate legacy artifact. Do not merge its synthetic matched values, roles or approval history into the newer case store by matching patient display names.
4. Import existing current-app facts as legacy source-linked assertions with relationship fields explicitly unknown. Do not infer specimen/assay relations merely from the nearest `Specimen` or `Method` label. Route required relation review when later functionality depends on it.
5. Preserve historical snapshots exactly, tagged as imported simulated reviews. Do not upgrade demo `Dr. Rao` strings into real user signatures, and do not claim unavailable historic snapshots have been reconstructed.
6. Recover documents by content hash, retain original versions and duplicate references, and display missing-original status. Never fabricate a replaced file or silently claim original inspection after an unavailable source restore.
7. Dry-run migration with a report of counts, broken references, duplicate/colliding IDs, unresolved relationships and semantic changes. A migration must be idempotent, atomic at the chosen boundary and roll back without losing original state.
8. After restoration, clinical review dependencies are recomputed from explicit relationships without mutating old approvals. Unresolvable dependencies remain labelled review-needed. Existing source version and author history remain inspectable.
9. Later production migration additionally requires institution-approved identities, authorization and retention mapping, transactional concurrency handling and authoritative-system reconciliation. This memo does not authorize transferring real records.

## Acceptance scenarios for later implementation

| ID | Demonstration scenario | Pass condition |
|---|---|---|
| W01 | Required pharmacy/nursing/diagnostic review still requested | Template adoption remains pending with the missing reviewer visible; an invitation cannot count as submitted review |
| W02 | One reviewer asks for changes | New template draft/version is reviewed; approval of the old content cannot cover the changed scope |
| W03 | v1 becomes active | New patient plan can select it; no patient plan appears approved automatically |
| W04 | Wrong-patient or ambiguous specimen report | Association is quarantined; facts cannot enter the target verified profile; original and resolution history remain available |
| W05 | Same analyte on two specimens/dates | Two distinct observations survive; profile comparison shows context and does not overwrite one |
| W06 | Negative versus not tested versus pending | All remain semantically distinct through extraction, review, summary, export and reload |
| W07 | Preliminary then amended final report | Versions and changed assertions are retained; only dependent reviews are flagged |
| W08 | Candidate with unsupported variant/assay relation | Reviewer sees unknown relation; no eligibility logic consumes an invented normalization |
| W09 | Operational task accepted/reassigned | Task history updates; unrelated clinical/evidence approval remains current |
| W10 | Scheduling change crosses a configured clinical boundary | Clinical reassessment task is created with reason/owner; routine reschedule is not automatically treated as a new research question |
| W11 | Patient-specific exception approved | Plan references exact exception/template version; shared protocol remains unchanged; another patient cannot inherit it |
| W12 | Exception rejected or lapses | Current plan is not silently replaced; responsible clinician receives the configured review need |
| W13 | Draft plan edited while another reviewer has it open | Approval rejects stale content and shows the current draft; no lost update or unauthorized overwrite |
| W14 | Handoff sent but unacknowledged | Delivery/receipt/acceptance remain visibly different; owner and escalation policy are clear |
| W15 | Oncologist transcribes a care-team acknowledgement | Reported sender and actual recorder both appear; no counterfeit team signature is created |
| W16 | Scheduled event has no administration confirmation | Record remains planned/unconfirmed; clinical summary does not claim delivered treatment |
| W17 | Patient reports symptoms; professional assessment pending | Source attribution and clinical review status remain distinct; configured responsible recipient receives work |
| W18 | Continue-unchanged after reviewed feedback | Encounter and next action are recorded without recreating unchanged source appraisal or changing the plan text/version unnecessarily |
| W19 | Historical event arrives after v2 adoption | Event links to the plan/order actually referenced, retains late-receipt time and remains recordable |
| W20 | Evidence source corrected or withdrawn | Dependent templates/cases are nominated for review; old versions survive; no silent bulk change to care |
| W21 | v2 has narrow scope | Impact queue includes candidate affected cases with reason; clinician can resolve no change/not applicable/change/more information |
| W22 | Missing follow-up or transferred care | Missing outcome is recorded as missing; receiving owner or unresolved handoff remains visible; no fabricated treatment success |
| W23 | Restore lacks source bytes or has repeated `D1/F1` IDs | Import reports incomplete source/collisions and requires resolution; no false current signature |
| W24 | Simulated approval is migrated | It remains a demo/historical imported event, never a production clinician authorization |
| W25 | A research analyst requests identifiable cohort data | Approved scope/purpose/role and extract rules determine access; care UI permission alone is insufficient |
| W26 | A new fixture layout/table is not parsed reliably | The system abstains or exposes uncertainty/source for review; document absence is not inferred as a negative finding |

Acceptance should cover state/model tests, API authorization/concurrency tests for a future backend, original-document rendering, and observed clinician/coordinator walkthroughs. This memo creates scenarios only; it does not implement or execute those tests.

## Decisions requiring the clinical partner

Before a real pilot, obtain named ownership of: the initial disease/service scope; required case inputs for each decision; what preparation staff may source-verify; specialty review and approval scopes; when review independent of the proposer is required; what constitutes material clinical change; urgent exception authority; allowed scheduling/logistics changes; follow-up definitions and escalation staffing; authoritative order/administration systems; patient/supporter permissions; outcome definitions and research governance. These cannot be derived from the existing labelled fixtures or a vendor's product description.

Planning audit: 0 web queries; 5 PDF fixture texts inspected; 1 fixture generator inspected; prior source audit reused; no repeated test run; no application, test, source fixture or real record modifications. This document is a design proposal, not a validated clinical SOP.
