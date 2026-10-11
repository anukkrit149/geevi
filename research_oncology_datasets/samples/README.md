# Small public research samples

Downloaded and inspected 11 October 2026 for report/data-structure research. These are de-identified research records. They are not a linked patient journey, clinical guidance, or data for a real patient in this app. No application fixtures were changed.

## Solid-tumour pathology example

- File: [solid-tumor_TCGA-44-6147_pathology.pdf](solid-tumor_TCGA-44-6147_pathology.pdf)
- Source: https://api.gdc.cancer.gov/data/709e6425-3cfe-4f28-b97b-edaaa6aa257a
- Metadata: https://api.gdc.cancer.gov/files/709e6425-3cfe-4f28-b97b-edaaa6aa257a?expand=cases.project&pretty=true
- File UUID: 709e6425-3cfe-4f28-b97b-edaaa6aa257a. Case: TCGA-44-6147, project TCGA-LUAD (lung adenocarcinoma). This is NOT AML.
- Original filename: TCGA-44-6147.06F76ECF-14DB-4228-B413-F6B4E187A1E4.PDF
- GDC file version: 1; data release field: 36.0–46.0. Open access. 23,130 bytes, two pages.
- SHA-256: `e9d9bfe190739b3c645f626979d5b46a3254efa3b22672720bbd23d73e0027b2`
- MD5: `32162173e9a79dd4070197fdd5c6903c`, matches GDC metadata.
- Original downloaded bytes unchanged; local filename adds a context label.
- Both pages text-inspected and visually reviewed. PNG previews: [page 1](solid-tumor_TCGA-44-6147_pathology_page-1.png), [page 2](solid-tumor_TCGA-44-6147_pathology_page-2.png). Redactions belong to the released source and were preserved.
- Attribution: The Cancer Genome Atlas (TCGA), TCGA-LUAD, case/file identifiers above; accessed through NCI Genomic Data Commons.
- Governing data terms: https://gdc.cancer.gov/access-data/data-access-policies. Do not identify or contact participants; acknowledge dataset/repository. No per-file Creative Commons licence was displayed. Open access is not a blanket product-redistribution or clinical-use approval. Article copyright terms do not replace data-use conditions.

## Beat AML research specimen metadata

- File: [BeatAML2_research-specimen-clinical.xlsx](BeatAML2_research-specimen-clinical.xlsx)
- Source: https://github.com/biodev/beataml2.0_data/raw/refs/heads/main/beataml_wv1to4_clinical.xlsx
- Original name: beataml_wv1to4_clinical.xlsx.
- Repository/attribution: BeatAML2.0 manuscript data, biodev; workbook initial dataset commit by dbottomly, 1 July 2022.
- Workbook file history: https://github.com/biodev/beataml2.0_data/commits/main/beataml_wv1to4_clinical.xlsx
- Last-change commit observed: `8571854b35ee0fa941c785b94153837541568896`.
- Pinned file reference: https://github.com/biodev/beataml2.0_data/blob/8571854b35ee0fa941c785b94153837541568896/beataml_wv1to4_clinical.xlsx
- SHA-256: `bc692f647f93945e1cf883271af5501bf75c8af3e681676241093c198ed167ad`.
- File downloaded from main; last-change commit identified in the file's GitHub history. Original bytes unchanged; local filename adds a research-context label.
- Repository-wide CC BY 4.0 displayed; no workbook-specific exclusion found. Retained [licence text](BeatAML2_LICENSE.txt), from https://github.com/biodev/beataml2.0_data/raw/refs/heads/main/LICENSE.txt. Keep attribution, licence link and change notices for derived/shared material. No clinical validation or privacy-right grant is implied.
- Workbook has summary, dataDictionary and metaData sheets. Inspected 942 data rows / 95 fields, 805 unique subject IDs; 108 subjects have multiple specimen rows. Counts were computed from this workbook, not claimed as cohort totals for all Beat AML releases.
- This is specimen-level research metadata with some longitudinal samples and summary treatment/outcome fields. Cumulative regimen lists are unordered. Do not turn them into event dates, orders, administrations or a complete medical record.
- This workbook and the lung PDF have unrelated patients. Never join them as one chart.

Only these two small data files and the licence were downloaded. No controlled files, raw sequencing, images or large collections were acquired.
