# mCODE: schema and public examples, not a real patient dataset

Retrieved 2026-10-11 through gstack browse.

Primary URLs:
- https://hl7.org/fhir/us/mcode/
- https://hl7.org/fhir/us/mcode/examples_genomics.html
- https://hl7.org/fhir/us/mcode/DiagnosticReport-gx-genomics-report-adam-anyperson.html
- https://hl7.org/fhir/us/mcode/DiagnosticReport-gx-genomics-report-adam-anyperson.json.html

## Verified
The current published implementation guide is **4.0.0 STU4**, active/generated 2025-02-16, using **FHIR R4 4.0.1**. This is the published release, not a continuous-build URL. It organizes approximately 40 profiles into patient, disease, assessment, genomics, treatment and outcome groups. It explicitly permits using other appropriate FHIR profiles/resources for concepts outside its scope.

Quote: “mCODE does not define a specific set of information that must be collected for each cancer patient.”

The public example JSON was actually read. Its DiagnosticReport references a ServiceRequest, a patient, a performing laboratory, an interpreting practitioner, two specimens and many result Observations. The examples distinguish genomic variants, pertinent negative findings, diagnostic implications and therapeutic implications. These are authored conformance examples, not real records or evidence of clinical accuracy. Narrative and JSON representations were both inspectable without login. The example includes observation dates that predate its report date; never adopt its timeline as a clinically validated scenario.

## Access, licence, confidence and fit
Public documentation and examples. FHIR R4 specification's CC0 terms are separately verified in structure_fhir.md; third-party terminology licences remain separate. mCODE package-specific content licence was not independently inspected in this bounded review; do not infer a blanket licence for all referenced content. Confidence high for version and observed structure. Bias: US-realm representation choices and selective examples; local Indian interoperability requirements require separate mapping. Fit: strong structural reference, weak as a realistic AML source-report corpus or complete local department workflow.
