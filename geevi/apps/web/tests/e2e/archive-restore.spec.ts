/** U13 in the browser: full backup download, staged restore into another workspace, and refusal of bad archives. */
import { expect, test } from "@playwright/test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { announced, as, errorCode, intake, makeTasks, meeraPlanned, signIn, W } from "./driver";

test("full backup → staged restore → explicit activation reproduces signatures, history and exact original bytes", async ({ browser }) => {
  const s = await meeraPlanned("Archive source");
  await makeTasks(s.ws, s.plan, s.sop);
  await intake(s.ws, s.meera, "meera-marrow-correction"); // an amendment and an open impact travel with the archive
  const raoApi = await as("rao");
  const planBefore = await raoApi.get(`${W(s.ws)}/plans/${s.plan}`);
  const dir = mkdtempSync(join(tmpdir(), "geevi-archive-"));

  const operator = await signIn(browser, "operator");
  await operator.goto(`/w/${s.ws}/imports`);
  const panel = operator.getByTestId("export");
  // A review-only packet is clearly not a backup.
  const [review] = await Promise.all([operator.waitForEvent("download"), panel.getByRole("button", { name: "Download review-only packet" }).click()]);
  await expect(panel.getByTestId("export-result")).toContainText("INCOMPLETE — not a full backup");
  await expect(panel.getByTestId("incomplete-reasons")).toContainText("original bytes are not included");
  expect(review.suggestedFilename()).toContain("review-packet");
  // The full backup includes every original.
  const [download] = await Promise.all([operator.waitForEvent("download"), panel.getByRole("button", { name: "Download full backup" }).click()]);
  await expect(panel.getByTestId("export-result")).toContainText("Complete backup");
  await expect(panel.getByTestId("export-result")).toContainText("7 of 7 with intact bytes");
  await expect(panel.getByTestId("export-result")).toContainText("password hashes");
  const archivePath = join(dir, "backup.json");
  await download.saveAs(archivePath);
  const archive = JSON.parse(readFileSync(archivePath, "utf8"));
  expect(archive.complete).toBe(true);
  expect(JSON.stringify(archive.tables)).not.toContain("argon2");

  // Restore beside the existing records, in a new empty workspace.
  await operator.getByLabel("Workspace name").fill(`Restore target ${Date.now()}`);
  await operator.getByRole("button", { name: "Create workspace" }).click();
  await expect(operator.locator(".page-head")).toContainText("Restore target");
  const target = operator.url().split("/w/")[1].split("/")[0];
  expect(target).not.toBe(s.ws);

  // A tampered original and an injected account table are refused before anything is staged.
  const tampered = structuredClone(archive);
  tampered.originals[0].base64 = Buffer.from("%PDF-not the original").toString("base64");
  writeFileSync(join(dir, "tampered.json"), JSON.stringify(tampered));
  const restore = operator.getByTestId("archive-restore");
  await restore.getByLabel("Archive file").setInputFiles(join(dir, "tampered.json"));
  await restore.getByRole("button", { name: "Validate into staging" }).click();
  await errorCode(operator, "original_hash_mismatch");
  const hostile = structuredClone(archive);
  hostile.tables.workspace_grants = [{ username: "operator", capabilities: ["plan.approve"] }];
  writeFileSync(join(dir, "hostile.json"), JSON.stringify(hostile));
  await restore.getByLabel("Archive file").setInputFiles(join(dir, "hostile.json"));
  await restore.getByRole("button", { name: "Validate into staging" }).click();
  await errorCode(operator, "forbidden_archive_content");
  await expect(operator.getByTestId("jobs")).toContainText("Nothing has been staged");

  // The intact archive validates into staging; nothing is active until the operator activates.
  await restore.getByLabel("Archive file").setInputFiles(archivePath);
  await restore.getByRole("button", { name: "Validate into staging" }).click();
  await announced(operator, "validated into staging");
  const job = operator.getByTestId("job-archive");
  await expect(job.getByTestId("job-status")).toContainText("validated");
  await expect(job.getByTestId("job-incomplete")).toHaveCount(0);
  await expect(job.getByTestId("disclosures")).toContainText("Accounts, sessions and capability grants are never imported");
  expect(await raoApi.get(`${W(target)}/patients`)).toEqual([]);
  await job.getByRole("button", { name: "Activate in this workspace" }).click();
  await announced(operator, "Activated");

  // A clinician in a fresh browser context sees the same journey in the restored workspace.
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${target}/patients/${s.meera}/decisions`);
  await expect(rao.getByTestId("plan-digest")).toHaveText(planBefore.approval.target_digest);
  await expect(rao.getByTestId("plan-currency")).toContainText("review needed"); // the open impact was restored with its owner
  await rao.goto(`/w/${target}/patients/${s.meera}/sources/${s.docs["meera-marrow"]}`);
  await expect(rao.getByTestId("source-canvas")).toHaveAttribute("data-rendered", "1");
  await expect(rao.getByTestId("observations")).toContainText("Corrected by issuer report version 2");
  const restored = await raoApi.get(`${W(target)}/plans/${s.plan}`);
  expect(restored.plan).toEqual(planBefore.plan);
  expect(restored.approval).toEqual(planBefore.approval);
  const bytes = async (ws: string) => (await raoApi.ctx.get(`/api/v1${W(ws)}/sources/${s.docs["meera-marrow"]}/content`)).body();
  expect(Buffer.compare(await bytes(target), await bytes(s.ws))).toBe(0);
  // The source workspace was not rewritten, and the operator gained no clinical authority from the archive.
  expect((await raoApi.get(`${W(s.ws)}/plans/${s.plan}`)).plan).toEqual(planBefore.plan);
  expect((await (await as("operator")).ctx.get(`/api/v1${W(target)}/patients`)).status()).toBe(403);
});
