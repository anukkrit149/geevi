# TCIA TCGA-KIRC linkage and date caveat

Retrieved 11 October 2026 via gstack. Primary collection documentation; last listed update 29 May 2020, so metadata context is historical.

- https://www.cancerimagingarchive.net/collection/tcga-kirc/
- Citation: Akin, O., et al. (2016). The Cancer Genome Atlas Kidney Renal Clear Cell Carcinoma Collection (TCGA-KIRC) (Version 3) [Data set]. The Cancer Imaging Archive. https://doi.org/10.7937/K9/TCIA.2016.V6PBVTDR
- 267 subjects, CT/MR/CR DICOM; CC BY 3.0. Patient identifiers match corresponding TCGA subjects. 439 studies does not imply every patient has serial scans.
- Quote: “TCIA and TCGA handle dates differently”.
- TCIA shifted image dates preserve within-subject scan intervals; TCGA clinical events are relative to a diagnosis index. A shared patient ID does not by itself reconcile those date systems. Baseline archived imaging is pre-surgical.
- Images and associated clinical/genomic links are verified; original free-text radiology reports are not advertised in the inspected download table. Whole-slide images and radiologist annotations are not equivalent to signed narrative reports.
- Use: optional solid-tumour imaging/linkage reference. Do not fuse with the retained lung report or AML workbook as if one patient's chart. No image download performed.
