# Clinical workflow: where the vision fits, and what changes

Generated 11 October 2026. Research strand only; no prototype inspection and no patient treatment recommendations.

## Finding

The direction is credible as an oncology care-coordination and learning workspace. The sharper problem is: **give the team a verified, usable account of the patient, a documented patient-specific decision, and a reliable way to carry that decision through care.** Merely collecting patients and attaching protocols misses much of the operational work.

The senior-expert model needs a correction. NHS guidance uses approved pathways to free multidisciplinary meeting time for complex cases while preserving oversight and individual decisions. It explicitly places “any treatment decision” with “the responsible clinician and patient.” Senior clinicians can spend more time developing evidence and reviewing difficult cases; public evidence does not support removing their clinical review role. [NHS guidance, pp. 9–13](https://www.england.nhs.uk/wp-content/uploads/2020/01/multi-disciplinary-team-streamlining-guidance.pdf)

## Proposed role-owned workflow

This is a proposed product workflow, informed by sources below and requiring local observation. It is not a claim that every department already works this way.

| Stage | Accountable human | Useful software work | Required output / next step |
|---|---|---|---|
| Referral and preparation | Navigator/coordinator, with referring clinician verifying clinical information | Collect prior records, organize chronology, expose missing or contradictory facts, assign collection tasks | Source-linked case package; explicit unknowns; named owner and next appointment |
| Clinical readiness | Treating oncologist, with relevant pathology/radiology specialists | Show reviewed diagnostic and patient context against a locally approved checklist | Ready / incomplete / needs clarification status, with reasons and accountable verifier |
| Select discussion route | Oncologist or approved triage group | Compare case to pathway eligibility; flag uncertainty or exception; assemble meeting agenda | Routine pathway candidate or multidisciplinary/complex review; human confirmation |
| Decide an individualized plan | Treating clinician and patient; multidisciplinary team contributes recommendations | Bring approved pathway, evidence, patient goals and practical constraints into one view | Options discussed; agreed plan; consent record/reference; rationale and unresolved questions |
| Execute care | Treating clinician, nurses, pharmacy and other relevant services | Convert approved plan into role-owned tasks and handoffs; reconcile with source systems | Clear next action and timing; verified planned versus actually completed care; delays and reasons |
| Monitor and adapt | Nursing team and treating clinician, with patient participation | Capture symptoms and patient concerns; route alerts; track response; prepare follow-up | Acknowledged issue, documented action and reassessment; clinician-approved change or escalation |
| Close a phase and learn | Treating team; departmental quality/research group receives governed data | Reconcile outcomes and missing follow-up, make review cohorts and recurring exception reports | Patient follow-up/support plan plus an auditable dataset for approved quality/research use |

The 2025 ASCO–COA standards support the broad service shape: multidisciplinary planning, individualized education, clear team responsibilities, support navigation and quality improvement. They say patients should receive “an individualized treatment plan.” These are professional expectations, not proof that this proposed product delivers them. [ASCO–COA 2025 standards](https://ascopubs.org/doi/10.1200/OP-25-00498)

## Four objects the product should keep distinct

1. **Clinical pathway/protocol:** the approved reference for a defined population, with eligibility, exceptions, evidence and version.
2. **Patient-specific care plan:** a clinician-approved, patient-agreed application or justified departure, with goals and follow-up.
3. **Departmental standard operating procedure:** how staff prepare, review, hand off, escalate, document and audit work.
4. **Research protocol:** a governed study with a specific question, population, methods, data plan and required approvals.

This separation is a design recommendation. It prevents the word “protocol” from hiding distinct responsibilities. An evidence article should not become a new live treatment pathway just because it entered the research module.

## Disconfirming findings and design consequences

- **Standardization is conditional.** The NHS minimum case dataset and triage safeguards make readiness a clinical process, not an upload count. A patient preference that conflicts with a standard pathway can itself justify full discussion. Proposed consequence: visible unknowns, clinician verification, and exception routing before any decision-assistance score. [NHS guidance](https://www.england.nhs.uk/wp-content/uploads/2020/01/multi-disciplinary-team-streamlining-guidance.pdf)
- **Patient benefit is not necessarily survival benefit.** In PRO-TECT, 1,191 patients across 52 US practices were studied. Mean emergency visits at 12 months were 1.02 with symptom monitoring versus 1.30 with usual care; survival did not differ (HR 0.99, P=0.86). Proposed consequence: measure symptom response, follow-through, patient experience and avoidable utilization rather than promising longer survival. [PRO-TECT](https://pmc.ncbi.nlm.nih.gov/articles/PMC12184200/)
- **Alerting creates work.** PRO-TECT used responsible nurses and supported patient participation. Its authors identify staff time and integration as implementation needs. Proposed consequence: no patient alert feature without an owner, response process and backup; count workload as well as detected issues. [PRO-TECT](https://pmc.ncbi.nlm.nih.gov/articles/PMC12184200/)
- **Good standards do not establish local demand.** The source settings are England and US oncology, not the user's intended Indian department. Which missing records, delays, handoffs, systems and staffing limits matter most remains unverified. The workflow should be tested against real staff practice before a broad build.

## Test whether this is the right problem

Start with one tumour service and observe consecutive real case journeys under the hospital's approved access arrangements. Include a coordinator, treating oncologist, specialist reviewer, nurse, pharmacy representative where relevant, and patients/caregivers. Ask each to identify the last actual delay, rework episode, lost handoff or unresolved patient concern. Record the existing system used at each step.

Suggested discovery measures (proposed, not research-derived thresholds): preparation time, repeated data entry, unresolved facts at review, cases deferred for missing information, decision-to-next-action delay, unowned tasks, follow-up completion, alert response work and clinician trust in source links. Separate clinical/administrative delay from affordability, patient choice, travel, capacity or other causes the product cannot directly solve.

Pilot the source-linked case package and action tracking in shadow mode first. Success requires saving work or reducing a real failure without adding unacceptable verification burden. A valuable disconfirmation would be discovering that an existing hospital system already handles the workflow and the main bottleneck is staffing, diagnostic capacity, access or data-sharing permission. In that case, a small integration or operating-process change may beat a new platform.

## Sources, access and audit

Primary sources cited: 3. Full primary sources read: 2 (NHS document and PRO-TECT); ASCO 2025 was available only as indexed official/article excerpts. Source notes are in `sources/clinical_nhs_mdt.md`, `sources/clinical_asco_2025.md`, and `sources/clinical_protect_2025.md`.

Search queries sent: **7** (4 browser discovery attempts, 3 substantive indexed queries). Indexed source URLs received: **22** (including duplicate article variants and irrelevant results); sources cited: **3**. No secondary result was used as substantive evidence.

Browser discovery queries:
1. Google: `NHS England multidisciplinary team streamlining cancer patient preferences minimum dataset` — CAPTCHA.
2. Bing: same terms — results apparently reduced to NHS; unhelpful.
3. Bing: `"Streamlining" "multi-disciplinary" "cancer"` — dictionary results; unhelpful.
4. NHS site search: `streamlining` — blank HTTP 202.

Indexed discovery queries after parent-authorized fallback:
5. `NHS England streamlining multidisciplinary team meetings cancer standard of care patient preferences minimum dataset`
6. `oncology medical home ASCO standards patient care coordination treatment plan shared decision making 2021`
7. `Basch PRO-TECT patient reported outcomes randomized trial 2025 symptom monitoring survival`

Access failures: 6 browser blocks/empty responses including the Google and NHS search failures, NICE 403, ASCO article 403, official ASCO 403, and PMC cookies-required response. Two additional Bing queries were unhelpful. Three read-only fallback fetches of ASCO pages failed. The browser sequence stopped after three consecutive primary-page blocks and was reported to parent; parent directed transparent read-only retrieval fallback. Do not represent those blocked pages as browser-verified. A preliminary tool invocation also failed because its /tmp working directory did not yet exist; it was created and the isolated browser then started successfully (PID 13933).

The browser used a separate working directory `/tmp/oncology-clinical-research`, with a fresh daemon at `about:blank`, to avoid interfering with parallel agents. No patient data was accessed, no external messages sent and no prototype files modified.
