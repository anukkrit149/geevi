# AI-assisted oncology intake: review format and validation boundaries

Reviewed 11 October 2026. Primary sources checked with gstack browse. This note informs a clinician-review prototype; it does not establish clinical accuracy, diagnostic performance, or regulatory suitability.

## What AI should prepare

The initial product should prepare a source-linked draft patient profile: what each report says, where it says it, what is missing, and which statements conflict. Extracting “the pathology report states AML” is different from independently establishing that the patient has AML. The clinician must interpret the report alongside the wider record. This is a product boundary, not a claim that source extraction is risk-free.

CAP/ASH's initial acute leukemia workup guideline addresses clinical information, specimen types, tests and reporting together. Its referral guidance includes the medical record, pathology slides, flow cytometry data, cytogenetic/genetic results and a list of pending studies. This supports an intake workspace that preserves sources and outstanding work rather than reducing the case to a diagnosis label and a handful of biomarkers. The CAP page identifies the guideline as originally published in 2017 and currently “Research and Review”; use it for workflow context, not as a current complete biomarker-ordering checklist. [CAP guideline](https://www.cap.org/cap-guidelines/initial-diagnostic-workup-of-acute-leukemia/)

Proposed profile field format:

| Element | What the reviewer needs |
|---|---|
| Reported finding | Exact wording plus a separate proposed structured value |
| Provenance | File, page, quote and actual source region; specimen identifier, collection/report date and reporting laboratory when present |
| Biomarker context | Test/method, variant as written, result, unit, assay limitation and interpretation when reported; preserve not detected, indeterminate and not tested as distinct states |
| Temporal context | Current versus historical result; preserve amended reports and disagreements |
| Review state | Proposed, verified, corrected, rejected, needs specialist review; actor, time and reason |
| Missing information | “Not found in supplied documents” versus a clinician-defined requirement; owner and next action |

These fields are proposed implementation requirements derived from the diagnostic workflow. They are not asserted to be a complete CAP-required data schema.

## What precise image review means

DICOM defines the exchange formats for medical images and related information, with the data and quality required for clinical use. The standard is used across CT, MRI, ultrasound and other modalities. [DICOM overview](https://www.dicomstandard.org/about)

Design consequence: distinguish three experiences clearly:

1. **Report extraction:** a proposed value links to the original report page and the exact text region. Text coordinates and image coordinates are different; a highlighted text excerpt must not pretend to locate an abnormality on a scan.
2. **Image navigation:** a specialist reviews the original study through a suitable imaging viewer. Retain study/series/instance identifiers, frame or slice, orientation and annotation provenance. A screenshot or schematic is only a preview, not a complete diagnostic study.
3. **Image interpretation:** an AI-detected lesion, cellular finding or measurement is a separate model output that needs its own intended-use definition, ground truth and validation. Do not imply that a PDF viewer or a report-extraction model provides this capability.

For the first prototype, show source page/region inspection and a clearly labeled imaging-review placeholder or synthetic illustration. Do not place invented AI findings on a real patient's scan. AML workup also involves pathology, flow and genetic information; do not make radiology the universal entry point.

## Why signatures are necessary but insufficient

FDA/Health Canada/MHRA transparency principles emphasize performance of the **human-AI team**, intended use, output basis, limitations, failure modes, local acceptance testing and ongoing monitoring. These principles support review interfaces but do not say that a signature validates an AI model. [Transparency principles](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/transparency-machine-learning-enabled-medical-devices-guiding-principles)

FDA's GMLP page points to the January 2025 IMDRF final principles and frames AI development across the total product lifecycle. This is a validation reference, not a determination of Indian regulatory obligations. [GMLP overview](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/good-machine-learning-practice-medical-device-development-guiding-principles)

**Engineering inference:** sign-off records who accepted a particular version. It cannot establish sensitivity for omitted biomarkers, accuracy on unfamiliar lab layouts, image interpretation performance or a clinician's ability to catch every error. “Medical grade” must be supported by measured performance in the intended setting, not used as a prototype label.

Before clinical deployment, define acceptance thresholds with clinicians and evaluate on an independently annotated, held-out dataset representative of intended hospitals, laboratories, languages, document quality and patient populations. Measure separately:

- Correct patient/specimen/date association; wrong-patient errors deserve separate reporting.
- Field precision and recall, including clinically important omissions, negation, numerical values and units.
- Source-region correctness and whether each proposed claim is actually supported.
- Abstention on unreadable, ambiguous or unsupported inputs; conflicting and amended reports.
- Performance by report type and site, rather than one blended accuracy score.
- Review time, residual errors after review and automation bias in the complete human-AI workflow.
- Any imaging model's task-specific performance independently from document extraction.

These are proposed evaluation measures; no performance result or universal percentage threshold has been established for this prototype.

## Chat updates and encounter reviews

Treat a chat instruction as a proposed change, not a signed order. Present a before/after diff, the affected fields and evidence, the responsible reviewer, and any missing inputs. Clarify ambiguous instructions. A proposed treatment-course change belongs in an oncologist review queue and becomes a new approved plan version only after the required review. Preserve the earlier plan and encounter history.

For every encounter, separate observed symptoms/results, patient-reported information, AI-prepared summaries, clinical interpretation and the next decision. The interface can save time by preparing these sections and linking changes to their sources; it should never silently convert a summary into a diagnosis, urgency determination or treatment order.

## Smallest useful clinician-review demonstration

Upload or open a fictional report → inspect proposed diagnosis/biomarker fields → click a field to inspect its exact source → correct or reject it → flag missing/conflicting information → approve the profile version → inspect a source-linked current-condition/prior-course summary → enter a chat update → review the change diff → sign the next encounter/plan version and assign follow-through.

Demonstrate the distinction between working functionality and simulated AI explicitly. Reviewer questions: Does the profile retain the information needed to judge the case? Can every field be checked quickly? Are omissions visible? Does the summary preserve chronology and uncertainty? Does the change review make clinical ownership clear?
