# Report structure and longitudinal data recommendations

Prepared 11 October 2026. Planning/research only; application files, fixtures and tests unchanged. This strand did not repeat the app audit. Recommendations target the simplified patient-summary/report model described in the research plan and require reconciliation with the parent agent's implementation audit.

## Decision

Use **published mCODE 4.0.0 plus its FHIR R4 foundations** as a structural reference, and use **explicitly synthetic, clinician-authored AML scenarios** for the first complete workflow. Add a small Synthea record set later for general longitudinal import mechanics. Authentic reports and AML research datasets should be additional, separately labelled evaluation sources. None of these sources alone provides a complete department journey, a clinical-rule engine and a reusable real-report corpus.

mCODE itself says it does not specify what must be collected for every patient; it specifies how supported concepts are represented when shared. Its current published release is 4.0.0 STU4, generated February 16, 2025, based on FHIR R4/4.0.1. This is a strong interoperability reference, not a disease-specific clinical checklist or automatic claim that our product is conformant. [mCODE](https://hl7.org/fhir/us/mcode/)

## What is actually available

| Source | Kind | What was verified | Access / licence | Use here | Do not assume |
|---|---|---|---|---|---|
| mCODE 4.0.0 and genomics examples | Published schema plus authored example resources | An actual example report JSON references request, patient, lab, interpreter, two specimens and many observations | Public pages; FHIR spec CC0 with third-party terminology exclusions; mCODE package-specific licence not separately inspected | Report/observation/specimen boundaries and exchange mapping | Real patients, full AML clinical accuracy, required workup or complete department workflow |
| CAP myeloid protocol 1.1.0.2, Sep 2026 | Disease-appropriate reporting template | Covers AML, marrow/blood/other sites, integrated diagnosis, morphology, flow and genetic studies | Public to read; substantial commercial, database/electronic and AI incorporation restricted by published terms | Reference discussion with hematopathologist; version-aware reporting coverage | Free-to-embed template or authentic patient report |
| Synthea | Synthetic longitudinal records and generator | Encounters, labs, conditions, medications, procedures, care plans; current sample links; oncology link identifies breast cancer | Generator Apache 2.0; official download page says synthetic data can be used without restriction and asks citation | Import mechanics and timeline testing; optional scaffold for synthetic histories | Clinically validated AML rules or real report diversity |
| MIMIC-IV Demo v2.2 | Real deidentified relational sample | 100 patients, public file listing, hospital/ICU tables, excludes clinical notes | ODbL v1.0; public | Optional real event/relationship example | Note corpus, AML cohort, outpatient oncology journey |
| MIMIC-IV-Note v2.2 | Real deidentified clinical notes | Official docs list discharge/radiology tables and linkage; raw notes not inspected | Credentialed access, training and data-use agreement; indexed metadata identifies credentialed licence 1.5.0 | Later approved text-extraction benchmark | Open downloadable notes, broad product redistribution permission or AML pathology reports |

[mCODE genomics examples](https://hl7.org/fhir/us/mcode/examples_genomics.html), [CAP current protocols and terms](https://www.cap.org/protocols-and-guidelines/cancer-protocols/current-cancer-protocols/), [Synthea downloads](https://synthetichealth.github.io/downloads.html), [MIMIC Demo](https://physionet.org/content/mimic-iv-demo/2.2/), [MIMIC Note documentation](https://mimic.mit.edu/docs/iv/modules/note/).

## Core model: preserve what the report actually says

The model below is a proposed internal structure with conceptual FHIR mappings, not a requirement to store raw FHIR resources as the application database.

| Object | Minimum useful information | Important relationships |
|---|---|---|
| Source document / document version | Original bytes or secured location, MIME type, digest, source organization, external identifier, author, authored/received/imported dates, page count, revision relationship, access basis | One document may carry several clinical reports; one report may have original and addendum documents. Never replace source bytes with an AI summary |
| Diagnostic report / report version | Accession and issuing lab, type, source status, clinical effective date, issue date, responsible interpreter, narrative conclusion, attachment references | Request, encounter, patient, one or more specimens, result observations; explicit amended/corrected/retracted relationships |
| Specimen | Accession, material, collection site and time, received time, collection method, adequacy/condition, parent specimen where present | Patient and collection event; several tests can use one sample; repeated samples stay separate |
| Observation / panel | Test code and original name; typed original value; normalized value/unit where justified; method; range; interpretation; result status; effective time; source location | Report, specimen, panel membership, prior observations and derivation provenance; preserve units and raw text |
| Clinical assertion | Diagnosis or classification stated by a qualified author; assertion date, applicable disease episode, source, certainty, classification/criteria version if given | Supporting observations and reports; a molecular finding is not itself the entire diagnosis |
| Care event | Event type, encounter, planned time, actual time, owner, status, relevant order or administration details | Longitudinal disease episode, care plan, patient-specific decision, follow-up |
| Provenance and review | Extractor/version, source page/span, transformation, confidence where calibrated, reviewer, review scope, timestamp and immutable decision history | Individual observation/assertion/report version; source status and local review status are separate |

FHIR explicitly says a DiagnosticReport is not intended to provide cumulative historical results. The patient timeline is a projection over repeated reports, observations, specimens, decisions and actual care events. A current summary is also a projection that points back to the evidence/version used to produce it. [DiagnosticReport](https://hl7.org/fhir/R4/diagnosticreport.html)

FHIR Observation supports typed values, missing-result reasons, reference ranges, methods, components and source derivation. DocumentReference distinguishes document metadata/provenance and replacement relationships; Specimen separates collection and processing history. Use these concepts to avoid collapsing evidence into six timeless fields. [Observation](https://hl7.org/fhir/R4/observation.html), [Specimen](https://hl7.org/fhir/R4/specimen.html), [DocumentReference](https://hl7.org/fhir/R4/documentreference.html).

## AML-specific corrections to the planning model

1. **A gene is not a Boolean.** Preserve the reported variant/fusion, assay or panel and tested scope, specimen, result date, quantitative measurement if supplied, lab interpretation and limitations. Separate a raw variant finding from a clinician's diagnostic or therapeutic implication. The public mCODE example models those as different observations; it is not an AML decision rule.
2. **Blood and marrow findings are not interchangeable.** Preserve material and collection event on each measurement. Repeated marrow or blood tests must not overwrite a single patient field.
3. **Missing is not negative.** Distinguish ordered/pending, not performed, unavailable document, insufficient/unsatisfactory sample, uninterpretable result, not detected within the reported assay scope, and unreviewed extraction. Exact vocabulary and mappings require clinical/lab agreement.
4. **Source-final does not mean locally reviewed.** A final lab report can contain unverified extracted facts; a clinician may review a preliminary result. Model both states separately.
5. **Keep time axes separate.** Collection/effective time, report issue time, arrival/import time and review time differ. Late reports and addenda must appear in the proper clinical sequence without rewriting history.
6. **Keep clinical classifications versioned and attributable.** If a report or clinician states a disease class, risk category or response, store its framework/edition, time point, author and supporting facts. Do not invent thresholds or recalculate categories from an incomplete summary.
7. **Amendments need dependency tracking.** A corrected laboratory observation should identify exactly which current summary, readiness decision, eligibility assessment or patient plan depends on it; reopen affected reviews. Unrelated verified facts should remain verified. This is a product requirement inferred from the need to handle revised/retracted reports, not a FHIR-specified UI rule.
8. **Separate the proposed plan from delivered treatment.** A protocol, a patient-selected plan, an order and an administration are different events. Research cohorts need the treatment actually received, its timing, interruptions and available outcome observations.

## Report and document families to design for

Candidate coverage for the clinical team's review—not a claim that every patient needs every test:

| Family | Data that the system should be capable of preserving |
|---|---|
| Complete blood count / differential and blood-film report | Individual measurements with units/ranges/time; morphology narrative; specimen and source |
| Bone-marrow aspirate / core / integrated hematopathology | Sample identities and adequacy; morphology and reported quantitative findings; integrated interpretation and addenda |
| Flow-cytometry report | Sample, panel/method, reported populations and interpretation, sensitivity/limitations when stated |
| Cytogenetics / karyotype / FISH | Exact reported result and tested targets, specimen, status, laboratory interpretation; do not flatten all into one genetic flag |
| Molecular assay / next-generation sequencing | Test scope, variants/fusions and quantitative fields as actually reported, interpretation and limitations |
| Residual-disease or response assessment | Method, specimen, time point, reported result, assay sensitivity if provided, and clinician interpretation; no invented schedule or cutoff |
| Chemistry, organ function, microbiology and other supporting tests | Repeated observations and panels; relevance to a decision is clinician-owned |
| Imaging and procedure reports | Narrative findings/conclusion and linked study/procedure; not raw image interpretation generated by this plan |
| Consultation, admission, discharge and follow-up notes | Authored narrative with encounter, assessment, plan and follow-up; represent as clinical documents rather than pretending every note is a diagnostic lab report |
| Treatment and supportive-care records | Orders, administrations, holds/changes, adverse-event observations and actual follow-through |

The current CAP myeloid template supports the distinction between integrated diagnosis and ancillary studies. The plan must not reproduce its proprietary field dictionary or clinical classification list. Independently authored local schemas can be reviewed against clinical needs; exact CAP incorporation needs appropriate rights. [Current myeloid reporting reference](https://www.cap.org/wp-content/uploads/2026/09/Heme.Myeloid_Mixed_Amb.Bx_.Res_1.1.0.2.REL_CAPCP.pdf?download=true).

## Staged acquisition and evaluation plan

1. **Now, without patient-data access:** map the conceptual model to mCODE/FHIR; inspect public JSON examples; draft an independently authored report envelope and typed observation design. Pin versions and document terminology choices. Do not claim conformance until profiles and exchanges are validated.
2. **Clinician-authored synthetic AML journey:** create scenarios only in a future authorized implementation phase. Include repeated samples, delayed results, contradictory reports, an addendum, insufficient material, a protocol exception, missed follow-up and recorded actual treatment. Clearly label all material synthetic and record clinical review. Avoid deriving patient-specific clinical facts by joining unrelated datasets.
3. **Small synthetic longitudinal import:** use a pinned, small Synthea sample or generate a small set with recorded seed/module version. Use it to test identity, event ordering and references; do not use it as AML medical ground truth. Public downloads already identify an oncology collection, but it is breast cancer and raw files were not validated here.
4. **Authentic report evaluation:** acquire a deliberately small, approved local deidentified set covering the above families, native PDFs/scans and addenda. Before intake, define permitted use, access, retention and whether external processing is allowed. Compare extracted values with adjudicated annotations; don't evaluate only whether the summary sounds plausible.
5. **Optional external benchmarks:** MIMIC Demo for real structured event relationships; MIMIC Note only after proper access and only for suitable note tasks. These sources do not replace AML-specific report validation or local workflow observation.

Acceptance dimensions should include patient/specimen matching, report version retention, exact value/unit extraction, negation and missingness, source citation accuracy, chronology, handling amendments, and separation of clinical facts from unapproved interpretations. Clinical thresholds, assay equivalence, classification edition, acceptable completeness and escalation rules remain owned by the oncology service.

## Audit and limits

- Five substantive indexed discovery queries, in two calls; no further search queries.
- Queries: official mCODE published guide/examples; official Synthea oncology/modules/licence; MIMIC-IV-Note/Demo access; CAP leukemia/bone-marrow reporting; mCODE 4.0.0 genomics/specimens.
- Search result entries: 37 in the first combined response; second response was output-truncated, so its total is not asserted. Search entries are not reviewed sources.
- Browser isolation: `/tmp/oncology-governance-research`, fresh daemon initially PID 25894. All main page inspection used gstack; read-only web fetch was used for PhysioNet/MIMIC documentation after access problems.
- Source reading: mCODE landing, genomics index, example narrative and JSON; four FHIR resource pages plus licence; Synthea downloads, repository and sample repository; CAP current listing/terms and five selected PDF pages; MIMIC access guide. MIMIC Note docs and Demo full page were read by web fallback. Old CAP guideline and Note exact licence label remained indexed-discovery only.
- Access failures: PhysioNet Note page timed out twice in gstack and twice in web fetch. An attempted mCODE ImplementationGuide JSON-rendering URL returned HTTP 300 and did not verify a package licence. No raw MIMIC data or Synthea archives inspected. Single CAP reference PDF was the only downloaded document (440 KB); local extraction succeeded after selecting the existing Python environment with pypdf.
- No accounts, agreements, full datasets or data-use permissions were requested/accepted. ICCR was not separately investigated because a current, AML-appropriate CAP reference was found within the five-query budget.
- Recommendation strength: strong for data-model boundaries and access distinctions; unproven for local adoption and AML clinical realism. No medical rules or thresholds were generated.
