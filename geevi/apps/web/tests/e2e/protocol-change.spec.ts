/** U11 in the browser: withdrawal and "more information" leave plans untouched and review owned. */
import { expect, test } from "@playwright/test";
import { acceptedEvidence, announced, arunPlanned, as, meeraPlanned, publishV2, signIn, W } from "./driver";

test("more-information keeps an impact open; withdrawal blocks new selection, nominates review and never changes a plan", async ({ browser }) => {
  const s = await meeraPlanned("Protocol change");
  const a = await arunPlanned(s.ws, s.protocol);
  const second = await acceptedEvidence(s.ws, "v2");
  const v2 = await publishV2(s.ws, s.protocol, [s.appraisal, second.appraisal]);
  const raoApi = await as("rao");
  const meeraBefore = await raoApi.get(`${W(s.ws)}/plans/${s.plan}`);

  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${s.ws}/impacts`);
  const open = rao.getByTestId("impacts-open");
  await expect(open.locator(".item[data-state]")).toHaveCount(2);
  const meera = open.getByTestId("impact-meera");
  await meera.getByLabel("Disposition").selectOption("more_information");
  await meera.getByLabel("Rationale").fill("Need to confirm the caregiver contact with the family first.");
  await meera.getByRole("button", { name: "Record disposition" }).click();
  await announced(rao, "Impact disposition recorded");
  await expect(rao.getByTestId("impacts-open").getByTestId("impact-meera").getByTestId("impact-state")).toContainText("more information");
  await expect(rao.getByTestId("impacts-open").getByTestId("impact-arun").getByTestId("impact-state")).toContainText("open"); // independent of Meera's

  // Withdraw v2: history is preserved, new selection is impossible, dependants are nominated.
  await rao.goto(`/w/${s.ws}/department/protocols/${v2}`);
  await rao.getByLabel("Rationale / reason").fill("Withdrawn pending rewrite of the caregiver requirement.");
  await rao.getByRole("button", { name: "Withdraw this version" }).click();
  await announced(rao, "Version withdrawn");
  await expect(rao.getByTestId("lifecycle")).toContainText("withdrawn");
  await expect(rao.getByTestId("publications")).toContainText("Withdrawn by Dr. Rao");
  await expect(rao.getByTestId("publications")).toContainText("Published by Dr. Rao");
  await rao.goto(`/w/${s.ws}/patients/${a.arun}/decisions`);
  await expect(rao.getByTestId("applicability").getByLabel("Effective protocol version")).toContainText("v1"); // v1 is effective again; v2 is not offered
  await expect(rao.getByTestId("applicability").getByLabel("Effective protocol version")).not.toContainText("v2");
  const refused = await raoApi.fail(`${W(s.ws)}/patients/${a.arun}/applicability`, { protocol_version_id: v2 });
  expect(refused.code).toBe("protocol_not_selectable");
  // No plan was changed by publication or withdrawal; no automatic stop was issued.
  const meeraAfter = await raoApi.get(`${W(s.ws)}/plans/${s.plan}`);
  expect(meeraAfter.plan).toEqual(meeraBefore.plan);
  expect(meeraAfter.approval).toEqual(meeraBefore.approval);
  expect(meeraAfter.disposition).toBe("active");
  await expect(rao.getByTestId("plan-current")).toContainText("disposition: active");
});
