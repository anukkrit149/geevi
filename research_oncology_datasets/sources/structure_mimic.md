# MIMIC-IV Note versus Demo: different access and content

Retrieved 2026-10-11.
- MIMIC-IV-Note v2.2 metadata: https://physionet.org/content/mimic-iv-note/2.2/
- Official note documentation: https://mimic.mit.edu/docs/iv/modules/note/
- Official access requirements: https://mimic.mit.edu/docs/gettingstarted/
- Demo v2.2: https://physionet.org/content/mimic-iv-demo/2.2/

## MIMIC-IV-Note
The official documentation describes deidentified discharge summaries and radiology reports, plus detail tables. Linkage to the rest of MIMIC-IV uses subject_id and hadm_id. Public documentation is not the note corpus. The indexed PhysioNet result identifies the dataset's licence as **PhysioNet Credentialed Health Data License 1.5.0**. Full metadata page timed out in gstack and read-only web fetch. The official access guide was read in gstack and verifies credentialing, human-subject research training and a signed data-use agreement for MIMIC access. No account, agreement or raw notes were accessed. Do not assume product redistribution, public demonstrations or external-model uploads are allowed merely because data are deidentified; project-specific licence terms require review if acquired later.

## MIMIC-IV Demo
The live project URL redirects to **v2.2, 31 January 2023**. The official full page was read using read-only web fetch after PhysioNet browsing problems. It contains **100 real deidentified patients** and explicitly excludes free-text clinical notes. The schema matches its corresponding MIMIC-IV version; hospital and ICU data are in CSV. Patient identifiers and dates are deidentified/shifted. File listings are public; total uncompressed content is 15.5 MB. No raw CSV was downloaded or inspected. It is **Open Data Commons Open Database License v1.0**, publicly accessible subject to that licence.

Demo quote (5 words): “but excludes free-text clinical notes.”

## Recommendation and limitations
Use Demo only as an optional real relational/timeline reference; it is not an oncology-specific cohort, an AML journey or an authentic report-narrative corpus. Note may help evaluate text extraction later, under appropriate approved access; it is hospital/radiology/discharge content, not a verified AML pathology dataset. Confidence high for official content/access descriptions; moderate for Note's exact licence version because only indexed metadata was available. Dataset age and US single-hospital care setting limit transfer to current Indian oncology.
