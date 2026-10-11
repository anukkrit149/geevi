# Fictional department-journey source pack

Everything in this folder is invented for software demonstration. No real patient, study subject, laboratory or
clinical recommendation appears here, and no real cohort record is joined to Meera or Arun. Values are
plausible-looking placeholders, not clinical guidance. Clinical content is **unvalidated** pending qualified review.

| Path | Purpose | Read by |
|---|---|---|
| `inputs/` | Separate source reports (PDF, one image-only PNG) and two synthetic research notes | Development fixture loader, tests, manual upload |
| `manifest.json` | Input list with SHA-256, length, patient, report type, stage and relative-day anchor | Fixture loader, tests |
| `scenario.json` | Authored scenario text: questions, appraisals, protocol v1/v2 requirements, SOP steps, exception wording | `/api/v1/dev/scenario` (development mode) to prefill forms |
| `gold/` | Independent expected outputs per input (intended assertions, relation, supersession) | **Tests only.** Never read by runtime code, never served |
| `references/public-references.json` | Public standards/datasets that informed structure only | Documentation |

Regenerate with `pnpm fixtures:make`. Output is byte-reproducible; a test compares regenerated hashes with the manifest.

## What each input exercises

| Input | Relationship |
|---|---|
| `meera-referral` | Episode history and source authorship; an explicitly unreported item |
| `meera-blood-day-minus-1`, `meera-blood-day-6` | Repeated panels: timed values, units, reference ranges, trend without overwrite |
| `meera-marrow` | Two specimen parts; each finding tied to its part and exact region |
| `meera-flow` | A line the layout rule over-reads, so the reviewer must correct the transcription |
| `meera-cyto` | `insufficient sample` as a distinct state |
| `meera-molecular-preliminary` | Pending / not detected / not tested / indeterminate; arrives late but describes Day 1 material |
| `meera-marrow-addendum` | Additive addendum: nothing is superseded |
| `meera-marrow-correction` | Correction: supersedes only the named assertion |
| `arun-*` | A second patient; `arun-cyto` reuses Meera's accession number from a different issuer |
| `arun-echo-scan` (PNG) | Image-only original: no machine findings, manual source-linked entry |
| `arun-blood-day-2` uploaded to Meera | Wrong-patient document is quarantined |

Dates are relative demonstration days (`Day 0` = referral received). They illustrate workflow only.
The protocol requirements are workflow requirements (identity, context, discussion, venue, an input gate); they
contain no clinical eligibility, dosing or therapy content.
