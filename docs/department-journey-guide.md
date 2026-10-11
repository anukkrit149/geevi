# Department journey guide

What the Geevi application demonstrates, how to walk through it, what was verified on 11 October 2026, and what it
does not establish.

> Fictional data, development identities, demonstration signatures. Software correctness below is **not** clinical
> validation. No treatment recommendation, dosing order or institutional qualification is inferred. Fictional reported treatment history is clearly labelled and separate from prescribing.

## 1. Walkthrough

Sign in with the development identities (passwords in `apps/api/.dev-credentials.json`). Each step is a real server
command by the signed-in account. "Insert fictional …" buttons only prefill a form in development mode; the account
still saves and submits it.

| Flow | Who | Where | What happens |
|---|---|---|---|
| F1 | Rao | Research | Add an attributed published-reference brief to the evidence library, open a question, write an appraisal citing an exact passage, submit to Sen |
| F1 | Sen | Today → question | Object with a rationale. Rao opens a successor revision; Sen approves it. Both decisions stay in the history |
| F1 | Rao, Sen | Department | Protocol v1 draft with accepted evidence → Sen approves → Rao publishes. Same for the separate SOP |
| F2 | Mira | Patients → Reports | Register Meera, receive each report, review identity, inspect each region in the original, verify or correct |
| F2 | Mira, Rao | Profile | Awaited investigations under Reports; clinician assessment, disease burden, treatment/response and trends under Clinical overview; earlier versions under Record history |
| F3 | Mira, Rao | Decisions | Discussion; criterion-level applicability; operational venue exception requested and approved; clinical exception left pending for Sen; plan saved, submitted (frozen) and signed |
| F4 | Mira, Isha | Care & follow-up | SOP tasks assigned and sent; Isha accepts and completes with evidence; scheduled event, then separate actual care; concern acknowledged, answered, reviewed |
| F4 | Mira, Rao | Care & follow-up, Impact queue | Follow-up result arrives; Rao classifies and dispositions it; encounter decision "continue unchanged" keeps the same plan and creates the next obligation |
| F5 | Rao, Sen | Research, Department, Impact queue | Second question and evidence; change proposal; protocol v2 published; one impact each for Meera and Arun; Meera retains v1; Arun adopts only after a new applicability review and a newly signed plan |
| F6 | Mira, Rao | Sources, Impact queue | Marrow correction; plan stays signed and active but review-needed; dependent new handoff is blocked; Rao dispositions the impact |
| Recovery | Operator | Import & recovery | Full backup download, staged restore into another workspace, explicit activation; legacy import |

The episode stays **ongoing** at the end. The pending clinical exception (next decider: Sen), the pending final
molecular report (owner: Mira), the next follow-up obligation (owner: Mira) and the undispatched planning-visit
task all remain visible with an owner and next action.

## 2. Verification run

All commands were run locally on 11 October 2026 (macOS, toolchain in `development.md`).

| Check | Command | Result |
|---|---|---|
| Backend lint | `uv run ruff check app tests scripts` | clean |
| Backend domain / HTTP / PostgreSQL | `uv run pytest tests` | **107 tests** (full suite verified again for this update) |
| Migrations | `alembic upgrade head`, `downgrade 0005`, `upgrade head` on an empty database | applied both ways |
| Contract | `pnpm contracts:check` | OpenAPI artifact and generated types current |
| Frontend lint, types | `pnpm --dir apps/web lint`, `typecheck` | clean |
| Frontend components | `pnpm --dir apps/web test` | **11 passed** |
| Frontend production build | `pnpm --dir apps/web build` | compiled, 19 routes |
| Browser journeys | `pnpm --dir apps/web exec playwright test` | **25 browser journeys** (includes clinician overview and post-login patient-link continuity) |
| Manual browser pass | gstack browse (headless fallback), desktop / tablet / mobile widths | see section 5 |
| Compose | `docker compose config` | valid; **stack not started** (no Docker daemon) |
| CI workflow | — | [Previous main CI passed](https://github.com/anukkrit149/geevi/actions/runs/38134598244); this change is verified again before deployment |
| Clinical content review | — | **not performed**; content stays unvalidated |

Backend tests run on a disposable PostgreSQL database with the real migrations. Browser tests run against the real
API, real sessions, a dedicated database and a production build; set-up steps that are not the subject of a test
use the same HTTP API as the proper account. No test writes to the database directly, except one archive test that
deliberately damages stored bytes to simulate storage loss.

### Where each proof lives

| Subject | Backend tests | Browser tests |
|---|---|---|
| Idempotent commands, payload/actor mismatch, workspace lock, aborted commit, same-id retry | `test_commands.py`, `test_transactions.py` | `guards.spec.ts` (lost response, same command id) |
| Sessions, CSRF, Origin, forged actor fields, cross-workspace, logout | `test_auth.py` | `guards.spec.ts` |
| Identities, originals, quarantine, result states, addendum vs correction, expected inputs, active content | `test_sources.py` | `source-review.spec.ts` |
| Trends, late-arriving report, knowledge-cutoff snapshots | `test_profiles.py` | `department-journey.spec.ts` (F6) |
| Fixture integrity, reproducibility, gold isolation, dev-mode gate | `test_fixtures.py` | — |
| Legacy import, missing originals, unmapped approvals, interruption, excluded format | `test_legacy_import.py` | `legacy-import.spec.ts` |
| Evidence review, independence, objection history, source withdrawal, insufficient evidence | `test_research.py` | `research-review.spec.ts`, journey F1 |
| Protocol/SOP review, publication, future-effective immutability, review due, withdrawal | `test_protocols.py`, `test_sops.py` | journey F1/F5, `protocol-change.spec.ts` |
| Applicability, watch scopes, stale signature, scoped currency | `test_applicability.py`, `test_review_dependencies.py` | `guards.spec.ts` (AE5) |
| Exceptions, non-waivable scope, pending clinical exception, expiry | `test_exceptions.py` | journey F3/F4 |
| Exact plan approval, concurrent change under the lock, signed history | `test_plans.py` | journey F3, `guards.spec.ts` |
| Handoffs, scheduling vs delivery, attribution, late event, pending transfer | `test_care.py` | `handoff.spec.ts`, journey F4 |
| Concerns, unchanged follow-up, missed/rescheduled, clinical vs administrative timing | `test_follow_up.py` | `follow-up.spec.ts`, journey F4 |
| Impacts: two per publication, dedupe, adoption needs an approved plan, atomic publication | `test_impacts.py` | journey F5/F6, `protocol-change.spec.ts` |
| Archive: fresh-database restore, incomplete backup, bad archives, injection, side-by-side ids | `test_archives.py` | `archive-restore.spec.ts` |
| Server restart and fresh browser contexts | — | journey (last test) |
| Keyboard, dialog focus, error summary, status, narrow width | component tests | `guards.spec.ts` (R32) |

### Acceptance examples

| ID | Evidence |
|---|---|
| AE1 | `test_impacts.py::test_publishing_v2_creates_two_impacts_resolved_independently`; journey F5 |
| AE2 | `test_profiles.py::test_correction_changes_current_profile_but_not_the_earlier_view`; journey F6 |
| AE3 | `test_exceptions.py::test_pending_clinical_exception_blocks_only_its_affected_action`; journey F3/F4 |
| AE4 | `test_follow_up.py::test_routine_review_needs_no_concern_retains_plan_and_creates_next_obligation`; journey F4 |
| AE5 | `test_review_dependencies.py`; `test_plans.py::test_concurrent_material_change_…`; `guards.spec.ts` |
| AE6 | `test_legacy_import.py`, `test_archives.py` (interruption, hash mismatch); `legacy-import.spec.ts`, `archive-restore.spec.ts` |

## 3. Requirements

| Req. | How it is met | Boundary |
|---|---|---|
| R1 | Separate patient, episode, encounter, specimen, report family/version records; namespaced identifiers; explicit association review; quarantine | |
| R2 | Content-addressed `source_blobs` (bytes, SHA-256, length, type), issuer/author, page/region per assertion | |
| R3 | `observation_versions` per report/specimen/assay; profile and assessment are separate | Many-to-many report↔document/specimen links are JSON lists validated in services, not association tables |
| R4 | Nine distinct result states end to end | State wording rules are fixture-layout rules, not a general parser |
| R5 | Relation kind and predecessor per report version; a re-sent accession with no stated relation stays `unresolved` | |
| R6 | Every record carries the workspace sequence; profile projection and stored snapshots use a knowledge cutoff | |
| R7 | Expected inputs with owner, next action, history; fulfilled only by an explicitly linked matching report | |
| R8 | Question, intended use, passages, structured appraisal, assignments, decision history | Local/imported evidence only |
| R9 | Evidence acceptance writes nothing to protocols or patients | |
| R10 | Frozen digest, named policy version, assigned independent reviewer, separate publication decision | Policy is a fixed fictional policy, not a committee engine |
| R11 | Draft, in review, changes requested, approved, published, effective, superseded, review-due, withdrawn | Effective/superseded are projections over recorded dates |
| R12 | SOP versions with role-owned steps; tasks reference the exact SOP version and step | |
| R13 | Publication/withdrawal nominates one impact per live dependent plan in the same transaction | |
| R14 | Insufficient-evidence conclusion; no protocol or recommendation | |
| R15 | Criterion-level match / difference / unknown / not applicable with rationale and pinned snapshot | |
| R16 | Signature names packet id and digest; read set and watch set re-checked under the workspace lock | |
| R17 | Typed, scoped request; approvers from policy; expiry or review trigger; protocol unchanged | |
| R18 | Gates per requirement; pending/rejected/expired exceptions and unknown non-waivable inputs block only their gate | |
| R19 | Impacts mark the plan review-needed; signature, history and disposition are kept | |
| R20 | Task edits touch no clinical scope; a change to authored timing opens clinician review | |
| R21 | Draft, sent, received, accepted, returned, blocked, completed, cancelled with owner and evidence | |
| R22 | Planned events, care events and external transcription are separate, attributed, with a historical plan reference | |
| R23 | Concern events; acknowledgement is not a response; closing requires a response | Escalation names a demo service; no triage logic |
| R24 | Follow-up obligations with schedule, missed, cancelled, transferred, fulfilled and history | |
| R25 | Encounter decision "continue unchanged" keeps the plan id and creates the next obligation | |
| R26 | Nothing infers discharge or outcome; the episode stays ongoing | |
| R27 | One transaction per command; receipts; revision compare-and-set | |
| R28 | Server sessions and grants; operator has no clinical authority; an author cannot review their own work | Development identities only |
| R29 | Explicit legacy snapshot/packet import to staging; raw payload preserved; retry-safe | Requires the user to capture the old stores; no cross-origin read |
| R30 | Versioned archive with all container records, receipts and original bytes; incomplete reasons listed | JSON/base64, suitable for small fictional data |
| R31 | Schema, size, hash and reference validation in staging; explicit activation | |
| R32 | Keyboard, dialog focus, focused error summary, live status, source links, narrow layout | Not a formal accessibility audit |
| R33 | Inputs, gold and public references are separate; nothing real is joined to a fictional chart | |
| R34 | Unvalidated status is stated in the UI, API notices, fixtures and this guide | Qualified clinical review has not happened |

Original acceptance matrix: A01–A11, B01–B06, C01–C10, D01–D08, E01–E03, F01/F02/F04/F06/F07 are covered by the tests
above. F03 is covered at HTTP/session level only. **E04** (cohort export), **F05** (upstream write-back) and
**F08** (human content/workflow review) are not delivered.

## 4. Implementation decisions worth knowing

- **Location.** The application lives in its own folder `geevi/` (with `apps/web`, `apps/api` inside), as directed,
  with Geevi itself as the independent GitHub repository root. The workflow is discovered at `.github/workflows/oncology-app-ci.yml`.
- **Six Alembic revisions**, one per unit group, plus the append-only triggers; not one revision per unit.
- **Read models are derived from the tables** (`app/schemas/auto.py`); request schemas are hand-written.
- **Uploads are base64 JSON**, bounded by `GEEVI_MAX_UPLOAD_BYTES`, so every write is one idempotent command.
- **The molecular requirement gates one SOP step**, not plan approval, so a pending clinical exception blocks only
  the planning-visit handoff while preparation continues.
- **New material after a signed plan opens an impact that needs classification**; while unclassified it blocks a new
  approval and an unchanged continuation. A corrected pinned fact skips classification.
- **A withdrawn successor makes its predecessor effective again** in the lifecycle projection.
- **Legacy facts import as unreviewed candidates.** The legacy review is kept as history, never as current verification.
- **Import staging and workspace creation** are idempotent through `import_jobs`, not through command receipts;
  `POST /workspaces` is not idempotent.
- **Browser specs** named in the plan all exist; `guards.spec.ts` is an addition.

## 5. Manual browser pass

Run with gstack browse. The Aside browser is not installed, so gstack's headless browser was used, signed in as
`mira` with the generated fictional password. Checked: sign-in page, Today worklist, a source document with the
rendered PDF, at 1280, 768 and 375 px. Findings fixed: duplicated units ("90 % %") and candidate findings not in
reading order. The only console message is the expected `401` session probe before sign-in.
Screenshots: `.gstack/browse-reports/` (ignored).

Problems found by the browser tests and fixed: the session context stayed stale after sign-in and sign-out; a
dialog opened with focus on Close instead of the first field; a queued native `close` event could close a dialog
that had just been reopened.

## 6. Limits

- **Not clinically validated.** Protocol, SOP, reports and scenario are invented workflow content. A qualified
  clinician has not reviewed them.
- **No extraction accuracy claim.** Candidate extraction is deterministic label/row matching for the fixture
  layouts. Other layouts and images need manual entry. There is no OCR or model.
- **Development authentication only.** No SSO, real-user qualification, password policy, rate limiting or lockout.
- **Signatures are demonstration records**, not institutionally authenticated signatures.
- **API-only function without a screen:** episode transfer. Evidence amendment/withdrawal, exception revision/withdrawal, follow-up creation/transfer/cancellation and concern review without closure now have screens.
- **Compose runtime is unexecuted**; the hosted Vercel demo and GitHub CI have been exercised.
- **Concurrency in browser tests** is two authenticated sessions interleaved against the real server lock; true
  simultaneous commits are proven in the backend tests with threads.
- **Archives** are single JSON documents with base64 originals; fine for small fictional data only.
- **Not built:** institutional SSO, hospital/EHR/FHIR integration and write-back, cohort analytics and export,
  prospective-study administration, clinical extraction evaluation, notifications outside the app,
  production security and operational backup.


## Oncologist UX and evidence update

See [the clinician walkthrough, source-depth notes, dataset model and usability study plan](oncologist-demo-and-ux.md). The synthetic research papers were replaced by cited, original evidence briefs. Patient documents remain fictional. Research metadata, full-text access and limitations are explicit; no systematic or current-guideline review is claimed. An isolated, prepared walkthrough is created through authenticated development-actor API commands, with simulated approvals, using `scripts/prepare-oncologist-demo.py`.
