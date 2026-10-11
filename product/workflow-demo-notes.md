# Interactive evidence-to-handoff demo

Open [the evidence lab](evidence-review.html). The main [clinical workspace](aml-screen-walkthrough.html) now demonstrates patient intake and longitudinal review; see [its review guide](intake-review-guide.md). Meera, Arun, their assessments, example cohorts and signatures are synthetic. Uploaded research can be an actual article, but its extraction and applicability require review. This is a local prototype, not a clinically validated product or authorization system.

Run `python3 product/serve-demo.py` from the workspace root and open `http://127.0.0.1:8765/product/evidence-review.html`. Keep the loopback server running. It exposes only files under `product/` and `research/`, with directory listings disabled. Use this HTTP preview: direct `file://` browsing cannot load the PDF worker.

## PDF walkthrough

1. Choose Meera and the Oncologist view. In **Attach research**, upload a text-based research PDF or select **Try a synthetic research PDF**. The included two-page fixture is conspicuously labeled as fabricated throughout. Its counts are invented solely for UI testing.
2. **Review PDF extraction** shows suggested criterion and result passages. Each retains the file's SHA-256 fingerprint, PDF page number, exact text and offsets. The keyword-based passage finder proposes passages, not verified interpretations or a complete study extraction.
3. Open **Inspect original source**. Compare the rendered original page with the quoted passage and highlighted extracted text. Mark the passage inspected, then verify or correct the field label and mapping. Inspection does not by itself verify interpretation.
4. For a criterion, choose the patient parameter, inclusion/exclusion logic, operator and required value. For the sample, map age to 18–65 inclusive, diagnosis to AML and intensive-treatment fitness to `fit`. Non-APL status and newly diagnosed setting are also in the fictional record; the example disease mapping alone does not encode every aspect of that sentence. Add separate exact excerpts for additional criteria as needed.
5. For a result, record the endpoint, estimate, population/denominator, intervention, comparator, time point and uncertainty if established by the reviewed source; explain limitations. The sample reports invented counts of 12/20 versus 8/20 at 6 months, with no established uncertainty or clinical benefit. Missing context is shown as not established, never invented. These are source-level results, not a patient-benefit prediction.
6. Verify or explicitly dismiss every suggestion. Use the full extracted page text to add an exact passage the finder missed. Confirm the selected extraction scope and which strategy it informs. If no results are included, explain that omission.
7. **Compare parameters** shows the reviewed criteria, patient facts, matches/differences/unknowns, and reviewed results with buttons back to the original pages. Sign a separate patient-specific applicability review with a rationale. Every attached source needs an applicability review.
8. **Review & sign** lets the oncologist choose the strategy, explain the reasoning and patient-facing next step, save it, and simulate approval. PDF evidence can support the selected strategy once extraction and applicability are reviewed; reference-only links remain contextual. Unknown parameters in supporting evidence block this guided non-urgent demo.
9. **Care handoff** lets the oncologist or coordinator assign the signed packet; the receiving care team separately acknowledges it. **Patient & family** shows only the approved explanation and coordination status, without research-review or clinical-signature controls.
10. Attach the PDF to Arun using the copy button. Its file and extracted text can be reused, but all source verification and patient-specific reviews start pending. His age differs from the sample cohort; fitness remains unknown until the fictional specialist report is loaded, after which it also differs. The intensive cohort can be reviewed as conflicting; the existing less-intensive example illustrates a separately supported lower-intensity strategy. No treatment is automatically selected from matching.
11. Change a verified field or its mapping after approval. Extraction and applicability reviews reopen; the current signature and handoff are archived. **History & audit** preserves the old signed quotes, mappings, results, rationale, file hash and handoff. New patient evidence similarly reopens applicability review.

## State and boundaries

- Original PDF bytes are parsed and rendered locally with vendored Mozilla PDF.js 5.6.205; no article is uploaded to the server or an external AI service. PDF scripts and XFA are not executed. PDF fonts, maps and worker resources are served locally.
- Original PDFs live in this origin's IndexedDB database `casebook-pdf-library`; case progress, extracted page text, reviews and signed snapshots live under `casebook-evidence-demo-v2` in localStorage. Browser/origin changes do not share this data. A visible warning reports failed case persistence.
- Resetting a patient clears their case progress, not the PDF library or the other patient. Clear this site's browser data to remove all locally retained files and case records. If original bytes are missing but case text remains, re-upload the identical PDF to restore the original; this does not duplicate the case attachment or inherit a signature.
- The limits are 15 MB, 100 pages, 300,000 extracted characters and 80 automatically suggested passages per PDF. The full extracted page text remains available when suggestions are capped. Processing timeouts and malformed/password-protected documents produce explicit errors.
- Scans need OCR before upload. Mixed pages with little text produce warnings. Multi-column order, tables, figures, symbols, footnotes, supplementary files and eligibility nuances can be missed. Source inspection and clinician-entered mappings remain necessary. This is not a general AI study parser.
- Numeric comparisons support equals, minimum, maximum and inclusive range; text comparisons use exact normalized values. Exclusion reverses a known match; missing facts remain unknown. ECOG, LVEF and unrecorded biomarkers are not inferred from narrative fitness or age.
- A reviewed passage, an applicability signature and a plan signature are separate steps. None establishes research authenticity, methodological quality, institutional adoption, complete trial eligibility or a treatment recommendation.
- All roles, approvals and local audit records are client-side demonstrations; they are not secure authorization, tamper-proof storage or legally meaningful electronic signatures. No prescription, administration clearance, patient consent, actual treatment or external message is created.
- Use research documents you are authorized to use. Do not enter real patient information. The original storyboard remains at [aml-journey-storyboard.html](aml-journey-storyboard.html).

## Implementation and verification

- `pdf-reader.js`: bounded PDF parsing/rendering, local original-file storage, hashing and error handling.
- `pdf-evidence.js`: exact passage suggestions, citation validation, mapping validation and patient comparisons.
- `pdf-workspace.js`: upload, source inspector, extraction review forms and result context.
- `workflow-model.js`: case transitions, extraction/applicability reviews, versioned snapshots and handoff invalidation.
- `workflow-app.js` / `workflow.css`: role-specific UI, local case persistence, escaped output and responsive layout.
- `vendor/pdfjs/`: locally bundled PDF.js and supporting assets, Apache-2.0 license and version provenance.

Run `node --test product/tests/*.test.cjs` from the workspace root. The 21 model tests cover provenance, decimal/line-wrap preservation, missing values, polarity, review gates, role checks, case isolation and signed-history preservation.

After opening the app in gstack browse, run `eval product/tests/browser-workflow-check.js` for the original 22 UI assertions and `eval product/tests/browser-pdf-check.js` for 44 PDF-flow assertions. These scripts reset both fictional cases. The PDF script tests original-page rendering, extraction verification, both patient comparisons, separate sign-offs, handoff, family restrictions and amendment behavior. `browser-pdf-errors.js` exercises scanned/corrupted/encrypted/missing-source errors. The synthetic sample can also be selected through the actual file input. Reload and responsive checks verify locally retained sources and desktop/mobile presentation.
