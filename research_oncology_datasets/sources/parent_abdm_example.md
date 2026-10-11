# Official ABDM laboratory bundle example

URL: https://www.nrces.in/ndhm/fhir/r4/Bundle-DiagnosticReport-Lab-example-03.html
Retrieved: 11 October 2026, rendered narrative inspected using gstack browse.
Type: primary official example, not authentic patient dataset. Guide displayed version 6.5.0, based on FHIR R4. Credibility: high for illustrating resource relationships; no claim of clinical realism. Recency: live published example, largely older illustrative timestamps. Bias: exchange demonstration.

The example has separate Composition, Patient, Practitioner, Organization, DiagnosticReport, Observation, Specimen, ServiceRequest and DocumentReference resources, including a PDF attachment. Its numeric observations carry units and reference information; these are not just lines in an undifferentiated summary. No original PDF from this example was downloaded.

Important observed limitation: its illustrated dates are not a coherent clinical chronology (for example specimen received and collected years differ, and some observation timing differs from report timing). Use it to study references and representation; do not copy its content as a realistic oncology patient journey or a clinical gold standard.

Plan implication: standards examples guide structure, while a clinician-reviewed synthetic case must independently validate chronology and clinical coherence. Preserve source timing inconsistencies in real imports and make them reviewable instead of automatically repairing them.
