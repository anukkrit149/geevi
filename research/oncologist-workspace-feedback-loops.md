# Oncologist workspace: two connected review loops

Research checked 11 October 2026. Purpose: support the product framing, not prescribe care for Meera or Arun. These are first-party Australian clinical resources; adoption in an Indian centre requires local clinical and institutional review.

## What the sources establish

1. **Profiling is longitudinal.** eviQ's safe-administration resource distinguishes baseline clinical, physical and psychosocial assessment from ongoing assessment. It lists performance status, laboratory tests, weight, treatment toxicities and protocol-specific investigations; administration checks compare the prescription with the protocol and current patient parameters. Its version history records reviewed changes. This supports keeping the latest verified patient profile alongside changes since the last encounter, rather than treating uploaded reports as a one-time intake. [eviQ: Safe administration of anti-cancer drugs, ID 5 v6](https://www.eviq.org.au/clinical-resources/administration-of-anti-cancer-drugs/5-safe-administration-of-anti-cancer-drugs)

2. **Treatment contains reassessment points and clinician-directed modifications.** The eviQ azacitidine–venetoclax AML protocol calls for repeat laboratory assessment before each cycle and as clinically indicated. Its response assessments distinguish persistent disease from remission; later scheduling and treatment-duration decisions depend on response and blood-count recovery. Thus an encounter record should connect observation, assessment, decision and the next review. This is an example of workflow structure, not a recommendation that either fictional patient should receive this regimen. [eviQ: Acute myeloid leukaemia azacitidine and venetoclax, ID 3892](https://www.eviq.org.au/haematology/leukaemias/acute-myeloid-leukaemia/3892-acute-myeloid-leukaemia-azacitidine-and-venet)

3. **Knowledge publication has its own governance.** eviQ describes evidence appraisal, summaries of outcomes and adverse events, conflict-of-interest declarations and expert reference-committee review. Consensus is required before approval and publication; the governance page states periodic review at one to four years. That is a separate process from an individual patient's treatment decision. [eviQ: Governance and development](https://www.eviq.org.au/governance-development)

## Product proposals inferred from those facts

These are design proposals, not features mandated by the sources or proven productivity benefits.

- **Clinical work queue:** surface patients with a decision due, changed findings, missing investigations, unresolved toxicities or overdue follow-up. A coordinator prepares the record; the oncologist reviews exceptions and makes the clinical decision. Show owner and deadline for each item.
- **Living patient workspace:** retain report provenance, collection date, verification status and successive profile snapshots. Each encounter records intended care, delivered care, observations, response/toxicity, patient preferences, clinician assessment, continue/hold/modify/change decision, rationale and next assessment. Measurements and reported symptoms must remain distinct from clinical interpretations.
- **Knowledge workspace:** research question → assigned search/review → evidence appraisal → requested additional reviews → approve/reject/defer → reusable evidence entry. Preserve source passages, population, interventions/comparators, results, limitations, reviewer and review date. A protocol revision should have a separate draft, review, publication and supersession history.
- **Explicit bridge:** approved knowledge can be considered for a patient. Record applicability, current patient facts and the oncologist's decision. Publishing new evidence should generate a review opportunity, not silently change active plans.

## Important distinctions to model

| Record | Scope | Proposed review responsibility |
|---|---|---|
| Evidence appraisal | What a study supports, and its limitations | Assigned qualified reviewers and approving clinician |
| Protocol template version | Reusable institutional approach | Institution's designated clinical governance process |
| Patient plan version | How the approach applies to this individual | Treating oncologist with relevant specialist input |
| Session/cycle decision | Whether and how to proceed using current findings | Authorized clinical team under local policy |
| Delivery record | What actually happened and what needs escalation | Delivering clinical team |

A patient's feedback may trigger a plan amendment or a request to review the reusable protocol; it does not by itself establish that the protocol should change for all patients. Family observations can inform the clinical review without becoming treatment authorization. Retain the prior signed plan and its source versions when creating an amendment.

## Limits and validation needed

These sources substantiate recurring assessments and governed evidence review. They do not establish this product's time savings, the typical Indian oncologist's patient load, an optimal alert threshold, or the right allocation of work in a particular hospital. Validate those through observed clinic workflows and time/task measurements. Medical-oncology cycles are not a complete surgical-oncology workflow; surgery needs its own multidisciplinary, preoperative, intraoperative and postoperative design. Source review dates and versions should remain visible because publication and freshness are different attributes.
