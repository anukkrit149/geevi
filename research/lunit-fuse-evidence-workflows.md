# Lunit and Fuse: what their public workflows establish

Primary-source review, **11 October 2026**. Scope: the supplied Lunit precision-oncology/resources pages, linked product/resource pages, and Fuse's public product pages. This is a public-documentation comparison, not a product demo or independent performance audit. “Not documented” below means not established in the inspected material—not that the capability is absent.

## Main finding

**These companies cover different layers.** Lunit SCOPE produces tissue-image-derived research biomarkers. Fuse provides radiation-oncology documentation, intent/prescription and operational workflows. FuseRX already describes patient/disease-based pathway suggestions and access to related studies; that overlaps with the proposed evidence-to-plan workflow. Neither inspected site establishes the complete clinician-uploaded-literature → explicit patient eligibility assessment → contextual study results → signed multidisciplinary recommendation → medical-and-surgical execution chain. This is a limited comparison, not evidence of an empty market. [Lunit overview](https://www.lunit.io/en/precision-oncology/) · [FuseRX](https://www.fuseonc.com/rx)

## 1. Lunit: turn tissue images into quantitative research information

The precision-oncology portfolio is marketed primarily to biopharma, translational research and companion-diagnostic development teams. A companion diagnostic is a test developed to help identify appropriate use of a corresponding therapy. The reviewed SCOPE pages explicitly state **research use only, not for diagnostic procedures or decisions**. Development of a companion diagnostic is not itself an approved diagnostic intended use. Do not transfer regulatory status from Lunit's other radiology products to these SCOPE offerings. [Lunit precision oncology](https://www.lunit.io/en/precision-oncology/)

| Product | Publicly described input → processing → output | Relevant users and limit |
|---|---|---|
| **SCOPE IO** | H&E-stained tissue-slide images → cell/spatial analysis → tumour microenvironment features and immune phenotypes such as inflamed, excluded and desert | Research/biopharma biomarker development and immunotherapy-trial enrichment; RUO |
| **SCOPE IHC suite** | Immunohistochemistry slide images → expression quantification → uIHC, HER2 and PD-L1 analyses | Biomarker/companion-diagnostic development and pathologist-assistive research workflows; listed components RUO |
| **SCOPE GP** | H&E images → model inference → genotype probabilities and predicted-area visualization | Research prescreening/co-mutation discovery; predictions are not molecular-test confirmation; RUO |
| **SCOPE PD-L1** | Digitized IHC whole-slide images from fixed tissue → detection/classification → quantitative PD-L1 assessment | Research/pharma and digital pathology users; page names integrations with Aperio AI Store, HALO AP and Roche navify; RUO |

Sources: [IO](https://www.lunit.io/en/precision-oncology/scope-io/), [IHC suite](https://www.lunit.io/en/precision-oncology/scope-ihc-suite/), [GP](https://www.lunit.io/en/precision-oncology/scope-gp/), [PD-L1](https://www.lunit.io/en/precision-oncology/scope-ihc-suite/pd-l1-analysis/). These are vendor-described functions; integration availability still needs verification for a specific deployment.

The [resources library](https://www.lunit.io/en/resources/) separates screening and precision-oncology materials and provides brochures/demos. The inspected [SCOPE IO resource page](https://www.lunit.io/en/resource/one-pager/lunit-scope-io-one-pager/) reinforces research/biomarker-discovery use and the same RUO restriction. This library is product education, not evidence that clinicians can upload their own papers into a patient-specific reasoning workspace.

**Lesson for our system:** accept validated, appropriately authorized diagnostic outputs as source-linked patient evidence; distinguish an image-model prediction from a confirmed laboratory result. A correlation between a research biomarker and response does not independently establish that changing treatment based on the biomarker benefits a particular patient. The inspected pages do not document a cross-specialty prescribing, consent or medication/surgical delivery system.

## 2. Fuse: translate radiation-oncology information into workflow

### FuseDocs

Fuse describes document extraction/categorization, data from EMR and oncology information systems (OIS), and draft consultation/history-of-present-illness notes. It explicitly describes review and approval of data-driven notes, and approved-document upload to the OIS/EHR according to customer configuration. It names Aria, MOSAIQ and Epic as examples. [FuseDocs](https://www.fuseonc.com/docs)

This establishes a public **draft → review/approval → destination-system** workflow. It does not establish which credentials constitute a legally meaningful signature, what fields each professional approves, whether approvals bind an immutable version, or how later corrections invalidate downstream orders. The page's broad claims about audit readiness and error-free documentation are marketing language, not a published audit-control specification.

### FuseRX

FuseRX is explicitly a **radiation-oncology intent and prescribing platform**. It describes saving/reusing treatment pathways, tags/properties for search and recommendation by patient/disease characteristics, related guidelines and studies in the workflow, side-by-side treatment options, and integrated ACROPath pathways. Physicians can customize treatment intent, sites, prescriptions, sequence, simulation orders and dose goals, including organs-at-risk goals. [FuseRX](https://www.fuseonc.com/rx)

The important overlap is not merely summarization: Fuse publicly connects clinical information, pathway suggestions, evidence references and downstream radiation ordering. However, it does not publicly document full-text ingestion of arbitrary physician-supplied literature, explicit trial inclusion/exclusion matching with “unknown” states, extraction of comparators and endpoint uncertainty, or a complete signed evidence-packet history.

Its stated EHR/OIS/treatment-planning-system integration should be verified at the connector, field and direction level. A radiation prescription/intent is not proof that a technically approved treatment plan was generated or that a fraction was delivered.

### Other modules: several material qualifications

| Module | What the detailed page actually says | Implication |
|---|---|---|
| **FuseAuth** | **Currently in early development**; proposed payer/health-plan authorization, documentation, denials and appeals workflows | Do not portray as an established live feature or confuse payer authorization with clinical approval |
| **S!GNAL** | Charge/documentation discrepancy detection and actionable worklists; FAQ explicitly says it **does not write directly back to the OIS** | Flagging a problem and closing the source-system task are different operations |
| **FuseAnalytics** | Revenue, errors, treatment volumes/new starts, filtering and customizable dashboards; FAQ says **daily refresh**, configurable | Do not infer continuously live data from the “real-time” headline, or patient-outcome evidence from operational dashboards |

Sources: [Auth](https://www.fuseonc.com/auth), [S!GNAL](https://www.fuseonc.com/signal), [Analytics](https://www.fuseonc.com/analytics).

## 3. Comparison against the proposed workflow

This matrix summarizes the sources linked above. “Documented” means publicly described by the vendor, not independently tested.

| Required capability | Lunit SCOPE reviewed pages | Fuse reviewed pages | What our design must demonstrate |
|---|---|---|---|
| Clinician attaches own papers/protocols | Not documented | Guidelines/studies referenced in RX; arbitrary literature ingestion not documented | Versioned source intake and reviewer ownership |
| Patient information extraction | Slide-image features/probabilities | Docs extracts/categorizes records and generates notes | Verified clinical facts with specimen, date and provenance |
| Match evidence population to patient | Biomarker/trial enrichment focus | Patient/disease-tagged pathway recommendations | Explicit matched, mismatched and unknown eligibility criteria |
| Show previous results in context | Product research/publication references | Study references and strategy comparisons | Design, population, comparator, endpoint, follow-up, uncertainty, harms |
| Patient-specific recommendation | Research biomarker output, not diagnostic decisions | Physician-centered radiation intent and prescription suggestions | Explainable draft assessment with clinical review |
| Evidence-linked approval | Clinical signoff chain not documented | Note review/approval documented; detailed version/signature controls not documented | Who approved precisely what, when, with which evidence version |
| Medical oncology execution | Not documented | Not established; reviewed suite is radiation focused | Regimen orders, pharmacy/nursing verification, actual administration |
| Surgical oncology execution | Not documented | Not established | Operability/procedure decisions, perioperative checkpoints, specimen/results loop |
| Radiation execution | Not documented | Intent/orders/dose goals/integrations documented | Distinguish intent, technical plan approval, readiness and actual delivery |
| Family caregiver permissions | Not documented | Not documented in inspected pages | Scoped access, education and logistics; no implied prescribing authority |
| Outcome learning | Research analyses | Operational metrics; patient-level causal treatment-effect comparison not established | Explicit cohort definitions, missingness and confounding limits |

The credible hypothesis is therefore **a source-grounded, clinician-governed evidence-to-protocol workflow spanning care teams**, not simply “AI reads oncology PDFs.” Two websites cannot establish its commercial novelty or hospital willingness to adopt it.

## 4. Results need context, including vendor results

Lunit's PD-L1 page cites research on scoring, inter-reader agreement and reading time. FuseDocs cites an ACRO-presented documentation-accuracy result and a time-saving claim. This review did not inspect the original studies or validate their numeric estimates; they are **not treated as independently established effect sizes** here. A documentation-accuracy metric, biomarker discrimination metric and patient survival benefit answer different questions. [Lunit PD-L1 evidence links](https://www.lunit.io/en/precision-oncology/scope-ihc-suite/pd-l1-analysis/) · [FuseDocs](https://www.fuseonc.com/docs)

For our proposed evidence cards, require the study's population, setting, intervention, comparator, endpoint definition, sample size, follow-up, effect/uncertainty, harms and limitations. Keep trial results separate from the hospital's observational outcomes. A subgroup that resembles the patient is supporting context, not a validated individual probability of benefit. These are proposed requirements rather than vendor capabilities established by this review.

For surgical implementation, the [WHO checklist implementation manual page](https://www.who.int/publications/i/item/9789241598590) explicitly emphasizes multidisciplinary involvement, staff engagement, training, feedback and local adaptation. This supports involving the actual clinical roles in workflow design; it does not establish that a generic digital approval button fulfills surgical safety checks. Detailed operative checkpoints should be verified with the hospital's approved policy.

## 5. Concrete questions for vendor demonstrations

1. Upload a clinician-selected paper: can the system retain its exact version and extract population, comparator, outcomes and limitations with source locations?
2. Change a patient's biomarker from pending to confirmed: which evidence matches and approvals change, and is the reason visible?
3. Show a patient outside the study eligibility criteria: does the interface expose the mismatch rather than silently generalize?
4. Compare overall survival, response and toxicity without combining unlike endpoints or uncontrolled cohorts into one score.
5. Approve a recommendation, amend a source report, and show who must review the change. Are signatures attached to immutable versions?
6. Demonstrate read/write interfaces separately, including failure handling. For S!GNAL, who closes work in the OIS? For Analytics, what is the configured freshness?
7. Show general availability versus development status, especially FuseAuth.
8. Show a real medical-oncology and surgical-oncology pathway, not a radiation template relabeled for another service.
9. Demonstrate family access, patient consent and professional signoff as separate permissions/actions.
10. For any proposed Lunit input, provide the exact product/version, intended-use label, validation population and applicable local authorization. Do not substitute another product's approval.

## Source and access notes

All links were inspected on **11 October 2026** using gstack browse. No registration, demo request or vendor contact was submitted. The IO one-pager landing page was read; its downloadable PDF did not provide extractable text and is not used for additional claims. WHO's checklist download returned HTML, so only the accessible manual landing page supports the limited implementation statement above. No public page was treated as proof of Indian regulatory authorization, current pricing or a hospital-specific deployment.
