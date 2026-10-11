/**
 * The complete fictional journey (F1–F6) through the real UI, HTTP API, sessions and PostgreSQL:
 * Meera from research → shared protocol and SOP → sources → applicability, exception and exact plan
 * approval → accepted handoffs, attributed care, a concern and an unchanged routine follow-up →
 * protocol v2 with independently resolved impacts (Arun adopts, Meera retains) → a source correction.
 * Each actor is a separate browser context signed in as its own development account.
 */
import { expect, test, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import {
  acceptApplicability, announced, as, assessAndDiscuss, baseline, draftPlan, errorCode, input, newWorkspace, signIn, signPlan, submitPlan, W, type Actor,
} from "./driver";

test.describe.configure({ mode: "serial" });

let ws = "";
let rao: Page, sen: Page, mira: Page, isha: Page;
const s: Record<string, string> = {};
const url = (path: string) => `/w/${ws}${path}`;
const idFromUrl = (page: Page) => page.url().split("/").pop()!.split("?")[0];
let raoApi: Actor;

async function verifyAll(page: Page): Promise<number> {
  const rows = page.locator("[data-testid^='candidate-']");
  await expect(rows.first()).toBeVisible();
  const count = await rows.count();
  for (let i = 0; i < count; i++) {
    const row = rows.nth(i);
    if ((await row.locator("[data-status='unreviewed']").count()) === 0) continue;
    await row.getByRole("button", { name: /Inspect source/ }).click();
    if ((await row.getAttribute("data-testid")) === "candidate-Myeloid markers") {
      // The layout rule over-reads this line; the reviewer corrects the transcription with a reason.
      await row.getByRole("button", { name: "Correct…" }).click();
      await row.getByLabel("Result state as stated by the source").selectOption("reported_value");
      await row.getByLabel("Reason").fill("Only MPO was not tested; the markers themselves are reported.");
      await row.getByRole("button", { name: "Record corrected" }).click();
      await expect(row.locator("[data-status='corrected']")).toBeVisible();
    } else {
      await row.getByRole("button", { name: "Verify" }).click();
      await expect(row.locator("[data-status='verified']")).toBeVisible();
    }
  }
  return count;
}

async function receive(page: Page, patient: string, fixture: string, kind: string, title: string): Promise<void> {
  await page.goto(url(`/patients/${patient}/sources`));
  await page.getByRole("tab", { name: "All sections", exact: true }).click();
  await page.getByLabel("Original file").setInputFiles(input(fixture));
  await page.getByLabel("Report type", { exact: true }).selectOption(kind);
  await page.getByRole("button", { name: "Receive document" }).click();
  await expect(page.getByTestId("upload-result")).toContainText("pending");
  await page.getByTestId(`doc-${fixture}.pdf`).getByRole("link", { name: title }).click();
  await page.getByLabel(/I checked the patient/).check();
  await page.getByLabel("How was identity verified?").fill("Name, identifier and accession checked against the referral.");
  await page.getByRole("button", { name: "Associate with this patient" }).click();
  await announced(page, "Document associated");
  await verifyAll(page);
}

async function reviewerDecides(page: Page, path: string, decision: "Approve" | "Object", rationale = ""): Promise<void> {
  await page.goto(url(path));
  const form = page.getByTestId("review-decision");
  if (rationale) await form.getByLabel("Rationale (required for an objection)").fill(rationale);
  await form.getByRole("button", { name: decision, exact: true }).click();
  await announced(page, decision === "Approve" ? "Approval recorded" : "Objection recorded");
}

async function setCriteria(page: Page, choices: Record<string, string>): Promise<void> {
  for (const [requirement, choice] of Object.entries(choices)) {
    const row = page.getByTestId(`criterion-${requirement}`);
    await row.getByRole("radio", { name: choice, exact: true }).check();
    if (choice !== "match") await row.getByLabel(`Rationale for ${requirement}`).fill("Documented at the fictional encounter with the patient.");
  }
}

test.beforeAll(async ({ browser }) => {
  ws = (await newWorkspace("Department journey")).ws;
  [rao, sen, mira, isha] = await Promise.all((["rao", "sen", "mira", "isha"] as const).map((u) => signIn(browser, u)));
  raoApi = await as("rao");
});

test("F1 · research question, cited appraisal, disagreement resolved by an independent reviewer", async () => {
  // Rao adds the published-reference evidence brief and opens a question.
  await rao.goto(url("/research"));
  await rao.getByRole("button", { name: "Evidence library", exact: true }).click();
  await rao.getByLabel("Source title").fill("ELN 2022 AML recommendations — evidence brief");
  await rao.getByLabel("Citation").fill("Döhner et al. Blood 2022;140:1345–1377. https://pubmed.ncbi.nlm.nih.gov/35797463/");
  await rao.getByLabel("Evidence file (PDF, optional)").setInputFiles(input("eln-aml-2022"));
  await rao.getByRole("button", { name: "Add source" }).click();
  await announced(rao, "Evidence source added");
  await expect(rao.getByTestId("evidence-library")).toContainText("citable passages");
  await rao.getByRole("button", { name: "Questions", exact: true }).click();
  await rao.getByRole("button", { name: "Insert demo question 1" }).click();
  await rao.getByRole("button", { name: "Open question" }).click();
  await rao.waitForURL(/\/research\/[0-9a-f-]{36}$/);
  s.question = idFromUrl(rao);

  // Structured appraisal citing an exact passage, submitted to the independent reviewer.
  await rao.getByRole("button", { name: "Insert evidence appraisal example 1" }).click();
  await rao.getByLabel(/^Finding 1:/).check();
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await expect(rao.getByTestId("review-decision")).toHaveCount(0); // the author gets no decision form for their own work

  // Sen finds it through Today and objects; the disagreement is recorded.
  await sen.goto(url("/today"));
  await sen.getByTestId("work-review").getByRole("link").first().click();
  await sen.waitForURL(new RegExp(`/research/${s.question}`));
  const form = sen.getByTestId("review-decision");
  await form.getByRole("button", { name: "Object", exact: true }).click();
  await errorCode(sen, "reason_required");
  await form.getByLabel("Rationale (required for an objection)").fill("Limitations understate the absence of a comparison group.");
  await form.getByRole("button", { name: "Object", exact: true }).click();
  await announced(sen, "Objection recorded");

  // Rao answers with a successor revision; the objected version is retained as history.
  await rao.goto(url(`/research/${s.question}`));
  await expect(rao.getByTestId("appraisal-changes_requested")).toBeVisible();
  await rao.getByRole("button", { name: "Open successor revision" }).click();
  await announced(rao, "Successor draft opened");
  const editor = rao.getByTestId("appraisal-editor");
  await editor.getByLabel("Limitations", { exact: true }).fill("Expert recommendations, not a comparative study; the full guideline tables were not appraised. Current evidence and local applicability require further review.");
  await editor.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await reviewerDecides(sen, `/research/${s.question}`, "Approve", "Limitations are now stated plainly.");

  await rao.goto(url(`/research/${s.question}`));
  await expect(rao.getByTestId("appraisal-accepted")).toContainText("Appraisal v2");
  await expect(rao.getByTestId("reviews").getByTestId("decision-object")).toContainText("Dr. Sen");
  await expect(rao.getByTestId("reviews").getByTestId("decision-approve")).toContainText("Limitations are now stated plainly.");
  // Accepting evidence published nothing.
  await rao.goto(url("/department"));
  await expect(rao.getByTestId("protocols")).toContainText("No protocol versions yet.");
  await rao.goto(url(`/research/${s.question}`));
  await rao.getByLabel("Conclusion").selectOption("evidence_accepted");
  await rao.getByLabel("Reasoning").fill("Accepted appraisal supports a departmental preparation protocol.");
  await rao.getByRole("button", { name: "Conclude question" }).click();
  await expect(rao.getByTestId("question-status")).toContainText("evidence accepted");
});

test("F1 · protocol v1 and the separate SOP: Sen approves, Rao publishes", async () => {
  await rao.goto(url("/department"));
  await rao.getByRole("button", { name: /New protocol draft/ }).click();
  await rao.waitForURL(/\/department\/protocols\//);
  s.protocol = idFromUrl(rao);
  await expect(rao.getByTestId("requirement-REQ-MOLECULAR")).toBeVisible();
  // Without accepted evidence linked, submission is refused and the draft is kept.
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await errorCode(rao, "evidence_required");
  await expect(rao.getByTestId("requirement-REQ-VENUE")).toBeVisible();
  await rao.getByTestId("evidence-picker").getByRole("checkbox").first().check();
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await expect(rao.getByTestId("lifecycle")).toContainText("in review");
  await expect(rao.getByRole("button", { name: /Publish version/ })).toHaveCount(0); // not publishable before approval

  await reviewerDecides(sen, `/department/protocols/${s.protocol}`, "Approve");
  await expect(sen.getByTestId("lifecycle")).toContainText("approved");
  await expect(sen.getByRole("button", { name: /Publish version/ })).toHaveCount(0); // the reviewer cannot publish
  await rao.goto(url(`/department/protocols/${s.protocol}`));
  await rao.getByRole("button", { name: "Publish version 1" }).click();
  await announced(rao, "Version 1 published");
  await expect(rao.getByTestId("lifecycle")).toContainText("effective");
  await expect(rao.getByTestId("publications")).toContainText("Published by Dr. Rao");
  await expect(rao.getByTestId("reviews")).toContainText("Approved by Dr. Sen");

  // The departmental SOP has its own version, steps and review.
  await rao.goto(url("/department"));
  await rao.getByRole("button", { name: /New SOP draft/ }).click();
  await rao.waitForURL(/\/department\/sops\//);
  s.sop = idFromUrl(rao);
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await reviewerDecides(sen, `/department/sops/${s.sop}`, "Approve");
  await rao.goto(url(`/department/sops/${s.sop}`));
  await rao.getByRole("button", { name: "Publish version 1" }).click();
  await announced(rao, "Version 1 published");
  await expect(rao.getByTestId("lifecycle")).toContainText("effective");
  await expect(rao.getByTestId("step-STEP-PLANNING-VISIT")).toContainText("gated by REQ-MOLECULAR");
});

test("F2 · Mira registers Meera and reviews separately sourced reports; Rao assesses", async () => {
  await mira.goto(url("/patients"));
  await mira.getByRole("button", { name: "Register patient" }).click();
  const dialog = mira.getByRole("dialog");
  await expect(dialog.getByLabel("Display name")).toBeFocused();
  await dialog.getByLabel("Display name").fill("Meera (fictional)");
  await dialog.getByLabel("Identifier value").fill("GEEVI-DEMO-0001");
  await dialog.getByRole("button", { name: "Register", exact: true }).click();
  await announced(mira, "Patient registered");
  await mira.getByRole("link", { name: "Meera (fictional)", exact: true }).click();
  await mira.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
  s.meera = idFromUrl(mira);

  await receive(mira, s.meera, "meera-referral", "referral", "Referral letter");
  await receive(mira, s.meera, "meera-blood-day-minus-1", "blood_panel", "Blood count panel");
  await receive(mira, s.meera, "meera-marrow", "marrow", "Bone marrow morphology report");
  await receive(mira, s.meera, "meera-flow", "flow", "Flow cytometry report");
  await receive(mira, s.meera, "meera-cyto", "cytogenetics", "Cytogenetics report");
  await expect(mira.getByTestId("observations")).toContainText("Karyotype");

  // The final molecular report is expected, owned, and not implied to be ordered.
  await mira.goto(url(`/patients/${s.meera}/sources`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByLabel("What is expected").fill("Final molecular report");
  await mira.getByLabel("Next action").fill("Check with the genetics laboratory on Day 8");
  await mira.getByRole("button", { name: "Record expected input" }).click();
  await announced(mira, "Expected input recorded");
  await expect(mira.getByTestId("expected-inputs")).toContainText("Owner: Mira");

  // Coordinator cannot record a clinical assessment (no form); the treating clinician does.
  await expect(mira.getByLabel("Assessment narrative")).toHaveCount(0);
  await rao.goto(url(`/patients/${s.meera}`));
  await rao.getByText("Update clinical assessment", { exact: true }).click();
  await rao.getByLabel("Assessment narrative").fill("Fictional encounter assessment: profile reviewed with the patient; final molecular classification outstanding.");
  await rao.getByLabel("Stated uncertainty (optional)").fill("Final molecular report outstanding.");
  await rao.getByRole("button", { name: "Record assessment" }).click();
  await announced(rao, "Assessment recorded");
  // Six-dimensional longitudinal profile with distinct result states and explicit gaps.
  await expect(rao.getByTestId("dimensions").locator("section")).toHaveCount(5);
  await expect(rao.getByTestId("dimension-biology")).toContainText("insufficient sample");
  await expect(rao.getByTestId("dimension-fitness")).toContainText("not reported");
  await expect(rao.getByTestId("disease-burden")).toContainText("No stage or remission category is inferred");
  await expect(rao.getByTestId("patient-overview")).toContainText("Final molecular report");
  await expect(rao.getByTestId("cutoff")).toHaveCount(0);
  await expect(rao.getByTestId("unresolved")).toHaveCount(0);
});

test("F3 · applicability, patient discussion, an operational exception and exact plan approval", async () => {
  await mira.goto(url(`/patients/${s.meera}/decisions`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByLabel("Participants (comma separated)").fill("Meera (patient), Sister (caregiver), Mira");
  await mira.getByLabel("Goals in the patient's or caregiver's words").fill("Wants appointments close to home where possible.");
  await mira.getByLabel("Preferences and practical constraints").fill("Prefers the satellite clinic; long travel to the main campus.");
  await mira.getByRole("button", { name: "Document discussion" }).click();
  await announced(mira, "Patient discussion documented");
  await expect(mira.getByRole("button", { name: "Start applicability review" })).toHaveCount(0); // not a coordinator action

  await rao.goto(url(`/patients/${s.meera}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await rao.getByRole("button", { name: "Start applicability review" }).click();
  await announced(rao, "Applicability draft started");
  await setCriteria(rao, { "REQ-IDENTITY": "match", "REQ-CONTEXT": "match", "REQ-DISCUSSION": "match", "REQ-VENUE": "difference", "REQ-MOLECULAR": "unknown" });
  await rao.getByRole("button", { name: "Accept applicability review" }).click();
  await announced(rao, "Applicability review accepted");
  await expect(rao.getByTestId("applicability-accepted")).toContainText("REQ-MOLECULAR");

  // Operational venue exception: requested, then approved by the permitted approver.
  const form = rao.getByTestId("exception-form");
  await form.getByLabel("Requirement").selectOption("REQ-IDENTITY");
  await form.getByLabel("Requested departure").fill("Skip the identity review for this patient.");
  await form.getByLabel("Rationale").fill("Trying to waive a non-waivable requirement.");
  await form.getByLabel("Review trigger").fill("None");
  await form.getByRole("button", { name: "Request exception" }).click();
  await errorCode(rao, "non_waivable");
  await form.getByLabel("Requirement").selectOption("REQ-VENUE");
  await form.getByRole("button", { name: "Insert fictional scenario text" }).click();
  await form.getByRole("button", { name: "Request exception" }).click();
  await announced(rao, "Exception requested");
  const venue = rao.getByTestId("exception-REQ-VENUE-pending");
  await venue.getByLabel("Decision rationale for REQ-VENUE").fill("Location preference documented in the discussion; no treatment rule is changed.");
  await venue.getByRole("button", { name: "Approve exception" }).click();
  await announced(rao, "Exception decision recorded: approve");
  await expect(rao.getByTestId("exception-REQ-VENUE-approved")).toBeVisible();
  await expect(rao.getByTestId("plan-current")).toHaveCount(0); // an approved exception approves no plan

  // The clinical exception for the molecular input needs Rao AND Sen; it stays pending and owned.
  await form.getByLabel("Requirement").selectOption("REQ-MOLECULAR");
  await form.getByRole("button", { name: "Insert fictional scenario text" }).click();
  await form.getByRole("button", { name: "Request exception" }).click();
  await announced(rao, "Exception requested");
  const molecular = rao.getByTestId("exception-REQ-MOLECULAR-pending");
  await molecular.getByLabel("Decision rationale for REQ-MOLECULAR").fill("Treating clinician's approval; awaiting the independent reviewer.");
  await molecular.getByRole("button", { name: "Approve exception" }).click();
  await announced(rao, "Exception decision recorded: approve");
  await expect(rao.getByTestId("exception-REQ-MOLECULAR-pending")).toContainText("approvals 1 of 2");
  await mira.goto(url(`/patients/${s.meera}/decisions`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(mira.getByTestId("exception-REQ-MOLECULAR-pending")).toContainText("Awaiting 1 more decision");
  await expect(mira.getByRole("button", { name: "Approve exception" })).toHaveCount(0);

  // Exact plan: save and submit freeze the packet; signing is a separate, reviewed action.
  const editor = rao.getByTestId("plan-editor");
  await editor.getByLabel("Individual intent").fill("Complete case preparation at the satellite clinic and arrange the planning visit as documented (fictional workflow intent).");
  await editor.getByLabel(/REQ-VENUE — operational exception/).check();
  await editor.getByRole("button", { name: "Save and submit for signature" }).click();
  await announced(rao, "frozen for signature");
  const submitted = rao.getByTestId("plan-submitted");
  await expect(submitted.getByTestId("gates")).toContainText("covered by approved exception");
  await submitted.getByRole("button", { name: "Review and sign…" }).click();
  const dialog = rao.getByTestId("sign-dialog");
  await expect(dialog).toContainText("signing exactly this frozen packet");
  await rao.keyboard.press("Escape"); // keyboard: the dialog closes without signing anything
  await expect(dialog).toHaveCount(0);
  await expect(rao.getByTestId("plan-current")).toHaveCount(0);
  await submitted.getByRole("button", { name: "Review and sign…" }).click();
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  await announced(rao, "Plan version 1 approved");
  const current = rao.getByTestId("plan-current");
  await expect(current.getByTestId("plan-disposition")).toContainText("active");
  await expect(current.getByTestId("plan-currency")).toContainText("review current");
  s.digest = (await current.getByTestId("plan-digest").innerText()).trim();
  expect(s.digest).toMatch(/^[0-9a-f]{64}$/);
  // The shared protocol was not changed by the individual exception.
  await current.getByRole("link", { name: "Open pinned protocol version" }).click();
  await expect(rao.getByTestId("lifecycle")).toContainText("effective");
  await expect(rao).toHaveURL(new RegExp(s.protocol));
});

test("F4 · SOP-derived handoffs, attributed actual care and a concern", async () => {
  await mira.goto(url(`/patients/${s.meera}/care`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByRole("button", { name: "Create tasks from the SOP" }).click();
  await announced(mira, "SOP tasks created");
  await expect(mira.locator("[data-testid^='task-STEP-']")).toHaveCount(4);
  // The task is inspectable back to the exact SOP version and step.
  await expect(mira.getByTestId("task-STEP-CONFIRM-VENUE")).toContainText("step STEP-CONFIRM-VENUE");
  await expect(mira.getByTestId("task-sop-link-STEP-CONFIRM-VENUE")).toHaveAttribute("href", new RegExp(`/department/sops/${s.sop}`));
  for (const step of ["STEP-CONFIRM-VENUE", "STEP-PREP-VISIT"]) {
    await mira.getByTestId(`task-${step}`).getByRole("button", { name: "Send handoff" }).click();
    await expect(mira.getByTestId(`task-status-${step}`)).toContainText("sent");
  }
  // The planning visit depends on the pending clinical exception: only that dispatch is blocked.
  await expect(mira.getByTestId("task-gate-STEP-PLANNING-VISIT")).toContainText("REQ-MOLECULAR");
  await mira.getByTestId("task-STEP-PLANNING-VISIT").getByRole("button", { name: "Send handoff" }).click();
  await errorCode(mira, "dependent_scope_unresolved");
  await expect(mira.getByTestId("task-status-STEP-PLANNING-VISIT")).toContainText("draft");

  // Isha: a sent handoff is not accepted until she acts.
  await isha.goto(url("/today"));
  await expect(isha.getByTestId("work-task")).toContainText("Receive or accept the handoff");
  await isha.getByTestId("work-task").getByRole("link").first().click();
  await isha.waitForURL(/\/care#tasks$/);
  const venue = isha.getByTestId("task-STEP-CONFIRM-VENUE");
  await venue.getByRole("link", { name: /Case preparation and handoff SOP/ }).click();
  await expect(isha.getByTestId("step-STEP-CONFIRM-VENUE")).toContainText("Confirmation note naming who was contacted");
  await isha.goBack();
  await venue.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(isha.getByTestId("task-status-STEP-CONFIRM-VENUE")).toContainText("accepted");
  await venue.getByLabel(/Reason or completion evidence/).fill("Spoke to Meera's sister; satellite clinic on Day 3 at 10:00 confirmed.");
  await venue.getByRole("button", { name: "Complete with evidence" }).click();
  await expect(isha.getByTestId("task-status-STEP-CONFIRM-VENUE")).toContainText("completed");

  // Scheduling is not delivery.
  await isha.getByRole("tab", { name: "All sections", exact: true }).click();
  const planned = isha.getByTestId("planned-events");
  await planned.getByLabel("What is scheduled").fill("Preparation visit at the satellite clinic");
  await planned.getByLabel("Scheduled for (relative day)").fill("3");
  await planned.getByLabel("Location").fill("Satellite clinic");
  await planned.getByRole("button", { name: "Schedule", exact: true }).click();
  await announced(isha, "Event scheduled");
  await expect(isha.getByTestId("care-events")).toContainText("No care events have been entered here.");
  // Actual care: partial, attributed to Isha, under the signed plan.
  const care = isha.getByTestId("care-events");
  await care.getByLabel("Status", { exact: true }).selectOption("partial");
  await care.getByLabel("Actual time (relative day)").fill("3");
  await care.getByLabel("What happened").fill("Preparation checklist started; information leaflet was not available on the day.");
  await care.getByRole("button", { name: "Save care record" }).click();
  await announced(isha, "Care record saved");
  await expect(care.getByTestId("care-partial")).toContainText("Performed by Isha");
  await expect(care.getByTestId("care-partial")).toContainText("under plan v1");

  // A concern: acknowledged is not responded; then response and clinician review.
  const concerns = mira.getByTestId("concerns");
  await mira.goto(url(`/patients/${s.meera}/care`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await concerns.getByLabel("Concern as reported").fill("Caregiver phoned: worried about transport to the satellite clinic next week.");
  await concerns.getByLabel("Reported by").selectOption("caregiver");
  await concerns.getByRole("button", { name: "Record concern" }).click();
  await announced(mira, "Concern recorded");
  await isha.goto(url(`/patients/${s.meera}/care`));
  await isha.getByRole("tab", { name: "All sections", exact: true }).click();
  await isha.getByTestId("concerns").getByRole("button", { name: "Acknowledge" }).click();
  await expect(isha.getByTestId("concern-status")).toContainText("acknowledged");
  await expect(isha.getByTestId("concern")).toContainText("an acknowledgement is not a response");
  await isha.getByTestId("concerns").getByLabel("Response / review note").fill("Called back: transport arranged with the sister for the next visit.");
  await isha.getByTestId("concerns").getByRole("button", { name: "Record response" }).click();
  await expect(isha.getByTestId("concern-status")).toContainText("responded");
  await rao.goto(url(`/patients/${s.meera}/care`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await rao.getByTestId("concerns").getByLabel("Response / review note").fill("Reviewed; response is adequate. No change to the plan.");
  await rao.getByTestId("concerns").getByRole("button", { name: "Review and close" }).click();
  await expect(rao.getByTestId("concern-status")).toContainText("closed");
});

test("F4 · routine follow-up: a new result is reviewed, then the same plan continues unchanged", async () => {
  // Mira schedules the authored follow-up (administrative) and receives the follow-up blood panel.
  await mira.goto(url(`/patients/${s.meera}/care`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  const followUps = mira.getByTestId("follow-ups");
  await followUps.getByLabel("Appointment (relative day)").fill("14");
  await followUps.getByRole("button", { name: "Schedule", exact: true }).click();
  await announced(mira, "Follow-up scheduled");
  await expect(mira.getByTestId("follow-up-scheduled")).toContainText("appointment: Day 14");
  await receive(mira, s.meera, "meera-blood-day-6", "blood_panel", "Blood count panel");

  // The new result is unclassified clinical material: an unchanged continuation is blocked until Rao reviews it.
  await rao.goto(url(`/patients/${s.meera}/care`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  const decision = rao.getByTestId("encounter-decision");
  await decision.getByLabel("Rationale").fill("Routine review at the scheduled visit; the documented plan continues unchanged.");
  await decision.getByLabel("Next clinical timing (day)").fill("28");
  await decision.getByRole("button", { name: "Record encounter decision" }).click();
  await errorCode(rao, "plan_review_needed");
  await expect(decision.getByLabel("Rationale")).toHaveValue(/Routine review at the scheduled visit/); // the draft is preserved

  const other = await rao.context().newPage(); // second tab of the same session
  await other.goto(url("/impacts"));
  const impact = other.getByTestId("impact-meera");
  await impact.getByLabel("Rationale").fill("Follow-up counts are relevant to the routine review.");
  await impact.getByRole("button", { name: "Relevant to this plan" }).click();
  await announced(other, "Classified as relevant");
  await impact.getByLabel("Disposition").selectOption("retained");
  await impact.getByLabel("Review trigger").fill("Next routine review");
  await impact.getByLabel("Rationale").fill("Counts reviewed at the visit; the current plan is retained.");
  await impact.getByRole("button", { name: "Record disposition" }).click();
  await announced(other, "Impact disposition recorded");
  await other.close();

  // Back in the first tab the draft is still there; the same command now succeeds.
  await decision.getByRole("button", { name: "Record encounter decision" }).click();
  await announced(rao, "Encounter decision recorded");
  await expect(rao.getByTestId("follow-up-fulfilled")).toContainText("continue unchanged");
  await expect(rao.getByTestId("follow-up-open")).toContainText("Clinical timing: Day 28");
  // Same plan, same signature; trend shows both panels; the episode stays ongoing.
  await rao.goto(url(`/patients/${s.meera}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-current")).toContainText("Plan version 1");
  await expect(rao.getByTestId("plan-digest")).toHaveText(s.digest);
  await rao.goto(url(`/patients/${s.meera}`));
  await expect(rao.getByTestId("trends")).toContainText("Day -1: 8.4 g/dL");
  await expect(rao.getByTestId("trends")).toContainText("Day 6: 7.9 g/dL");
  await expect(rao.getByTestId("episode-status")).toContainText("ongoing");
  await expect(rao.getByTestId("timeline").locator("li[data-lane='actual']")).toHaveCount(1);
  await rao.getByText("Clinical and care timeline", { exact: true }).click();
  await expect(rao.getByTestId("timeline").locator("li[data-lane='planned']").first()).toBeVisible();
});

test("F5 · protocol v2: two separate impacts; Meera retains v1, Arun adopts through a new approved plan", async () => {
  // Arun independently uses the same shared protocol version (set up through the same HTTP API as Mira and Rao).
  const arun = await baseline(ws, "arun");
  s.arun = arun.pid;
  await assessAndDiscuss(ws, s.arun);
  const applicability = await acceptApplicability(ws, s.arun, s.protocol);
  s.arunPlan = await draftPlan(ws, s.arun, applicability);
  await submitPlan(ws, s.arunPlan);
  await signPlan(ws, s.arunPlan);
  await rao.goto(url(`/patients/${s.arun}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-current").getByRole("link", { name: "Open pinned protocol version" })).toHaveAttribute("href", new RegExp(s.protocol));

  // New question and evidence for the change (UI), then change proposal → v2.
  await rao.goto(url("/research"));
  await rao.getByRole("button", { name: "Evidence library", exact: true }).click();
  await rao.getByLabel("Source title").fill("VIALE-A — randomized-trial appraisal brief");
  await rao.getByLabel("Citation").fill("DiNardo et al. N Engl J Med 2020;383:617–629. https://pubmed.ncbi.nlm.nih.gov/32786187/");
  await rao.getByLabel("Evidence file (PDF, optional)").setInputFiles(input("viale-a-2020"));
  await rao.getByRole("button", { name: "Add source" }).click();
  await announced(rao, "Evidence source added");
  await rao.getByRole("button", { name: "Questions", exact: true }).click();
  await rao.getByRole("button", { name: "Insert demo question 2" }).click();
  await rao.getByRole("button", { name: "Open question" }).click();
  await rao.waitForURL(/\/research\/[0-9a-f-]{36}$/);
  const question2 = idFromUrl(rao);
  await rao.getByRole("button", { name: "Insert evidence appraisal example 2" }).click();
  await rao.getByTestId("passages").getByLabel("Evidence source").selectOption({ label: "VIALE-A — randomized-trial appraisal brief (v1)" });
  await rao.getByLabel(/^Finding 1:/).check();
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await reviewerDecides(sen, `/research/${question2}`, "Approve");
  // A new question and newly accepted evidence changed no patient decision.
  await rao.goto(url("/impacts"));
  await expect(rao.getByTestId("impacts-open")).toContainText("No open impact reviews.");

  await rao.goto(url(`/department/protocols/${s.protocol}`));
  await rao.getByLabel("Rationale / reason").fill("Add individual-context review before interpreting trial evidence.");
  await rao.getByRole("button", { name: "Open change proposal (successor draft)" }).click();
  await rao.waitForURL((u) => u.pathname.includes("/department/protocols/") && !u.pathname.endsWith(s.protocol));
  s.protocol2 = idFromUrl(rao);
  await rao.getByRole("button", { name: "Insert fictional pathway requirements (v2)" }).click();
  await expect(rao.getByTestId("requirement-REQ-TRIAL-CONTEXT")).toBeVisible();
  for (const box of await rao.getByTestId("evidence-picker").getByRole("checkbox").all()) await box.check();
  await rao.getByRole("button", { name: "Save and submit for independent review" }).click();
  await announced(rao, "submitted for independent review");
  await reviewerDecides(sen, `/department/protocols/${s.protocol2}`, "Approve");
  await rao.goto(url(`/department/protocols/${s.protocol2}`));
  await expect(rao.getByTestId("proposal")).toContainText(/changed: .*requirements/);
  await rao.getByRole("button", { name: "Publish version 2" }).click();
  await announced(rao, "Version 2 published");
  await expect(rao.getByTestId("protocol-record")).toContainText("v1 (superseded)");

  // Two independent impacts. Nothing changed either plan.
  await rao.goto(url("/impacts"));
  const open = rao.getByTestId("impacts-open");
  await expect(open.getByTestId("impact-meera")).toContainText("version 2 was published");
  await expect(open.getByTestId("impact-arun")).toBeVisible();
  // Meera retains v1 with a reason and a review trigger.
  const meeraImpact = open.getByTestId("impact-meera");
  await meeraImpact.getByLabel("Disposition").selectOption("retained");
  await meeraImpact.getByLabel("Rationale").fill("Caregiver contact is already documented in the discussion; the current plan is retained.");
  await meeraImpact.getByRole("button", { name: "Record disposition" }).click();
  await errorCode(rao, "review_trigger_required");
  await meeraImpact.getByLabel("Review trigger").fill("Revisit at the next routine review");
  await meeraImpact.getByRole("button", { name: "Record disposition" }).click();
  await announced(rao, "Impact disposition recorded");
  await expect(rao.getByTestId("impacts-closed").getByTestId("impact-meera").filter({ hasText: "version 2 was published" })).toContainText("retained");
  await expect(rao.getByTestId("impacts-open").getByTestId("impact-arun")).toBeVisible(); // Arun's is untouched

  // Arun: 'adopted' cannot close without a newly approved successor plan.
  const arunImpact = rao.getByTestId("impacts-open").getByTestId("impact-arun");
  await arunImpact.getByLabel("Disposition").selectOption("adopted");
  await expect(arunImpact.getByLabel("Newly approved successor plan")).toContainText("No approved successor plan exists yet");
  await arunImpact.getByLabel("Rationale").fill("Adopting version 2 for this patient.");
  await arunImpact.getByRole("button", { name: "Record disposition" }).click();
  await errorCode(rao, "adoption_requires_approved_plan");

  await rao.goto(url(`/patients/${s.arun}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-currency")).toContainText("review needed");
  await rao.getByRole("button", { name: "Start applicability review" }).click();
  await announced(rao, "Applicability draft started");
  await setCriteria(rao, { "REQ-IDENTITY": "match", "REQ-CONTEXT": "match", "REQ-DISCUSSION": "match", "REQ-VENUE": "match", "REQ-MOLECULAR": "unknown", "REQ-TRIAL-CONTEXT": "match" });
  await rao.getByRole("button", { name: "Accept applicability review" }).click();
  await announced(rao, "Applicability review accepted");
  await rao.getByRole("button", { name: "Draft a successor plan version" }).click();
  const editor = rao.getByTestId("plan-editor");
  await editor.getByLabel("Individual intent").fill("Continue preparation under protocol version 2, including the confirmed caregiver contact (fictional).");
  await editor.getByRole("button", { name: "Save and submit for signature" }).click();
  await announced(rao, "frozen for signature");
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  await announced(rao, "Plan version 2 approved");
  await expect(rao.getByTestId("plan-history")).toContainText("1 superseded version");

  await rao.goto(url("/impacts"));
  const adopt = rao.getByTestId("impacts-open").getByTestId("impact-arun");
  await adopt.getByLabel("Disposition").selectOption("adopted");
  await adopt.getByLabel("Newly approved successor plan").selectOption({ label: "Plan v2 (approved)" });
  await adopt.getByLabel("Rationale").fill("Adopted through the newly approved plan version 2.");
  await adopt.getByRole("button", { name: "Record disposition" }).click();
  await announced(rao, "Impact disposition recorded");
  await expect(rao.getByTestId("impacts-open")).toContainText("No open impact reviews.");
  // Meera's plan still pins v1 with the original signature.
  await rao.goto(url(`/patients/${s.meera}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-digest")).toHaveText(s.digest);
  await expect(rao.getByTestId("plan-currency")).toContainText("review current");
});

test("F6 · a source correction opens a scoped impact, blocks the stale action and is dispositioned", async () => {
  const before = await raoApi.get(`${W(ws)}/patients/${s.meera}/profile`);
  await receive(mira, s.meera, "meera-marrow-correction", "marrow", "Bone marrow report - corrected");
  await expect(mira.getByTestId("report-relation")).toContainText("correction");
  await expect(mira.getByTestId("observations")).toContainText("80 %");

  // The signed plan stays in force but is review-needed; a dependent new handoff is blocked.
  await mira.goto(url(`/patients/${s.meera}/care`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByTestId("task-STEP-FOLLOWUP").getByRole("button", { name: "Send handoff" }).click();
  await errorCode(mira, "plan_review_needed");
  // Historical care stays recordable.
  await isha.goto(url(`/patients/${s.meera}/care`));
  await isha.getByRole("tab", { name: "All sections", exact: true }).click();
  const care = isha.getByTestId("care-events");
  await care.getByLabel("Status", { exact: true }).selectOption("performed");
  await care.getByLabel("Actual time (relative day)").fill("4");
  await care.getByLabel("What happened").fill("Late entry: information leaflet handed over at a short visit.");
  await care.getByRole("button", { name: "Save care record" }).click();
  await announced(isha, "Care record saved");

  await rao.goto(url(`/patients/${s.meera}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-currency")).toContainText("review needed");
  await expect(rao.getByTestId("plan-disposition")).toContainText("active");
  await expect(rao.getByTestId("plan-digest")).toHaveText(s.digest); // the signature and its history are retained
  await expect(rao.getByTestId("currency-reasons")).toContainText("owner Dr. Rao");
  await rao.getByTestId("currency-reasons").getByRole("link", { name: "Open the impact queue" }).click();
  const impact = rao.getByTestId("impacts-open").getByTestId("impact-meera");
  await expect(impact).not.toContainText("needs classification"); // a pinned fact was corrected: relevance is certain
  await impact.getByLabel("Disposition").selectOption("retained");
  await impact.getByLabel("Review trigger").fill("Next routine review");
  await impact.getByLabel("Rationale").fill("Corrected cellularity reviewed; it does not alter the preparation pathway.");
  await impact.getByRole("button", { name: "Record disposition" }).click();
  await announced(rao, "Impact disposition recorded");

  await mira.goto(url(`/patients/${s.meera}/care`));
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByTestId("task-STEP-FOLLOWUP").getByRole("button", { name: "Send handoff" }).click();
  await expect(mira.getByTestId("task-status-STEP-FOLLOWUP")).toContainText("sent");

  // AE2: the current profile shows the correction; the earlier knowledge snapshot does not.
  await rao.goto(url(`/patients/${s.meera}`));
  await expect(rao.getByTestId("dimension-biology")).toContainText("80 %");
  await rao.goto(url(`/patients/${s.meera}/history`));
  await rao.getByLabel("Show the profile as it was known at").selectOption(String(before.knowledge_cutoff_seq > 0 ? (await raoApi.get(`${W(ws)}/patients/${s.meera}/snapshots`))[0].knowledge_cutoff_seq : ""));
  await expect(rao.getByTestId("cutoff")).toContainText("Historical view");
  await expect(rao.getByTestId("dimension-biology")).toContainText("90 %");
  await expect(rao.getByTestId("dimension-biology")).not.toContainText("80 %");
});

test("after an API server restart and fresh browser sessions, the whole journey is intact and still owned", async ({ browser }) => {
  // Kill the FastAPI server process; the test supervisor starts a brand-new process on the same PostgreSQL database.
  const pidBefore = execSync("lsof -ti tcp:8010 -sTCP:LISTEN").toString().trim();
  execSync(`kill -9 ${pidBefore.split("\n").join(" ")}`);
  const health = () => execSync('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/api/v1/health || true').toString().trim();
  await expect.poll(health, { timeout: 60_000 }).toBe("200");
  expect(execSync("lsof -ti tcp:8010 -sTCP:LISTEN").toString().trim()).not.toBe(pidBefore);

  // Server-side sessions are in PostgreSQL too: an existing browser session keeps working after the restart.
  await rao.goto(url(`/patients/${s.meera}/decisions`));
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-digest")).toHaveText(s.digest);
  // Brand-new browser contexts (a "browser restart") see the same durable state.
  const fresh = await signIn(browser, "sen");
  await fresh.goto(url(`/patients/${s.meera}/decisions`));
  await fresh.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(fresh.getByTestId("plan-digest")).toHaveText(s.digest);
  // Remaining obligations keep an owner and a next action; the episode is ongoing.
  await expect(fresh.getByTestId("exception-REQ-MOLECULAR-pending")).toContainText("Awaiting 1 more decision");
  await expect(fresh.getByTestId("exception-REQ-MOLECULAR-pending").getByRole("button", { name: "Approve exception" })).toBeVisible(); // Sen is the named next decider
  await fresh.goto(url("/today"));
  await expect(fresh.getByTestId("work-exception")).toContainText("Clinical exception awaiting your decision: REQ-MOLECULAR");
  await fresh.goto(url(`/patients/${s.meera}`));
  await expect(fresh.getByTestId("episode-status")).toContainText("ongoing");
  await fresh.goto(url(`/patients/${s.meera}/sources`));
  await fresh.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(fresh.getByTestId("expected-inputs")).toContainText("Final molecular report");
  await expect(fresh.getByTestId("expected-inputs")).toContainText("pending");
  await fresh.goto(url(`/patients/${s.meera}/care`));
  await fresh.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(fresh.getByTestId("follow-up-open")).toContainText("owner Mira");
  await expect(fresh.getByTestId("task-status-STEP-PLANNING-VISIT")).toContainText("draft");
  // The original bytes of a source are still served byte-identically.
  const docs = await raoApi.get(`${W(ws)}/sources?patient_id=${s.meera}`);
  const marrow = docs.find((d: any) => d.filename === "meera-marrow.pdf");
  const content = await raoApi.ctx.get(`/api/v1${W(ws)}/sources/${marrow.id}/content`);
  expect(content.headers()["x-content-sha256"]).toBe(marrow.sha256);
});
