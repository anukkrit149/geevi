# Research and protocol governance findings

Prepared 11 October 2026. Scope: evidence-to-protocol governance, departmental research and the proposed senior-expert staffing model. This strand did not inspect Oncologic or the local product.

## Decision

The intended learning loop is coherent: reliable care records → useful operational and research questions → evidence appraisal → approved departmental changes → monitored care. The weak assumption is that the most expert oncologist can stop participating in complex clinical decisions and that colleagues can simply execute their SOPs. The reviewed sources support expert curation and shared evidence processes, with continued individual clinician judgment. They do not establish the proposed staffing model as effective.

## What evidence supports

NCI explicitly distinguishes evidence summaries from treatment recommendations: “They are not clinical practice guidelines or treatment recommendations.” Its PDQ editorial process reviews new papers monthly and uses consensus updates, and it ranks expert opinion below stronger study designs. This argues for a senior clinician leading an evidence group and protocol review, with documented disagreement and applicability, rather than one person's judgment being the software's ground truth. [NCI PDQ](https://www.cancer.gov/publications/pdq/information-summaries), [NCI evidence methods](https://www.cancer.gov/publications/pdq/levels-evidence/treatment).

ASCO's own guideline assistant says it “does not substitute for the independent judgment of a licensed healthcare professional.” This source was available in indexed discovery but its website was blocked for full browsing. The design implication is to preserve patient-specific decisions and an exception route. This does not prove which cases should be escalated or how much senior time can be reallocated; those thresholds need local clinician agreement and pilot measurement. [ASCO Guidelines Assistant](https://www.asco.org/practice-patients/guidelines/assistant).

The data problem is real at the institutional level: NCI's September 2026 program prioritizes completeness, quality, extraction and harmonization of care data. It explicitly describes routine electronic records as messy. That supports a foundation of source-linked clinical facts, review status and consistent longitudinal events before a sophisticated departmental research interface. It does not independently validate demand for this specific product. [NCI real-world data](https://www.cancer.gov/about-nci/organization/cbiit/projects/real-world-data).

## Keep three kinds of research distinct

| Activity | Useful first software capability | Review/authorization boundary | What the result means |
|---|---|---|---|
| Literature and guideline research | Evidence inbox; source excerpts; paper population/intervention/comparator/endpoints; evidence strength; applicability; draft amendment | Named expert review and departmental adoption before a clinical protocol changes | A synthesis or proposed change, not automatic patient advice |
| Operational audit and retrospective clinical research | Data quality dashboard; follow-through, delay and exception analysis; reproducible cohort definitions; dataset snapshot; missingness | Institution determines quality improvement versus research and applicable review/consent conditions; do not let the software decide exemption | Service signals and associations; useful for quality improvement or research hypotheses |
| Prospective studies/trials | Eligibility worklist for investigator review; study protocol/version; consent status; scheduled study events; study-specific data | Named investigator and applicable scientific/ethics approvals before research starts; appropriate registration | Research evidence under a defined study design; distinct from routine care |

The ICMR research-integrity policy calls for scientific and ethics review as applicable, qualified research conduct, peer review and preservation of raw data. It supports explicit investigator and study ownership. It does not mean every service audit requires full committee review, nor that retrospective research is automatically exempt. [ICMR policy, section 5](https://www.icmr.gov.in/icmrobject/uploads/Guidelines/1724844182_icmr_pripe2019.pdf).

## Proposed departmental loop and owners

These are design recommendations inferred from the sources, not a validated hospital workflow:

1. **Evidence lead and relevant specialists:** watch important evidence, appraise quality and applicability, log a proposed protocol amendment with citations and uncertainties.
2. **Departmental review group:** evaluate clinical implications, practical delivery and patient-context constraints; approve, reject or request revisions. Capture rationale and conflict disclosures.
3. **Protocol owner:** publish a versioned pathway/SOP with defined eligible population, review date, responsible roles, exception and escalation rules. Do not silently alter old versions.
4. **Treating oncologist:** assess the individual patient, record the selected pathway version and case decision, incorporate the patient's priorities, and document any deviation or expert consultation.
5. **Care team:** record actual treatment and follow-through. Planned, ordered and actually delivered care must be separately represented.
6. **Quality/research team:** examine data completeness, delays, exceptions, adverse effects and outcomes under an appropriate study or audit plan. Preserve lineage from source to cohort to analysis.
7. **Evidence/review group:** consider findings alongside external evidence. Decide whether a signal warrants investigation or a new version. Never automatically promote a pattern observed in local data into a clinical protocol.

A senior expert can have protected research and protocol-development time, while remaining available for difficult cases, unresolved exceptions, mentorship and periodic audit. That arrangement is more defensible than the absolute promise that the best clinician will only do research. The amount of time saved remains unproven.

## Counterevidence and practical limits

NCI's evidence-methods page summarizes a comparison of 350 population-based observational treatment comparisons with 121 randomized trials. Only 40% agreed on treatment effects. It warns about selection, comparability and observational inference, including large datasets. This directly challenges a product claim that local outcome dashboards alone will discover the best therapy or SOP. The original PubMed page was cookie-blocked, so these numbers should be attributed to NCI's summary, not described as a directly reviewed original study. [NCI evidence methods](https://www.cancer.gov/publications/pdq/levels-evidence/treatment).

The lesson is not that observational data are useless. They can identify missing care, describe service patterns, generate hypotheses and support carefully designed studies. The software should show cohort construction, denominators, missingness, follow-up windows and possible confounding; claims of causal superiority need an appropriate study design and statistical/clinical review.

No primary oncology-AI failure case was verified in this bounded search. Do not include a Watson failure anecdote as if researched. Also unresolved: local SOP ownership, how often protocols change, current exception workload, available research staff, data access and whether evidence curation is the actual bottleneck.

## What to build first and how to test it

The first research feature should be an **evidence-to-protocol change record**, not autonomous protocol generation: citation → short appraisal → applicable patient group → proposed change → review comments → approval → published version. Pair it with a small source-linked dataset sufficient to answer one agreed service question (for example, why planned follow-up was missed).

Run a pilot on one service and one repeated workflow. Measure researcher/clinician time spent finding and verifying information, data completeness, unresolved exceptions, amendment-review turnaround and rework. Set target improvements after baseline measurement rather than inventing percentage benefits. An adverse result would be more documentation time, duplicate entry, low source trust, unused protocol versions or persistent missing outcome data. Those findings should change the scope before broader development.

## Search and access audit

- Substantive indexed search queries: 3, all in one discovery call after search-browser failures.
- Additional attempted browser queries: 3 (Google twice CAPTCHA; Bing returned unrelated results). Total query attempts: 6.
- Substantive queries: `site.asco.org clinical pathways criteria physician judgment multidisciplinary updating pathways`; `site.cancer.gov real world data randomized trials bias`; `site.icmr.gov.in national ethical guidelines retrospective clinical research ethics committee quality assurance`.
- Search result entries returned: 26. These are discovery entries, not 26 reviewed sources.
- Fully read primary source pages/documents: 4 (NCI PDQ overview, NCI evidence methods, NCI real-world-data program, ICMR 2019 PDF). Two additional ASCO primary pages were usable only as indexed search text.
- Cited URLs in this findings report: 5 (the four fully read sources plus ASCO Guidelines Assistant). The separate ASCO pathways source note is discovery-only and not needed for the core recommendation.
- Access failures: 2 Google CAPTCHA pages; 1 irrelevant Bing result set; 2 ASCO URLs HTTP 403; PubMed cookie block; ICMR institute page timeout; a second ICMR ethics PDF download triggered a browser-daemon crash. No claim relies on unread content from these failures.
- Browser isolation: cwd `/tmp/oncology-governance-research`, own daemon initially PID 14190. All actual page navigation/downloads used gstack browse. Indexed discovery used `web__run` after failures as agreed with parent.
- Source limitations are recorded individually under `sources/governance_*.md`. No patient data, product files, or persistent user memory were modified.
