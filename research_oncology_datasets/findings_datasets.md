# Oncology datasets for realistic reports and patient data

Prepared 11 October 2026. Scope: data research and planning only. No app code, fixtures or tests changed.

## Recommendation

Use **three separate inputs**: real public documents for report structure; AML research metadata for realistic specimen/biomarker/outcome fields; explicitly synthetic records for the continuous care workflow. Later, validate that workflow with hospital-authorized records. The bounded search did not find one open dataset containing all these layers together.

Two small, inspectable resources are now saved: a real [lung pathology PDF](samples/solid-tumor_TCGA-44-6147_pathology.pdf) and the [BeatAML2.0 clinical workbook](samples/BeatAML2_research-specimen-clinical.xlsx). Their [provenance, checksums and terms](samples/README.md) are recorded. They are unrelated datasets and must never be combined into one patient.

## What each source can realistically provide

| Source | What is available / patient linkage | Reports, time and formats | Access and product-use limits | Recommended use |
|---|---|---|---|---|
| GDC TCGA pathology files | Actual released pathology documents; inspected files include case identifiers | PDF; one inspected two-page lung report has multiple specimens and report sections. Historical source document, not a full timeline | The inspected file is open. GDC/NIH data policy applies; no per-file CC licence displayed | Start here for authentic document structure, redaction handling, source anchoring and extraction review |
| TCGA-LAML in GDC | Case, diagnosis, demographic, biospecimen and some treatment/follow-up metadata; stable case/sample IDs | JSON/TSV API; TCGA supplemental data also uses XML/tab-delimited files. Timing is sparse and relative. Genomic file access varies | Public metadata can be inspected without login; raw/identifying genomic data can be controlled | Test case/specimen hierarchy, unknowns and coded assertions. Do not expect serial clinical reports |
| BeatAML2.0 workbook | Actual specimen-level research data linked through subject and DNA/RNA sample IDs | XLSX with dictionary; collection-day offsets and some repeated specimens, laboratory/phenotype/molecular fields, summary treatments and outcomes | Repository CC BY 4.0, attribution/change notices needed. No workbook exclusion observed | Best inspected AML field reference for the present prototype; not a drug-selection engine or event-by-event EHR |
| TCIA CMB-AML | AML radiology and pathology imaging, specimen metadata; explicit temporal alignment design | DICOM, SVS, JSON; day offsets from registration. Open clinical subset linked through CTDC; full clinical data controlled | Some imagery CC BY 4.0; reconstructable head images and complete clinical data controlled | Future multimodal/longitudinal reference after a small case-level feasibility check |
| TCIA TCGA-KIRC | Matched TCGA/TCIA patient IDs, imaging plus external clinical/genomic links | CT/MR/CR DICOM; some serial studies. Shifted imaging dates differ from TCGA diagnosis-relative dates | CC BY 3.0 for listed image data; collection citation and policy required | Optional solid-tumour imaging integration reference; not a source of verified narrative radiology reports |

Sources: [GDC inspected PDF metadata](https://api.gdc.cancer.gov/files/709e6425-3cfe-4f28-b97b-edaaa6aa257a?expand=cases.project&pretty=true), [GDC API](https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/), [TCGA supplements](https://gdc.cancer.gov/content/where-can-i-find-clinical-data-elements-specific-my-cancer-research-interest), [Beat AML repository](https://github.com/biodev/beataml2.0_data), [CMB-AML, DOI 10.7937/pcte-6m66](https://doi.org/10.7937/pcte-6m66), [TCGA-KIRC, DOI 10.7937/K9/TCIA.2016.V6PBVTDR](https://doi.org/10.7937/K9/TCIA.2016.V6PBVTDR).

## Concrete report inspected today

The saved PDF is file UUID `709e6425-3cfe-4f28-b97b-edaaa6aa257a`, case `TCGA-44-6147`, project **TCGA-LUAD**. GDC labels it a released, open pathology report. Its 23,130-byte file has two pages; both were read and visually reviewed. Its original redactions remain intact.

It contains separately labelled specimens A–E, clinical context, a frozen-section result, gross descriptions, a block summary, microscopic findings and specimen-specific final diagnoses. In one part, the report says “None definitively identified” for regional lymph nodes. This should not be silently converted to a negative node result. The document mixes different kinds of findings and uncertainty at different specimen levels. [Original PDF](https://api.gdc.cancer.gov/data/709e6425-3cfe-4f28-b97b-edaaa6aa257a)

Proposed report-model consequences:

- Represent a document independently of the patient summary, with version, source, author/date status when known, pages, extraction method and review status.
- Represent specimens and sections explicitly; attach each assertion to its specimen and source location.
- Preserve not-assessed, not-identified, negative, positive, indeterminate, missing and redacted as different states.
- Keep reported classification/stage wording and its source context; do not reinterpret a historical report using current definitions without a clinician-reviewed transformation.
- Allow an interim result, final report and later addendum to be related, rather than overwriting earlier evidence.

These are design recommendations inferred from the inspected structure. The PDF is useful for layout and provenance; it is **not AML** and cannot validate an AML clinical extraction schema.

## AML reality check

### TCGA-LAML

A live project-filtered GDC query returned 200 cases. The inspected case `TCGA-AB-2810` has multiple biospecimen entities, relative follow-up information and many missing fields. Some follow-up objects contain only IDs. Some treatment entries explicitly say treatment was not given. Database creation/update timestamps must not become clinical event dates.

The exact project-plus-Pathology-Report query returned **zero** on 11 October 2026. That is a scoped retrieval result, not proof that no AML reports exist elsewhere. The unfiltered pathology query returned 11,324 files and gave three open PDF records with case links; those results do not establish report availability for every project. [LAML query](https://api.gdc.cancer.gov/files?filters=%7B%22op%22%3A%22and%22%2C%22content%22%3A%5B%7B%22op%22%3A%22%3D%22%2C%22content%22%3A%7B%22field%22%3A%22cases.project.project_id%22%2C%22value%22%3A%22TCGA-LAML%22%7D%7D%2C%7B%22op%22%3A%22%3D%22%2C%22content%22%3A%7B%22field%22%3A%22files.data_type%22%2C%22value%22%3A%22Pathology%20Report%22%7D%7D%5D%7D&fields=file_id,file_name,data_format,access,file_size,cases.submitter_id,cases.case_id&size=3&pretty=true), [all pathology query](https://api.gdc.cancer.gov/files?filters=%7B%22op%22%3A%22%3D%22%2C%22content%22%3A%7B%22field%22%3A%22files.data_type%22%2C%22value%22%3A%22Pathology%20Report%22%7D%7D&fields=file_id,file_name,data_format,access,file_size,cases.submitter_id,cases.case_id&size=3&pretty=true), [inspected case query](https://api.gdc.cancer.gov/cases?filters=%7B%22op%22%3A%22%3D%22%2C%22content%22%3A%7B%22field%22%3A%22project.project_id%22%2C%22value%22%3A%22TCGA-LAML%22%7D%7D&fields=case_id,submitter_id,project.project_id,demographic,diagnoses,follow_ups,samples&expand=demographic,diagnoses,diagnoses.treatments,follow_ups,samples&size=1&pretty=true).

### BeatAML2.0

The workbook provides a substantially richer AML schema. The inspected copy contains 942 specimen-level records, 95 columns and 805 distinct subject IDs; 108 subject IDs occur on multiple rows. Its dictionary and metadata sheets are essential, because the labels alone are easy to misread. [Workbook and dictionary](https://github.com/biodev/beataml2.0_data/blob/main/beataml_wv1to4_clinical.xlsx)

| Field group observed | Examples | Design implication |
|---|---|---|
| Linkage | subject ID, DNA sample ID, RNA sample ID | Patient and specimen are separate entities; no invented cross-study linkage |
| Disease context | diagnosis at inclusion/acquisition, relapse status, disease stage at collection, historical ELN2017 field | Findings need a timepoint and classification context |
| Specimen/timing | specimen type, collection offset relative to earliest specimen | Preserve the anchor and offset; do not invent absolute dates |
| Laboratory and morphology | blood/marrow blast percentages, blood counts, chemistry, morphology | Store units and specimen context; dictionary and collection window travel with values |
| Pathology/molecular | immunophenotype text, karyotype, cytogenetics, molecular markers, variant summary | Multiline source assertions should not become unexplained patient-wide badges |
| Care/outcome summaries | cumulative regimen list, most recent regimen, induction response, vital status, survival interval | A summary is not a sequence of administered treatments or visits |

The first two inspected records share a subject ID but have different specimen IDs and different relative collection offsets. That is genuine within-dataset longitudinal information. It does not supply the intervening encounters. The dictionary explicitly says cumulative regimen-list ordering “has no importance”. Therefore do not infer therapy sequence from pipe-delimited list position.

The metadata also specifies different ascertainment windows for laboratory/pathology categories. Some outcome/duration fields use sentinel values and some classification fields are historical. Preserve these meanings in any future import; do not normalize them to zero, normal or current clinical truth.

## Imaging is not a narrative report

TCIA CMB-AML is a useful later option because it explicitly aligns scans through registration-relative day offsets. Version 9 lists 16 total subjects, but open radiology, controlled head images and pathology have distinct membership and access. Its complete clinical data is controlled; only a clinical subset is labelled open. The CTDC link loaded a site shell/warning in this run, so its case content was not inspected. [CMB-AML collection](https://www.cancerimagingarchive.net/collection/cmb-aml/)

The inspected TCIA download tables advertise image/metadata formats, not signed narrative radiology-report PDFs. This bounded search did not verify a public cancer radiology-report corpus suitable for our exact workflow. Do not call an image, image annotation, derived caption or generated description an authentic clinical report.

For TCGA-linked imaging, shared patient IDs support linkage, but the collection documentation warns that TCIA shifted image dates and TCGA diagnosis-relative clinical dates use different systems. Keep their anchors explicit until reconciliation is demonstrable. [TCGA-KIRC collection](https://www.cancerimagingarchive.net/collection/tcga-kirc/)

## What should remain explicitly synthetic or require hospital-authorized data

The inspected sources do not establish a continuous operational chart with referral reason, appointments, consent conversations, patient goals, affordability/travel concerns, serial orders/results, actual administrations, adverse-event responses, nursing actions, multidisciplinary deliberation, protocol-version selection, signed exceptions, tasks and SOP-change approvals.

Proposed strategy:

1. Use the saved public pathology report to design document/specimen/source review.
2. Use a deliberately small, versioned Beat AML subset to test schema and missingness. Keep its research provenance visible and preserve dictionaries.
3. Author a **clearly synthetic** AML journey for operational states and exceptions, informed by clinicians. Do not append fabricated events to a real research subject and present them as real.
4. Use standards/templates from the separate document-structure research strand for field organization; distinguish them from observed source data.
5. Validate with a locally authorized sample of real hospital documents and staff workflow before claiming report coverage or care-workflow realism.

A useful future acquisition manifest should include source URL, dataset/version, downloaded file UUID or immutable commit, checksum, access category, licence/policy, attribution, synthetic/real status, subject/specimen IDs, date anchor, de-identification transformation and restrictions. Missing permissions or missing fields remain explicit.

## Reuse and product boundaries

GDC open access still requires NIH data-policy compliance and acknowledgement. It does not itself label each file CC BY. TCIA licences are collection/subset-specific; its policy explicitly distinguishes restricted data, and mirroring through another tool has additional attribution requirements. Beat AML's inspected repository carries CC BY 4.0 with no workbook exclusion observed. These data terms differ from the copyright licence of an associated journal article. [GDC policy](https://gdc.cancer.gov/access-data/data-access-policies), [TCIA policy](https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/), [Beat AML licence](https://github.com/biodev/beataml2.0_data/blob/main/LICENSE.txt).

No repository licence establishes clinical validity or authorizes attempts to identify participants. Public exploratory inspection is complete; production redistribution, training or deployment should use an explicitly recorded intended-use assessment.

## Audit and limits

- Five substantive indexed search queries, sent in two calls; 59 result entries returned before deduplication, including irrelevant results. No social-media patient reports were used.
- Query 1: `site.gdc.cancer.gov pathology reports PDF TCGA clinical supplement open access`
- Query 2: `site.cancerimagingarchive.net radiology reports pathology reports collection TCGA LAML`
- Query 3: `Beat AML Vizome clinical data download data use terms`
- Query 4: `site.cancerimagingarchive.net collection radiology reports TCGA-RCC kidney pathology reports`
- Query 5: `"Beat AML" "data" "download" "2022"`
- Fourteen substantive primary source pages/API result views were inspected (thirteen in the browser and one by read-only fallback), plus the original PDF and clinical workbook; CTDC reached only a site shell and was not counted as a clinical-data inspection. Seven source-note groups consolidate dataset and policy evidence. Page-view count excludes repeated navigation, licence download and DOI access pointers.
- Browser isolation: /tmp/oncology-clinical-research, new daemon PID 26963. GDC AI page timed out; read-only fetch fallback retrieved it. A late completion subsequently produced one URL/content mismatch during GitHub navigation; that output was excluded and the GitHub history was reloaded with URL verification.
- The initial case query included four group names in `fields` that the API warned were unrecognized; corresponding `expand` groups returned the inspected data. This warning was retained in interpretation, and no completeness claim is made.
- Local extraction/rendering: initial pdftotext path absent; pypdf worked. Optional pymupdf unavailable; installed pdftoppm then rendered both pages. A fontconfig warning did not prevent readable output, which was visually checked.
- Download boundary: one 23KB PDF, one 477KiB workbook and its licence only. No controlled access, credential entry, bulk image/sequence download, or data-use application. The first licence save path was rejected by browse's safe-directory rule; download succeeded under /tmp and was then copied to the authorized research samples folder.
- No GENIE assessment included; it was optional and the five-query budget was used for directly relevant sources. The search is bounded, not an exhaustive proof of absence.
