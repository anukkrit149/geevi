# A real open GDC pathology report inspected

Retrieved 11 October 2026. Primary live GDC API and original research-released report, high confidence for this file only.

- Metadata: https://api.gdc.cancer.gov/files/709e6425-3cfe-4f28-b97b-edaaa6aa257a?expand=cases.project&pretty=true
- File: https://api.gdc.cancer.gov/data/709e6425-3cfe-4f28-b97b-edaaa6aa257a
- Original name: `TCGA-44-6147.06F76ECF-14DB-4228-B413-F6B4E187A1E4.PDF`.
- UUID: `709e6425-3cfe-4f28-b97b-edaaa6aa257a`; project TCGA-LUAD; PDF; open; 23,130 bytes; version 1; data releases 36.0–46.0. Local MD5 matches API `32162173e9a79dd4070197fdd5c6903c`.
- Read two pages with pypdf and visually reviewed both rendered pages. Source has deliberate black redactions. Do not reverse, reconstruct or infer redacted identifiers.
- Observed structure: five separately labelled surgical specimens; clinical context; frozen-section result; detailed gross description and block summary; microscopic findings; separate diagnoses for each specimen. Supports specimen-level source anchors and multiple findings, rather than one patient-wide text field.
- Short quote: “Regional lymph nodes (pN): None definitively identified.”
- This is a historical lung solid-tumour report, not AML, not a complete care timeline and not a current staging reference. Do not attach it to an AML patient.
- Reuse: GDC open-data policy applies; no per-file CC licence was found. See `datasets_gdc_access.md` and sample README.
