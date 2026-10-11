import { expect, test } from "@playwright/test";
import { announced, as, errorCode, input, newWorkspace, register, signIn, upload, W } from "./driver";

test("separate source reports: receive, quarantine, associate, inspect the exact region and verify", async ({ browser }) => {
  const { ws } = await newWorkspace("Source review");
  const meera = await register(ws, "meera");
  await register(ws, "arun");
  const mira = await signIn(browser, "mira");
  await mira.goto(`/w/${ws}/patients/${meera}/sources`);
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();

  // Receive the marrow report through the upload form.
  await mira.getByLabel("Original file").setInputFiles(input("meera-marrow"));
  await mira.getByLabel("Report type", { exact: true }).selectOption("marrow");
  await mira.getByRole("button", { name: "Receive document" }).click();
  await expect(mira.getByTestId("upload-result")).toContainText("pending — 4 candidate finding(s)");
  await expect(mira.getByRole("link", { name: "Review received document", exact: true })).toHaveAttribute("href", /\/sources\/[0-9a-f-]{36}$/);

  // The same bytes again are refused; the stored original is kept.
  await mira.getByLabel("Original file").setInputFiles(input("meera-marrow"));
  await mira.getByRole("button", { name: "Receive document" }).click();
  await errorCode(mira, "duplicate_source");

  // A report naming another patient's identifier is quarantined, never attached.
  await mira.getByLabel("Original file").setInputFiles(input("arun-blood-day-2"));
  await mira.getByLabel("Report type", { exact: true }).selectOption("blood_panel");
  await mira.getByRole("button", { name: "Receive document" }).click();
  await expect(mira.getByTestId("upload-result")).toContainText("quarantined");
  await mira.getByRole("link", { name: "Blood count panel" }).click();
  await expect(mira.getByTestId("association")).toContainText("quarantined");
  await mira.getByLabel(/I checked the patient/).check();
  await mira.getByLabel("How was identity verified?").fill("Trying to attach it to Meera anyway");
  await mira.getByRole("button", { name: "Associate with this patient" }).click();
  await errorCode(mira, "invalid_association");

  // Marrow report: findings cannot be verified before identity review.
  await mira.goto(`/w/${ws}/patients/${meera}/sources`);
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByRole("link", { name: "Bone marrow morphology report" }).click();
  await expect(mira.getByTestId("source-canvas")).toHaveAttribute("data-rendered", "1");
  await expect(mira.getByTestId("candidate-Cellularity").getByRole("button", { name: "Verify" })).toHaveCount(0);
  await mira.getByLabel(/I checked the patient/).check();
  await mira.getByLabel("How was identity verified?").fill("Name, identifier and accession match the referral.");
  await mira.getByRole("button", { name: "Associate with this patient" }).click();
  await announced(mira, "Document associated");

  // Verifying requires inspecting the original region first (also enforced by the server).
  const cellularity = mira.getByTestId("candidate-Cellularity");
  await cellularity.getByRole("button", { name: "Verify" }).click();
  await errorCode(mira, "source_inspection_required");
  await cellularity.getByRole("button", { name: "Inspect source" }).click();
  const highlight = mira.getByTestId("source-highlight");
  await expect(highlight).toBeVisible();
  await expect(mira.getByTestId("source-frame")).toBeFocused();
  await expect(mira.getByTestId("source-frame")).toHaveAttribute("aria-label", /Highlighted source region: Cellularity: 90 %/);
  const box = await highlight.boundingBox();
  const frame = await mira.getByTestId("source-canvas").boundingBox();
  expect(box!.y - frame!.y).toBeGreaterThan(frame!.height * 0.3); // the Part B line sits well below the header
  expect(box!.y - frame!.y).toBeLessThan(frame!.height * 0.5);
  await cellularity.getByRole("button", { name: "Verify" }).click();
  await announced(mira, "Cellularity: source review recorded (verified)");
  await expect(cellularity.locator("[data-status='verified']")).toBeVisible();
  for (const name of ["Blast percentage", "Morphology", "Reported diagnosis"]) {
    const row = mira.getByTestId(`candidate-${name}`);
    await row.getByRole("button", { name: "Inspect source" }).click();
    await row.getByRole("button", { name: "Verify" }).click();
    await expect(row.locator("[data-status='verified']")).toBeVisible();
  }

  // The profile links each fact back to its exact source region, per specimen part.
  await mira.goto(`/w/${ws}/patients/${meera}`);
  const biology = mira.getByTestId("dimension-biology");
  await expect(biology).toContainText("Cellularity");
  await expect(biology).toContainText("Part B");
  await expect(biology).toContainText("result pending"); // 'to follow' wording stays an explicit pending state
  await biology.getByRole("link", { name: "Open source region" }).first().click();
  await expect(mira.getByTestId("source-highlight")).toBeVisible();
  await expect(mira).toHaveURL(/observation=/);
});

test("image-only original needs manual, source-linked entry; unauthorized content requests fail", async ({ browser }) => {
  const { ws } = await newWorkspace("Manual entry");
  const arun = await register(ws, "arun");
  const doc = (await upload(ws, arun, "arun-echo-scan")).target.id;
  const mira = await as("mira");
  await mira.post(`${W(ws)}/sources/${doc}/associate`, { expected_revision: 1, patient_id: arun, checked: true, note: "Identifier on the scan matches the referral." });

  const page = await signIn(browser, "mira");
  await page.goto(`/w/${ws}/patients/${arun}/sources/${doc}`);
  await expect(page.getByTestId("source-image")).toBeVisible();
  await expect(page.getByTestId("document-head")).toContainText("Image-only original");
  await expect(page.getByTestId("candidates")).toContainText("No candidates were extracted");
  // Region by keyboard-entered bounds (no pointer needed), then by dragging on the page.
  for (const [label, value] of [["Left", "0.04"], ["Top", "0.40"], ["Right", "0.5"], ["Bottom", "0.48"]]) await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByRole("button", { name: "Select region on page" }).click();
  const layer = await page.getByTestId("select-layer").boundingBox();
  await page.mouse.move(layer!.x + layer!.width * 0.05, layer!.y + layer!.height * 0.41);
  await page.mouse.down();
  await page.mouse.move(layer!.x + layer!.width * 0.45, layer!.y + layer!.height * 0.47, { steps: 4 });
  await page.mouse.up();
  await expect(page.getByLabel("Left", { exact: true })).not.toHaveValue("0.04");
  await page.getByLabel("Finding name").fill("LVEF");
  await page.getByLabel("Exact wording on the page").fill("LVEF: 55 %");
  await page.getByLabel("Value text").fill("55 %");
  await page.getByLabel("Units").fill("%");
  await page.getByLabel("Profile dimension").selectOption("fitness");
  await page.getByRole("button", { name: "Add finding for review" }).click();
  await announced(page, "Manual source-linked finding added");
  const row = page.getByTestId("candidate-LVEF");
  await expect(row).toContainText("manual entry");
  await row.getByRole("button", { name: "Inspect source" }).click();
  await expect(page.getByTestId("source-highlight")).toBeVisible();
  await row.getByRole("button", { name: "Verify" }).click();
  await announced(page, "LVEF: source review recorded (verified)");

  // Original bytes are served only to an authenticated account with record access.
  const content = `/api/v1${W(ws)}/sources/${doc}/content`;
  const anonymous = await browser.newContext();
  expect((await anonymous.request.get(content)).status()).toBe(401);
  expect((await (await as("operator")).ctx.get(content)).status()).toBe(403);
  const ok = await (await as("rao")).ctx.get(content);
  expect(ok.status()).toBe(200);
  expect(ok.headers()["content-type"]).toBe("image/png");
  expect(ok.headers()["content-security-policy"]).toContain("sandbox");
  // Active content is refused at upload.
  const html = Buffer.from("<html><script>alert(1)</script></html>").toString("base64");
  const refused = await mira.fail(`${W(ws)}/sources`, { patient_id: arun, filename: "x.html", media_type: "text/html", content_base64: html, doc_kind: "other" });
  expect(refused.code).toBe("unsupported_media");
});
