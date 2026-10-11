# TCGA-LAML live metadata inspection

Retrieved 11 October 2026 using documented GDC API via gstack. Primary live metadata, high confidence for returned records; cohort completeness not established.

- Access entry: https://portal.gdc.cancer.gov/projects/TCGA-LAML
- Case inspected: `TCGA-AB-2810`, case UUID `865cda60-ec30-4562-b681-0e90737a97ca`.
- Reproducible case endpoint: https://api.gdc.cancer.gov/cases/865cda60-ec30-4562-b681-0e90737a97ca?expand=demographic,diagnoses,diagnoses.treatments,follow_ups,samples&pretty=true
- Project-filtered case query returned 200 cases. Inspected one record: diagnosis, demographics, primary peripheral-blood and normal-tissue sample entities, relative follow-up days, vital status and limited treatment assertions. Some follow-up objects had only identifiers; dates/values were often null. Treatment fields included explicit `treatment_or_therapy: no`, so a listed agent is not proof of administration.
- Exact filters and observed queries are recorded in `findings_datasets.md`.
- A query combining `cases.project.project_id=TCGA-LAML` and `files.data_type=Pathology Report` returned zero on this date. This only establishes the result of that filter, not absence of all AML reports in all repositories.
- Quote: none; machine field names retained as identifiers.
- Access/licence: inspected metadata required no login; open/controlled file access is per-file. GDC data policy applies. Supplemental XML/TSV availability should be inspected before choosing a subset; no raw sequencing downloaded.
