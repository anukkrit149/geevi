# Synthea: longitudinal synthetic records

Retrieved 2026-10-11 through gstack browse.
- https://synthetichealth.github.io/downloads.html
- https://github.com/synthetichealth/synthea
- https://github.com/synthetichealth/synthea-sample-data

## Verified
Synthea generates simulated lifetime health records, including encounters, conditions, medications, labs/observations, procedures and care plans. Formats include FHIR R4, C-CDA and CSV. The public download page lists latest 100-patient examples; the FHIR R4 archive is 36 MB. The sample repository was updated 2026-08-18. No sample archive was downloaded or raw record inspected in this strand.

The official downloads page links an oncology mCODE collection explicitly described as **breast cancer**, not AML. It also lists a 9 GB Coherent dataset connecting synthetic FHIR records, imaging, genomics and simple notes. We did not download it or inspect its raw files. Do not describe either as a clinically validated AML dataset.

Quote from generator README: “synthetic, realistic (but not real), patient data”.

## Access/licence
The generator software uses **Apache 2.0**. Separately, the official download page says its synthetic data may be used without restriction for secondary uses in academia, research, industry and government, and asks for citation. Do not confuse the software licence with raw hospital-data permissions. The sample-data repository itself displayed no separately inspected licence file; preserve the official download-page terms when acquiring a sample.

## Fit and limitations
Strong for timeline mechanics, import/export, repeated encounters and treatment-versus-observation relations. US population defaults and generic generated content are not Indian clinical practice evidence. AML-specific clinical rules, report narratives, regimen choices, adverse-event logic and response schedules require clinical authorship/validation; none were verified here. Confidence high for published capabilities and access; moderate for dataset clinical realism because raw samples were not inspected.
