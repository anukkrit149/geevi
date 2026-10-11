# BeatAML2.0 clinical workbook

Retrieved 11 October 2026. Primary public manuscript-data repository and its actual workbook; high confidence for structure/version inspected, no claim of full EHR coverage.

- Repository: https://github.com/biodev/beataml2.0_data
- Workbook: https://github.com/biodev/beataml2.0_data/blob/main/beataml_wv1to4_clinical.xlsx
- Workbook last-change commit: https://github.com/biodev/beataml2.0_data/commit/8571854b35ee0fa941c785b94153837541568896 (1 July 2022; initial dataset).
- Licence: https://github.com/biodev/beataml2.0_data/blob/main/LICENSE.txt — repository-wide CC BY 4.0; no workbook-specific exclusion observed. Preserve attribution and indicate modifications. Licence does not grant identity/privacy rights or establish clinical validity.
- Downloaded one small workbook (477 KiB); read headers, dictionary, metadata and first two specimen records; counted rows/subject IDs. Summary: 942 rows, 95 columns, 805 unique subject IDs, 108 subjects with multiple rows. Three sheets: summary, dataDictionary, metaData.
- Includes subject/sample identifiers, collection offsets, disease stage, specimen type, laboratory values, morphology, immunophenotype, cytogenetics, molecular markers, treatment summaries and outcomes. Repository separately lists sequencing-expression, mutation and inhibitor-response files; these were not downloaded.
- Crucial quote from regimen-list dictionary: “order of listing has no importance”. Therefore cumulative treatment lists are not ordered event histories.
- Historical classification labels and data-collection windows require context; sparse or sentinel-valued fields must not become asserted normal findings.
