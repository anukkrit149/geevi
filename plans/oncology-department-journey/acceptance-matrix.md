# Acceptance matrix for the complete journey

11 October 2026 · Planned checks, not executed tests. This matrix specifies the intended implementation; the current prototype does not claim these checks pass.

| ID | Scenario | Observable acceptance condition | Primary level |
|---|---|---|---|
| A01 | Same external accession in different issuing labs | Separate internal records retain issuer/system; no accidental patient/specimen merge | Model/integration |
| A02 | Wrong-patient PDF imported | Association is blocked pending resolution; no facts leak into either approved profile | Model/browser |
| A03 | Same bytes imported twice | Duplicate is recognized; prior review/source identity preserved; no doubled observations | Model/integration |
| A04 | Same report family arrives amended | Both versions remain accessible; changes and impacted decisions are identified | Model/browser |
| A05 | Different value on a later specimen | Separate timed results are shown; no silent overwrite or automatic error label | Model/browser |
| A06 | Negative, untested, pending, insufficient sample and unreported | States remain distinct in profile, applicability, export and cohort preparation | Model/browser |
| A07 | Multi-specimen report | Each finding resolves to the correct specimen/part and source region | Model/browser |
| A08 | Source transcription corrected | Original wording, correction, reason and reviewer retained; affected decisions only are flagged | Model/browser |
| A09 | Image-only or unsupported report | Original remains reviewable; no invented findings; evaluated/manual path visible | Browser |
| A10 | Original unavailable/corrupt | Error is explicit; no replacement bytes or false source verification | Integration/browser |
| A11 | Historical snapshot opened after a new report | It shows only the source/fact versions known to that review | Model/browser |
| B01 | Evidence accepted for library | It can be reused, but no protocol or patient plan is automatically approved | Model/browser |
| B02 | Required protocol reviewer has not responded | Publication remains unavailable with named missing review | Model/browser |
| B03 | Reviewers disagree | Disagreement and resolution are explicit; majority/last edit cannot silently mark consensus | Model/browser |
| B04 | Protocol approved for future effective date | Approved and active/effective states are different; applicable version is visible | Model/browser |
| B05 | Protocol v2 published | v1 stays immutable; patients referencing v1 enter scoped impact review | Model/integration |
| B06 | Source withdrawn or materially corrected | Its status and dependencies are visible; assigned impact review opens; no automated treatment instruction | Model/integration |
| C01 | Same shared protocol applied to two patients | Separate applicability decisions, goals, plans and signatures; no cross-case approval reuse | Model/browser |
| C02 | Required fact unknown | It is not interpreted as matching; approved local requirement/exception policy determines disposition | Model/browser |
| C03 | Patient-specific exception approved | Scope, rationale, reviewer and review trigger retained; shared protocol unchanged | Model/browser |
| C04 | Exception rejected/expired | It cannot silently authorize a plan; clinician sees required next step | Model/browser |
| C05 | Non-waivable configured requirement | General exception or admin role cannot bypass it | Authorization/model |
| C06 | User edits an already reviewed draft before sign | Signature rejected until exact changed version is reviewed | Model/browser |
| C07 | New material dependent fact arrives while signing | Concurrent version check rejects stale approval with reason | Integration |
| C08 | Routine no-change follow-up | Clinician can record scoped continuation without re-appraising an unchanged paper | Model/browser |
| C09 | Coordinator changes a task owner/deadline | Task audit updates; unrelated clinical approval stays valid | Model/browser |
| C10 | New patient preference changes plan relevance | Targeted clinical review is requested; source evidence appraisal remains reusable | Model/browser |
| D01 | Handoff sent but unacknowledged | Sent/received/accepted statuses remain distinct and assigned owner is visible | Integration/browser |
| D02 | Task returned/blocked | Reason and next owner/action shown; status is not completed | Model/browser |
| D03 | Session scheduled but not recorded | UI cannot claim delivery, response or tolerability | Model/browser |
| D04 | Partial/deferred/uncertain care | Actual event preserves status and historical plan/order references | Model/browser |
| D05 | Clinician transcribes external team report | Reported author/source and transcriber distinguished from authenticated team signature | Model/browser |
| D06 | Patient concern received | Owner, acknowledgement, response/escalation and unresolved state are visible | Integration/browser |
| D07 | Follow-up missed | Team can record reason and reassign/reschedule under policy; no silent closure | Model/browser |
| D08 | Historical care recorded against an older plan | Allowed with attribution; does not reactivate that plan or authorize new treatment | Model/browser |
| E01 | Protocol impact review resolved for Meera | Arun remains open; current plan is preserved unless a new version is approved | Model/browser |
| E02 | Clinician elects to remain on previous protocol | Rationale, authority and review trigger recorded as required by service policy | Model/browser |
| E03 | Research question generated from case issue | Optional case link plus scope/owner/due date; no immediate treatment conclusion | Model/browser |
| E04 | Dataset export for research | Purpose, version, inclusion criteria, lineage and missingness included; access scope enforced | Integration/research review |
| F01 | Reload and restart during workflow | Current draft and immutable approvals persist or storage failure is explicit | Integration/browser |
| F02 | Legacy-store migration interrupted | Retry is idempotent; no lost originals or fabricated protocol approvals; rollback/export available | Migration |
| F03 | Unauthorized role directly calls approval action | Server blocks in pilot; UI hiding alone does not count as authorization | Authorization/integration |
| F04 | Duplicate integration message or repeated click | One durable event/task/plan change, not duplicates | Integration |
| F05 | Upstream write-back fails | Pending/failed state and retry owner visible; not shown as delivered | Integration |
| F06 | Keyboard and screen-reader navigation | Source links, review forms, error summaries, focus and status changes usable | Accessibility/browser |
| F07 | Export/reimport review packet | Versions, provenance and uncertainty preserved; missing originals reported | Integration |
| F08 | Independent clinical/content review | Synthetic case plausibility and clinical policy gaps documented; no clinical-validity claim from software tests | Human review |

## Completion of the first deliverable

P0–P6 are complete only when the main journey can be demonstrated from a clean fictional store, both patients reference the same published protocol, an exception and a no-change follow-up work, protocol v2 produces independent impact reviews, and the applicable checks above pass. Server-specific checks are gates for P7; local simulated roles do not satisfy them.

The demonstration packet includes source originals, expected facts, scenario script, review history, screenshots/recording if useful, known limitations and test results. The real-data extraction evaluation is a separately reported result with corpus/access details and independent annotation. Nothing in this matrix establishes a patient-treatment recommendation.
