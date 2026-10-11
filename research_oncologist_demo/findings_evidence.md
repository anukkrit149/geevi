# Verified AML evidence for the oncologist demonstration

Verified on 11 October 2026. Three attributed evidence briefs are ready in [evidence-catalog.json](evidence-catalog.json). These are original Geevi summaries of published sources, not original publications or a current comprehensive guideline review. No real research participant data or copyrighted full papers were downloaded.

## What an oncologist would investigate

The demonstration should begin with a clinical question, not with a library of approved answers. For a newly diagnosed fictional AML case, three distinct questions make the workflow understandable:

1. **What do we know about this case, and what is unresolved?** Use the ELN source to explain why diagnosis, classification, molecular information and response-assessment context need attributable documentation. The source does not fill in missing patient facts.
2. **Does a published clinical comparison apply to this particular situation?** Use VIALE-A to demonstrate population, comparator, benefit, harm, limitations and a clinician's applicability judgment. A fitness assessment and treatment history cannot be inferred from an AML label.
3. **What could a departmental research project study, and what data would it need?** Use Beat AML to demonstrate patient–specimen–assay–analysis relationships and separate laboratory research measurements from clinical decisions.

These three source types must retain different roles. An expert recommendation, a randomized trial and a functional-genomic cohort do not have interchangeable evidence strength or clinical meaning.

## Sources and verification

| Brief | Primary source verified | Purpose in the demonstration | Access/reuse boundary |
|---|---|---|---|
| ELN 2022 | [Döhner et al., Blood; PubMed record](https://pubmed.ncbi.nlm.nih.gov/35797463/), DOI 10.1182/blood.2022016867, journal issue date 22 September 2022 | Record the assessment framework, unresolved molecular information and the question being discussed | Abstract verified. Publisher returned a 403 security challenge. Free-to-read status does not establish unrestricted reuse; cite/link and keep the Geevi brief separate. |
| VIALE-A | [DiNardo et al., NEJM; PubMed record](https://pubmed.ncbi.nlm.nih.gov/32786187/), DOI 10.1056/NEJMoa2012971, 13 August 2020; [trial record NCT02993523](https://clinicaltrials.gov/study/NCT02993523) | Appraise benefits and harms in a defined population, then document the patient's applicability and uncertainty | Abstract and browser-accessible registry API verified. The journal copyright belongs to Massachusetts Medical Society; no article/PDF redistribution license verified. |
| Beat AML 2018 | [Tyner et al., Nature](https://www.nature.com/articles/s41586-018-0623-z), 17 October 2018; [original dbGaP accession](https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs001657.v1.p1); [Vizome additional files](https://www.vizome.org/additional_figures_BeatAML.html) | Explain linked research data and assay provenance | Abstract and data-availability text accessible, full paper subscription-only in this pass. dbGaP individual data require authorized access; public metadata are a separate lane. No unrestricted redistribution license verified. |

Short source excerpts illustrating their different roles:

- ELN abstract: “revised ELN genetic risk classification, revised response criteria.”
- VIALE-A abstract defines patients as “ineligible for intensive chemotherapy.”
- Beat AML describes “ex vivo drug sensitivity.”

The catalog contains an original, bounded summary of the research findings and appraisal prompts. It omits dosing instructions and does not turn any paper into a treatment recommendation.

## Provenance and contradictions to preserve

The original VIALE-A 2020 analysis includes 431 patients. The current registry lists 443 actual enrollment and a later 2021 data cutoff. The trial record was last updated on11 June2026 and was active, not recruiting, when accessed. Keep the original publication analysis distinct from registry versions; this research did not establish the reason for the denominator difference. Do not advertise this record as an open trial for the fictional patient.

The Beat AML 2018 paper describes 672 specimens from 562 patients. Its original dbGaP record lists 583 consented subjects and marks that release superseded, linking to phs001657.v3.p1. These are different populations/releases, not numbers to harmonize silently. A research model needs both patient and specimen identifiers, collection/assay dates, data-release identifiers and analysis denominators.

The ELN source is dated 2022. This pack is foundational demonstration material, not proof that the latest recommendations or all relevant 2026 evidence have been reviewed. The publisher's blocked full text limits this pass to citation and abstract scope.

## Replacement structure

Replace invented research audits with visibly attributed **evidence briefs**. Each imported brief should show its real citation, publication date, source type, original-source link, review date, access status and an explicit note that it is a Geevi summary. A research dossier should then contain:

- The investigator's question and intended decision or research use.
- Search terms and search/review date, including what sources have and have not been examined.
- Source-specific population, comparison, outcomes, findings and limitations.
- Patient applicability: relevant facts, missing inputs, assumptions and the clinician's judgment.
- Independent appraisal, objections and disposition.
- A separate draft departmental protocol or research proposal, with accountable owner, scope, approval and next review date.

Do not pre-approve a clinical recommendation simply because a source is real. A demo can demonstrate review actions under named fictional accounts while showing that professional validation and institutional adoption remain pending.

Synthetic patient PDFs/scans serve a different purpose: testing source verification and case readiness. They should remain clearly fictional, separately labeled and outside this public-evidence pack. Replacing patient reports with published papers would erase the patient-versus-evidence distinction and make the clinical workflow less coherent.

## Dataset structure

Beat AML is an appropriate reference for designing research tables, but it is not a drop-in dataset for routine care or a substitute for individual patient reports. A first model can use separate entities for:

| Entity | Key information |
|---|---|
| Research cohort/release | Study/accession, publication, data release, approved use and access conditions |
| Research participant | Coded research identifier, cohort membership and consent/use restrictions |
| Specimen | Participant link, collection time, tissue/source, baseline/follow-up context |
| Assay | Method, platform, quality information, assay run and result version |
| Molecular result | Variant/expression measurement, reference system, assay provenance |
| Ex vivo result | Compound, assay conditions, response metric and quality status |
| Clinical annotation | Definition, time point, source and missingness |
| Analysis | Cohort selection, denominator, code/version, endpoint, limitations |

For a demonstration, use the published metadata and original synthetic examples of this structure. Before importing real rows, inspect the release dictionary and required data-use terms. Do not assume that every participant has every assay or that laboratory sensitivity is a validated clinical outcome.

## Research method and limits

Three targeted searches were used: a Google ELN query (blocked by a CAPTCHA, not bypassed), a PubMed ELN query, and a PubMed Beat AML title query. The Beat AML search did not yield the main article, so its known DOI was verified directly on the publisher site. VIALE-A was verified directly through its PubMed record and linked trial identifier. Reading was confined to primary publication records, publisher text and the named trial/data repositories.

No external article PDFs, clinical protocols, dataset rows or credentials were copied into the repository. Full-text critical appraisal, a current systematic search and professional oncology review remain separate work. The strongest immediate use of this pack is demonstrating evidence traceability and accountable departmental review.
