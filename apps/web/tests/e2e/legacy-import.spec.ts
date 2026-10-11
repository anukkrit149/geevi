/**
 * U2 in the browser: explicit legacy import. The old prototype directory is only READ here (one of
 * its fixture PDFs stands in for an original the user still holds); it is never modified, and no old
 * browser storage is read by the new origin.
 */
import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { announced, errorCode, input, ROOT, signIn } from "./driver";

const LEGACY = join(ROOT, "..", "product");
const ORIGINAL = join(LEGACY, "fixtures", "meera-intake.pdf");
const sha = (path: string) => createHash("sha256").update(readFileSync(path)).digest("hex");
const tree = (dir: string): string => readdirSync(dir, { withFileTypes: true }).filter((e) => e.name !== "node_modules").map((e) =>
  e.isDirectory() ? tree(join(dir, e.name)) : `${join(dir, e.name)}:${statSync(join(dir, e.name)).size}:${statSync(join(dir, e.name)).mtimeMs}`).join("|");

function legacyCase(hash: string) {
  return { id: "meera", revision: 4,
    documents: [{ id: "D1", hash, name: "meera-intake.pdf", title: "Intake report", pages: ["Reported diagnosis: AML\nNPM1: Pending"], pageCount: 2, kind: "pdf",
      layouts: [{ segments: [{ start: 0, end: 23, box: [0.1, 0.2, 0.4, 0.02] }] }], identity: "checked", claimed: "DEMO-MEERA",
      identityReview: { by: "coordinator", note: "Checked against referral", at: "2026-09-01T10:05:00.000Z" } }],
    facts: [{ id: "F1", docId: "D1", hash, label: "Reported diagnosis", category: "diagnosis", value: "AML", originalValue: "AML", quote: "Reported diagnosis: AML", page: 1,
      start: 0, end: 23, boxes: [[0.1, 0.2, 0.4, 0.02]], status: "verified", seen: true, review: { by: "Dr. Rao · demo", at: "2026-09-01T11:00:00.000Z", reason: "" } }],
    annotations: [], tasks: [{ id: "T1", text: "Prepare the initial profile", owner: "Coordinator", status: "open" }],
    plan: { text: "Review the diagnostic profile and discuss the next treatment step.", version: 2 },
    protocol: { text: "Legacy prose protocol for this patient", approval: { by: "Dr. Rao · demo", at: "2026-09-02T09:00:00.000Z" } },
    encounters: [], history: [], audit: [{ text: "Report received", role: "coordinator" }], messages: [] };
}

async function newImportWorkspace(page: Page, name: string): Promise<string> {
  await page.getByLabel("Workspace name").fill(name);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page.waitForURL((u) => u.pathname.endsWith("/imports") && page.url() !== "");
  await expect(page.getByRole("heading", { name: "Import & recovery" })).toBeVisible();
  await expect(page.locator(".page-head")).toContainText(name);
  return page.url().split("/w/")[1].split("/")[0];
}

test("explicit legacy snapshot with the exact original: staged, disclosed, activated, and legacy approvals stay unmapped", async ({ browser }) => {
  test.skip(!statSync(ORIGINAL, { throwIfNoEntry: false }), "legacy prototype fixtures are not present in this checkout");
  const before = tree(LEGACY);
  const dir = mkdtempSync(join(tmpdir(), "geevi-legacy-"));
  const hash = sha(ORIGINAL);
  const snapshot = join(dir, "legacy-stores.json");
  writeFileSync(snapshot, JSON.stringify({ "casebook-intake-v1": { meera: legacyCase(hash) }, "casebook-research-lab-v1": [{ id: "q1", title: "Legacy question", scope: "x", papers: [], applications: [] }] }));

  const operator = await signIn(browser, "operator");
  const ws = await newImportWorkspace(operator, `Legacy import ${Date.now()}`);
  const wizard = operator.getByTestId("legacy-import");
  await expect(wizard).toContainText("matched by SHA-256, never by filename");

  // A file that is not the exact original is refused (matching is by hash).
  await wizard.getByLabel("Captured snapshot or packet JSON").setInputFiles(snapshot);
  await wizard.getByLabel("Exact original files (PDF/PNG/JPEG)").setInputFiles(input("meera-cyto"));
  await wizard.getByRole("button", { name: "Stage legacy import" }).click();
  await errorCode(operator, "original_hash_mismatch");
  await expect(operator.getByTestId("jobs")).toContainText("Nothing has been staged");
  // The excluded older demo format is refused.
  const excluded = join(dir, "old-demo.json");
  writeFileSync(excluded, JSON.stringify({ "casebook-evidence-demo-v2": { anything: 1 } }));
  await wizard.getByLabel("Captured snapshot or packet JSON").setInputFiles(excluded);
  await wizard.getByLabel("Exact original files (PDF/PNG/JPEG)").setInputFiles([]);
  await wizard.getByRole("button", { name: "Stage legacy import" }).click();
  await errorCode(operator, "unsupported_legacy_format");

  // The real snapshot plus the exact original bytes (under a different filename).
  const renamed = join(dir, "renamed-by-user.pdf");
  writeFileSync(renamed, readFileSync(ORIGINAL));
  await wizard.getByLabel("Captured snapshot or packet JSON").setInputFiles(snapshot);
  await wizard.getByLabel("Exact original files (PDF/PNG/JPEG)").setInputFiles(renamed);
  await wizard.getByRole("button", { name: "Stage legacy import" }).click();
  await announced(operator, "staged for review");
  const job = operator.getByTestId("job-legacy");
  await expect(job.getByTestId("job-status")).toContainText("validated");
  await expect(job.getByTestId("job-incomplete")).toHaveCount(0);
  await expect(job.getByTestId("unmapped")).toContainText("1 protocol");
  await expect(job.getByTestId("disclosures")).toContainText("cannot read the legacy app's browser storage");
  await expect(job.getByTestId("disclosures")).toContainText("unmapped history and are not signatures");

  // Nothing is active until the operator explicitly activates.
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${ws}/patients`);
  await expect(rao.getByTestId("patient-list")).toContainText("No patients are registered");
  await job.getByRole("button", { name: "Activate in this workspace" }).click();
  await announced(operator, "Activated");
  await expect(operator.getByTestId("job-legacy").getByTestId("job-status")).toContainText("activated");

  // The imported workspace reloads from PostgreSQL with matching bytes and honest labels.
  await rao.reload();
  await rao.getByRole("link", { name: "Meera (legacy import)" }).click();
  await expect(rao.getByTestId("legacy-records")).toContainText("not reviewed publications and not signatures");
  await expect(rao.getByTestId("legacy-records")).toContainText("protocol");
  await rao.getByRole("link", { name: "Reports", exact: true }).click();
  await rao.getByRole("link", { name: "Intake report" }).click();
  await expect(rao.getByTestId("document-head")).toContainText(hash);
  await expect(rao.getByTestId("source-canvas")).toHaveAttribute("data-rendered", "1");
  const candidate = rao.getByTestId("candidate-Reported diagnosis");
  await expect(candidate).toContainText("legacy status: verified");
  await expect(candidate.locator("[data-status='unreviewed']")).toBeVisible(); // a legacy review is history, not current verification
  await candidate.getByRole("button", { name: "Inspect source" }).click();
  await expect(rao.getByTestId("source-highlight")).toBeVisible(); // legacy geometry preserved
  // No legacy approval became a publication or a signed plan.
  await rao.goto(`/w/${ws}/department`);
  await expect(rao.getByTestId("protocols")).toContainText("No protocol versions yet.");
  expect(tree(LEGACY)).toBe(before); // the legacy app was not touched
});

test("a metadata-only export packet is never a complete migration; its original stays unavailable", async ({ browser }) => {
  const dir = mkdtempSync(join(tmpdir(), "geevi-packet-"));
  const packet = join(dir, "case-export.json");
  writeFileSync(packet, JSON.stringify({ prototype: true, notClinicalAuthorization: true, createdAt: "2026-09-03T00:00:00Z", patient: { name: "Meera", id: "DEMO-MEERA" }, case: legacyCase("a".repeat(64)) }));
  const operator = await signIn(browser, "operator");
  const ws = await newImportWorkspace(operator, `Legacy packet ${Date.now()}`);
  const wizard = operator.getByTestId("legacy-import");
  await wizard.getByLabel("Captured snapshot or packet JSON").setInputFiles(packet);
  await wizard.getByRole("button", { name: "Stage legacy import" }).click();
  await announced(operator, "staged for review");
  const job = operator.getByTestId("job-legacy");
  await expect(job.getByTestId("job-incomplete")).toContainText("INCOMPLETE");
  await expect(job.getByTestId("missing-originals")).toContainText("Intake report");
  await expect(job.getByTestId("disclosures")).toContainText("not a complete migration");
  await job.getByRole("button", { name: "Activate in this workspace" }).click();
  await announced(operator, "Activated");

  const mira = await signIn(browser, "mira");
  await mira.goto(`/w/${ws}/patients`);
  await mira.getByRole("link", { name: "Meera (legacy import)" }).click();
  await mira.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(mira.getByTestId("source-list")).toContainText("unavailable");
  await mira.getByRole("link", { name: "Intake report" }).click();
  await expect(mira.getByTestId("original-unavailable")).toContainText("Supply the exact original file");
  await expect(mira.getByTestId("original-unavailable")).toContainText("Reported diagnosis: AML"); // captured legacy text, shown as plain text
  await expect(mira.getByTestId("candidate-Reported diagnosis").getByRole("button", { name: "Inspect source" })).toBeDisabled();
  await mira.getByTestId("candidate-Reported diagnosis").getByRole("button", { name: "Verify" }).click();
  await errorCode(mira, "original_unavailable");
});
