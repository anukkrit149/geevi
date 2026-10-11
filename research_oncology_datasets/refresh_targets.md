# Research refresh targets

As of 11 October 2026. Refresh at the relevant implementation/acquisition milestone; no recurring automation was created.

| Trigger | Verify | Why |
|---|---|---|
| Before importing Beat AML | Pinned workbook, dictionary, metadata, licence and any field-specific constraints | Preserve collection windows, sentinel values, historical classifications and unordered treatment summaries |
| Before additional GDC downloads | Live case/file links, access tier, data release and governing policy | Availability and metadata can change; open is not a universal reuse licence |
| Before TCIA integration | Collection version, subject coverage per subset, temporal anchors, licences and controlled-access boundary | Imaging, pathology and clinical membership differ |
| Before FHIR implementation | Published mCODE and ABDM versions, selected base FHIR version, terminology rights and profile validation tooling | Do not mix incompatible releases or claim conformance from a conceptual mapping |
| Before copying clinical template content | CAP or other publisher's current incorporation rights and local clinical approval | A readable template is not necessarily free to embed |
| Before real hospital evaluation | Permitted purpose, document families, access/retention/external-processing policy and independent annotations | Public and synthetic examples cannot establish local extraction accuracy |
| Before claiming workflow benefit | Observed baseline, staff roles, required approvals, response ownership and measured pilot results | A completed demonstration is not adoption or clinical validation |

Still unverified: a public narrative AML radiology-report corpus for this exact use; full CMB-AML open clinical records behind the CTDC shell; raw MIMIC Note and Synthea samples; mCODE package-specific licence beyond the FHIR specification; institution-specific workflow, clinical thresholds and approval policies.
