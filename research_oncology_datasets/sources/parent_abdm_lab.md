# ABDM DiagnosticReportLab structural reference

Official URL: https://www.nrces.in/ndhm/fhir/r4/StructureDefinition-DiagnosticReportLab.html
Retrieved: 11 October 2026, full rendered page via gstack browse.
Observed publication: ABDM implementation guide 6.5.0, marked current published release, based on FHIR R4. A search also returned a 7.0.0 preview; the plan uses the published page rather than assuming preview is current.

Type: primary interoperability specification, not a patient dataset. Credibility: high for defined exchange structure. Recency: current published page at retrieval. Bias/transfer: India interoperability reference; not a complete oncology workflow or clinical requirements list.

Short quote: “Laboratory results are grouped and summarized using the DiagnosticReport resource”.

The profile groups individual Observation records into a report; it supports request, result, interpretation and formatted-report context, with report status distinct from the result itself. Official examples include https://www.nrces.in/ndhm/fhir/r4/DiagnosticReport-Lab-example-01.html and https://www.nrces.in/ndhm/fhir/r4/Bundle-DiagnosticReport-Lab-example-03.html.

Implication: model the original document, report, specimen, atomic findings and review decisions separately; render the six-dimensional profile from those attributed records. This mapping is proposed, not a claim of conformance. The profile is not evidence that the sample patient data are real, a full longitudinal oncology dataset, or a diagnostic gold standard. Data/terminology permissions and actual conformance validation remain separate implementation tasks.
