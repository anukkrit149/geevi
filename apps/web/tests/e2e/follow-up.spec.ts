/** U10 in the browser: missed and rescheduled reviews, clinical versus administrative timing, escalation. */
import { expect, test } from "@playwright/test";
import { announced, meeraPlanned, signIn } from "./driver";

test("a missed review keeps an unknown outcome; a clinical timing change opens clinician review while a reschedule does not", async ({ browser }) => {
  const s = await meeraPlanned("Follow-up");
  const [mira, isha, rao] = await Promise.all((["mira", "isha", "rao"] as const).map((u) => signIn(browser, u)));
  const care = `/w/${s.ws}/patients/${s.meera}/care`;
  await mira.goto(care);
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  const panel = mira.getByTestId("follow-ups");
  await expect(panel).toContainText("authored by the signed plan");
  await panel.getByLabel("Appointment (relative day)").fill("14");
  await panel.getByRole("button", { name: "Schedule", exact: true }).click();
  await announced(mira, "Follow-up scheduled (no delivery recorded)");
  await expect(mira.getByTestId("care-events")).toContainText("No care events have been entered here."); // scheduling is not delivery
  await panel.getByLabel("Reason (for reschedule, miss, transfer)").fill("Patient did not attend; the reason is not yet known.");
  await panel.getByRole("button", { name: "Mark missed" }).click();
  await announced(mira, "Marked missed (outcome unknown)");
  await expect(mira.getByTestId("follow-up-missed")).toContainText("owner Mira");
  // Administrative reschedule needs a reason and opens no clinical review.
  await panel.getByLabel("Appointment (relative day)").fill("16");
  await panel.getByLabel("Reason (for reschedule, miss, transfer)").fill("Rebooked after the missed visit.");
  await panel.getByRole("button", { name: "Reschedule" }).click();
  await announced(mira, "Follow-up scheduled");
  await expect(mira.getByTestId("follow-up-scheduled")).toContainText("Clinical timing: Day 14 · appointment: Day 16");
  await panel.getByText(/^History/).click();
  await expect(panel).toContainText("missed — Mira — Patient did not attend; the reason is not yet known. (outcome: unknown)");
  await rao.goto(`/w/${s.ws}/patients/${s.meera}/decisions`);
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await expect(rao.getByTestId("plan-currency")).toContainText("review current");

  // Changing the AUTHORED clinical timing is not an administrative edit.
  await panel.getByLabel("Propose new clinical timing (day)").fill("30");
  await panel.getByLabel("Reason (for reschedule, miss, transfer)").fill("Family asked to delay the review.");
  await panel.getByRole("button", { name: "Request clinical timing change" }).click();
  await announced(mira, "sent for clinician review");
  await expect(mira.getByTestId("follow-up-scheduled")).toContainText("awaiting clinical review; the authored timing still stands");
  await rao.reload();
  await expect(rao.getByTestId("plan-currency")).toContainText("review needed");
  await rao.goto(`/w/${s.ws}/today`);
  await expect(rao.getByTestId("work-impact")).toContainText("authored clinical obligation");

  // A concern can be escalated to a named demo service; it stays open and owned until reviewed.
  await mira.goto(care);
  await mira.getByRole("tab", { name: "All sections", exact: true }).click();
  await mira.getByTestId("concerns").getByLabel("Concern as reported").fill("Patient asked whether the review can be done by phone.");
  await mira.getByTestId("concerns").getByRole("button", { name: "Record concern" }).click();
  await announced(mira, "Concern recorded");
  await isha.goto(care);
  await isha.getByRole("tab", { name: "All sections", exact: true }).click();
  await isha.getByTestId("concerns").getByLabel("Response / review note").fill("Question is beyond the care team; needs the clinician.");
  await isha.getByTestId("concerns").getByRole("button", { name: "Escalate to clinician" }).click();
  await expect(isha.getByTestId("concern-status")).toContainText("escalated");
  await expect(isha.getByTestId("concern")).toContainText("owner Dr. Rao");
  await rao.goto(care);
  await rao.getByRole("tab", { name: "All sections", exact: true }).click();
  await rao.getByTestId("concerns").getByLabel("Response / review note").fill("Trying to close before any response exists.");
  await rao.getByTestId("concerns").getByRole("button", { name: "Review and close" }).click();
  await expect(rao.getByTestId("error-summary").first()).toHaveAttribute("data-error-code", "response_required");
  await expect(rao.getByTestId("concern-status")).toContainText("escalated");
});
