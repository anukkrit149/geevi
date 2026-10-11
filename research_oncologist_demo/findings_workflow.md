# Clinician-led Geevi demonstration: workflow audit

Reviewed 2026-10-11. Read-only source review against the department journey plan. These are product and workflow findings, not clinical validation and not treatment recommendations. No tests were run for this audit.

## What the current software can usefully demonstrate

Geevi already separates a received report, a verified observation, a clinician interpretation, an evidence appraisal, a departmental publication, and an individual patient decision. Its backend preserves exact versions and independent review. That is a useful foundation for demonstrating case preparation, a departmental evidence review meeting, owned handoffs, and follow-up coordination.

It does **not** presently demonstrate clinical research discovery, prospective study management, cohort analysis, validated treatment selection, or a complete treatment administration record. The demonstration should describe research as **finding and critically reviewing published evidence to inform a local protocol**, with prospective research as a later capability. The product should not imply a senior doctor's judgement automatically substitutes for each treating clinician's responsibility.

## Eight gaps to fix before an oncologist demonstration

### 1. P1 — Replace fabricated research notes and preserve honest source classification

**Clinician action:** Read the evidence that supports the department's proposed preparation workflow and decide whether it justifies a local change.

The demonstration currently uses `research-preparation-audit.pdf` and `research-caregiver-contact.pdf`, both synthetic invented audits. Their claims, populations and appraisals are fabricated in `apps/api/app/demo_data/scenario.json` under `research`. The packaged manifest declares the notes at `apps/api/app/demo_data/manifest.json:327` and `:337`. Worse, `ResearchHome.addSource`, `apps/web/src/features/research/ResearchHome.tsx:33`, always sends `source_label: "synthetic"`, even though `SourceCreate` permits `public_reference` in `apps/api/app/schemas/research.py:24`.

**Fix:** Use attributable, openly available primary research or official evidence documents with URL/DOI, publication date, document type, licence/access status, retrieval date and exact source provenance. Make the label selectable or use an explicit public-reference import. Keep fictional patient charts separate from the real evidence library. Replace the scenario's invented appraisal claims with a transparent reading exercise: clinician-authored draft interpretation, appropriate study design (including guideline/consensus when applicable), actual limitations, no invented effect sizes. A curated reading brief must identify itself as a brief rather than an original article.

**Tests:** Manifest/hash and packaged-copy parity in `apps/api/tests/test_fixtures.py`; `test_research.py` for a public reference round trip; component/e2e check that a newly imported reference remains `public_reference`; update `helpers.py` and the full journey test's hard-coded fictional audit assumptions.

### 2. P1 — Reviewers cannot inspect the complete evidence or appraisal

**Clinician action:** Dr Sen independently verifies the author’s interpretation against the original paper before approving it.

The entire evidence library is nested inside `can("evidence.author")` at `ResearchHome.tsx:52–70`. A reviewer or read-only clinician can read question pages but is denied the visible library. The backend already exposes authenticated original evidence bytes via `source_content`, `apps/api/app/api/routes/research.py:70`, but the library/appraisal screens have no original-document viewer or download/open-source link. The submitted/accepted appraisal display in `QuestionDetail.tsx:124–126` shows findings, study design, limitations and unattributed passage text, while omitting population, intervention, comparator, outcome, timepoint and uncertainty—even though `FIELDS` at `:14` gathers all nine fields.

**Fix:** Give every workspace reader an evidence library and source detail/viewer; restrict only mutation controls to authors. Show the complete structured appraisal to reviewers, with citation title, source version, page/region and original-document navigation. Display publication/date/provenance for paper context. Independent approval should follow reading the packet, not merely seeing a digest.

**Tests:** Sign in as Sen, open original PDF and full PICO/context; verify no authoring controls; cross-workspace and signed-out original-file requests stay denied. Extend `research-review.spec.ts`.

### 3. P1 — Research has no discoverability or case-origin loop

**Clinician action:** From Meera’s unresolved molecular workup, ask a focused question, search literature, save relevant documents and see whether the department has already reviewed them.

`ResearchHome` currently lists every question/source and provides blank free-text forms; there is no text search, topic/status/source-type filter, or literature-search handoff. `AppraisalEditor` renders every extracted line as a checkbox in `QuestionDetail.tsx:67–80`; a full article will create hundreds of selections. `QuestionCreate.origin` in `apps/api/app/schemas/research.py:19` and `research.create_question` already preserve origin data, but `ProfileTimeline` and `ResearchHome.createQuestion` never expose a patient-to-question action or send an origin.

**Fix:** Support library keyword search over title/citation/passages, question/status filters, and passage search within a selected document. Add "Open research question from this case" preserving a patient link and a clinician-written question, without converting that question into a recommendation. Offer a clear link to an official literature search (e.g. PubMed/ClinicalTrials.gov); describe remote search as external discovery, not a completed search/import. Useful demo search terms are disease classification, diagnostic workup, molecular testing, management pathway, outcomes and the individual patient's stated uncertainty. Choose specific queries with the clinician, not an automatic therapy recommendation.

**Tests:** Search real-document passages; no-match state; follow case-origin link back; imported evidence alone creates no protocol or patient recommendation; scope stays within the workspace.

### 4. P1 — Patient landing page lacks a decision-oriented case summary

**Clinician action:** Understand the patient, current uncertainty, next decision and responsible team within a minute.

`PatientFrame` shows name/identifier and episode labels, then four tabs. `ProfileTimeline.tsx:38` leads with the knowledge-cutoff selector; `:49` shows six fact dimensions; the latest clinical assessment appears only at `:131` after the results and expected-input forms. The current approved plan, pinned departmental protocol, clinical review currency, exceptions and next follow-up are all on other tabs. `PatientList.tsx:45` shows an initial registration summary but no current decision/readiness synopsis.

**Fix:** Add a top-level "Case at a glance" projection showing the latest clinician assessment, disease/workup context explicitly as documented, verified/unverified/pending inputs, goals/preferences, current plan/protocol, material-change alert, outstanding exceptions and next owner/action. Keep the complete source-derived longitudinal details underneath. For the demo, label absent diagnosis/stage/risk/performance/comorbidities/prior therapy as "not recorded" or "not applicable" where appropriate; never fabricate missing clinical data or make a one-size-fits-all solid-tumour stage field authoritative for AML.

**Tests:** Known facts remain attributable and link to source; pending does not display as negative; historic knowledge-cutoff views do not use current plan/facts without a clear label; current assessment and actionable missing input appear above the long table.

### 5. P1 — Evidence, applicability and signature are not readable as one connected decision

**Clinician action:** Explain why this protocol applies to this patient, where it does not apply, what exception is accepted, and exactly what is being approved.

The read-only protocol page displays only a count of accepted appraisals (`ProtocolDetail.tsx:119`), with no evidence-to-appraisal-to-paper navigation. `CriteriaEditor` preserves a `supporting` array (`ApplicabilityReview.tsx:14,42`) but supplies no controls to attach or inspect a report/observation/assessment version. Backend `applicability.accept` validates exact supporting records when provided, so this is a missing UI connection rather than absence of backend support. `PlanPanel`'s signing dialog (`:214–223`) shows intent, version, digest and obligations, but omits patient discussion, alternatives, rationale, criterion decisions and exception decisions. Its current-plan summary presents input counts/digests rather than a readable clinical review packet.

**Fix:** Add linked evidence to published protocols; let each applicability criterion cite exact patient records; show an understandable frozen approval summary: patient and clinician assessment/version, protocol/version and linked evidence, goals/preferences, intent and rationale/alternatives, match/difference/unknown criteria with support, exception departures and approvals, follow-up owner/timing. Keep hashes/read sets in secondary technical details. Build that summary from the frozen packet's exact versions; do not silently substitute current records.

**Tests:** Criterion support persists exact version IDs and rejects another patient; full appraisal and source are reachable from a published protocol; signing shows frozen discussion/exception/rationale and a later source correction blocks stale signature without changing historic content. Extend `department-journey.spec.ts` and existing stale-packet guard tests.

### 6. P1 — Follow-up silently infers actual encounter time from appointment time

**Clinician action:** Record what occurred at a follow-up review, including a delayed, remote or unscheduled encounter.

`FollowUpPanel.tsx:76` sends `actual_time: o.scheduled_time` when recording the encounter decision. This asserts the appointment time as the actual clinical time, even when they differ. The care-recording panel already keeps scheduled and actual times separate; follow-up should do the same.

**Fix:** Add a separate clinician-entered actual encounter time, with explicit unknown/time-not-recorded state, and send that value. Do not pre-populate it invisibly from the appointment. Preserve appointment history and clinical timing separately.

**Tests:** Scheduled Day 14, actual review Day 16 persists two distinct times; unscheduled review can explicitly record Day 16; unknown actual time remains unknown. Extend `follow-up.spec.ts` plus `test_follow_up.py` as needed.

### 7. P2 — Exception repair and source amendment are available only through API calls

**Clinician action:** Correct a rejected exception, withdraw a request no longer needed, or mark an evidence document withdrawn/retracted and inspect affected department work.

`ExceptionPanel` exposes request/approve/reject/record-expiry, but not owner-controlled revise/withdraw, although the routes exist at `apps/api/app/api/routes/exceptions.py:28` and `:44`. `ResearchHome` similarly has no amend/withdraw controls despite the research routes and dependent-review machinery (`research._flag_dependants`). The demo currently needs a developer to trigger material changes, weakening the clinical governance demonstration.

**Fix:** Add revision/withdrawal forms with mandatory rationale and clear preserved-history explanation. Research source withdrawal must retain original bytes and citations, mark dependent appraisals/protocols for review, and keep patient-plan currency handling scoped to the affected material.

**Tests:** Requester revises a rejected exception without inheriting old approval; withdrawal leaves history and opens required impact; source withdrawal opens named dependent work and is visible to the reviewer; unrelated patient/protocol records stay unchanged.

### 8. P2 — Care/follow-up ownership cannot complete common real-world lifecycle actions in the UI

**Clinician action:** Ask for another review, transfer it to a receiving team, cancel with a reason, or review a concern while leaving the unresolved duty open.

`FollowUpPanel` has schedule/miss/due-change/encounter decision but no standalone create, transfer or cancel controls. Backend supports create (`api/routes/follow_up.py:61`), cancel (`:75`) and transfer (`:80`). Its empty-state wording assumes follow-up can originate only from a signed plan. `ConcernPanel.tsx:47` always sends `close: true`; backend `ConcernReview.close` defaults to false and supports review without closure. Escalation is also hard-coded to the fictional on-call clinician/service, preventing the oncologist from illustrating an actual ownership choice.

**Fix:** Expose administrative follow-up creation, named owner transfer, reasoned cancellation, review-without-closing, and a capability-filtered escalation recipient/service. Preserve distinctions between review, response and closure. Authored clinical timing must retain its existing clinician-review gate; changing scheduling/ownership must not silently rewrite the clinical plan.

**Tests:** Transfer preserves owner/history and creates receiving-owner work; cancellation preserves reason/outcome unknown; clinician review with `close:false` keeps duty open; no response cannot be closed; administrative action does not invalidate the clinical packet. Extend `follow-up.spec.ts`/`handoff.spec.ts` and corresponding API tests.

## Recommended demo sequence

1. **Start with the patient.** Oncologist opens Meera's case summary, sees verified findings, pending molecular work, the patient's goals, and the question requiring judgement. Show original source and longitudinal changes.
2. **Move to the department's research desk.** Search for an actual reference, inspect its document and study context, draft a focused question and appraisal, distinguish evidence certainty from applicability to this patient.
3. **Use independent review.** The second clinician reads the complete cited evidence, records disagreement, receives a revised appraisal, and independently accepts it.
4. **Approve shared department work.** Explain which requirements are operational and which require clinician-authored content; link evidence, approve/publish a version, and keep SOP tasks distinct from clinical treatment.
5. **Return to the individual patient.** Review each criterion, cite the exact support, document uncertainty/goals, use a reasoned exception for a specific departure, and sign a readable exact packet.
6. **Show the team doing the work.** A coordinator assigns, a care team member accepts, actual activity is recorded separately from appointment scheduling, and unresolved work has a named owner.
7. **Close the loop.** Record a concern without forced closure, transfer or reschedule follow-up appropriately, record an actual follow-up decision/time, and create the next obligation.
8. **Show learning without silent rewriting.** A corrected report or new departmental version opens an impact review; the treating clinician explicitly decides whether to retain or revise the individual plan.

This order presents clinical usefulness first, while making the departmental research role and governance understandable. A clean hosted workspace containing only unreviewed baseline sources will otherwise require long intake/authoring work before the audience sees the full loop. A guided demonstrator workspace should make its preparation status explicit and retain actual named demo actors/history; it must not represent seeded signatures as qualified clinical approval.

## Questions for the oncologist to validate during the demonstration

- Which repeated problem is most costly now: unreadable reports, missing workup, protocol drift, handoff loss or missed follow-up?
- What five facts and next actions must be visible at the top of a new AML case?
- Which evidence sources do they actually use, and who performs extraction/appraisal before departmental review?
- What triggers a department protocol change and who must independently approve it?
- Which patient differences require documented exceptions, and which can never be waived locally?
- What is sufficient source support for each applicability judgement?
- Which team owns follow-up, and what transfer/closure evidence prevents patients being lost?
- What would make this faster than their current spreadsheet/EMR meeting workflow?

Do not claim clinical effectiveness from a software demo. The immediate hypothesis is that the app makes preparation, reasoning, shared knowledge and ownership easier to inspect; the oncologist should validate that against their actual department workflow.
