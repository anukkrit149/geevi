# TCIA CMB-AML

Retrieved 11 October 2026 via gstack. Primary current collection page; high confidence for collection metadata, individual files not downloaded.

- Collection: https://www.cancerimagingarchive.net/collection/cmb-aml/
- Citation: Cancer Moonshot Biobank. (2023). Cancer Moonshot Biobank – Acute Myeloid Leukemia (CMB-AML) (Version 9) [dataset]. The Cancer Imaging Archive. https://doi.org/10.7937/pcte-6m66
- Version 9, updated 2 July 2026: 16 total subjects; open radiology subset 9 subjects/16 studies; pathology 16 subjects/67 slides. DICOM radiology, SVS whole-slide images and JSON pathology metadata. Distinct subsets have different access policies; counts need not sum.
- Time: DICOM tag 0012,0052 stores offset days with 0012,0053 set to REGISTRATION. Modified dates preserve intervals. Useful genuine longitudinal alignment; never represent modified dates as real calendar dates.
- Clinical subset: https://clinical.datacommons.cancer.gov/?cid=eb_govdel#/study/NCT04314401 — linked official open subset, but this session reached only site shell/warning. Full clinical/genomic/phenotypic data is controlled via https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id=phs002192.
- Open imaging/pathology subset CC BY 4.0; facially reconstructable head-image subset controlled. No actual narrative report PDFs advertised in inspected table.
- Quote: “subset of Clinical Data – open access”.
- Limit: promising multimodal temporal reference, not verified complete patient narrative or departmental workflow history; do not download the 445GB pathology package for report-layout design.
