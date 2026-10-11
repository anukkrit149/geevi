# FHIR R4 report, observation, specimen and document boundaries

Retrieved 2026-10-11 through gstack browse. Primary technical specifications:
- https://hl7.org/fhir/R4/diagnosticreport.html
- https://hl7.org/fhir/R4/observation.html
- https://hl7.org/fhir/R4/specimen.html
- https://hl7.org/fhir/R4/documentreference.html
- https://hl7.org/fhir/R4/license.html

## Verified
These are permanent R4 4.0.1 pages, deliberately chosen because published mCODE 4.0.0 uses R4. The pages identify R5 as newer; do not call R4 the newest FHIR version.

- DiagnosticReport combines report-level context, results, interpretation, specimens, request references, responsible parties and the issued human-readable document. It distinguishes effective clinical time from issue time. Observations provide the atomic results; reports can be narrative, structured or both. Updated and withdrawn reports need explicit handling.
- Observation supports typed results, status, method, specimen, reference ranges, components, panel membership, source derivation and missing-result reason. It is not a general substitute for a diagnosis or every clinical entity.
- Specimen captures collection/receipt, material, body site, accession, parent specimen and processing. A sample identity is different from a patient or report identity.
- DocumentReference indexes source documents and their metadata; its relationships include replacement/appending, and it distinguishes document provenance from the provenance of the reference.

DiagnosticReport quote: “The DiagnosticReport resource is not intended to support cumulative result presentation (tabular presentation of past and present results in the resource).”

## Licence and confidence
Public specification under CC0, with trademark conditions and explicit exclusion of third-party terminology rights. Clinical/operational fitness must be validated by implementers. Confidence high for source structure; these specifications do not choose a local database or imply product conformance. Bias: interoperability abstractions, not a ready-made hospital workflow. Use a separate timeline/read model over repeated events, rather than treating one report as the complete longitudinal record.
