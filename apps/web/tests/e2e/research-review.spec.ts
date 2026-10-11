/** U5 in the browser: evidence review is independent of protocol publication and patient approval. */
import { expect, test } from "@playwright/test";
import { acceptedEvidence, announced, as, newWorkspace, signIn, W } from "./driver";

test("insufficient evidence concludes without a protocol or recommendation; a reopened draft keeps the accepted version", async ({ browser }) => {
  const { ws } = await newWorkspace("Research review");
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${ws}/research`);
  await rao.getByRole("button", { name: "Insert fictional question 3" }).click();
  await rao.getByRole("button", { name: "Open question" }).click();
  await rao.waitForURL(/\/research\/[0-9a-f-]{36}$/);
  await expect(rao.getByTestId("question")).toContainText("issues no patient recommendation");
  // "Evidence accepted" is impossible without an independently accepted appraisal.
  await rao.getByLabel("Conclusion").selectOption("evidence_accepted");
  await rao.getByLabel("Reasoning").fill("Looks sufficient to the author.");
  await rao.getByRole("button", { name: "Conclude question" }).click();
  await expect(rao.getByTestId("error-summary")).toHaveAttribute("data-error-code", "no_accepted_evidence");
  await rao.getByLabel("Conclusion").selectOption("insufficient_evidence");
  await rao.getByLabel("Reasoning").fill("No local or imported evidence addresses weekend scheduling.");
  await rao.getByRole("button", { name: "Conclude question" }).click();
  await expect(rao.getByTestId("question-status")).toContainText("insufficient evidence");
  await rao.goto(`/w/${ws}/department`);
  await expect(rao.getByTestId("protocols")).toContainText("No protocol versions yet.");

  // Reopening an accepted appraisal creates a successor draft; the accepted version is retained.
  const { question, appraisal } = await acceptedEvidence(ws);
  await rao.goto(`/w/${ws}/research/${question}`);
  await rao.getByRole("button", { name: "Open successor revision" }).click();
  await announced(rao, "the earlier version is retained");
  await expect(rao.getByTestId("appraisal-accepted")).toContainText("Appraisal v1");
  await expect(rao.getByTestId("appraisal-editor")).toBeVisible();
  // The author never gets a decision form; a reviewer without an assignment cannot decide either.
  await expect(rao.getByTestId("review-decision")).toHaveCount(0);
  // Withdrawing the source creates owned dependent-review work and flags the accepted appraisal.
  const raoApi = await as("rao");
  const source = (await raoApi.get(`${W(ws)}/research/sources`))[0];
  await raoApi.post(`${W(ws)}/research/sources/${source.id}/withdraw`, { expected_revision: source.revision, reason: "Withdrawn by its fictional authors." });
  await rao.reload();
  await expect(rao.getByTestId("appraisal-accepted")).toContainText("review needed");
  await rao.goto(`/w/${ws}/department`);
  await expect(rao.getByTestId("work-items")).toContainText("Evidence source withdrawn");
  await expect(rao.getByTestId("work-items")).toContainText("Owner Dr. Rao");
  expect((await raoApi.get(`${W(ws)}/research/appraisals`)).find((a: any) => a.id === appraisal).status).toBe("accepted");
});
