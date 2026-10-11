/** U9 in the browser: handoffs are sent, received, returned with a reason, and care is attributed. */
import { expect, test } from "@playwright/test";
import { announced, makeTasks, meeraPlanned, signIn } from "./driver";

test("a returned handoff keeps its owner and reason; an administrative edit leaves clinical review current; external care keeps the transcriber distinct", async ({ browser }) => {
  const s = await meeraPlanned("Handoff");
  await makeTasks(s.ws, s.plan, s.sop);
  const [mira, isha, rao] = await Promise.all((["mira", "isha", "rao"] as const).map((u) => signIn(browser, u)));
  const care = `/w/${s.ws}/patients/${s.meera}/care`;
  await mira.goto(care);
  await mira.getByTestId("task-STEP-CONFIRM-VENUE").getByRole("button", { name: "Send handoff" }).click();
  await expect(mira.getByTestId("task-status-STEP-CONFIRM-VENUE")).toContainText("sent");

  await isha.goto(care);
  const task = isha.getByTestId("task-STEP-CONFIRM-VENUE");
  await task.getByRole("button", { name: "Mark received" }).click();
  await expect(isha.getByTestId("task-status-STEP-CONFIRM-VENUE")).toContainText("received");
  await task.getByRole("button", { name: "Return", exact: true }).click();
  await expect(isha.getByTestId("error-summary").first()).toHaveAttribute("data-error-code", "reason_required");
  await task.getByLabel(/Reason or completion evidence/).fill("The patient's phone number is missing from the packet.");
  await task.getByRole("button", { name: "Return", exact: true }).click();
  await announced(isha, "Handoff returned");

  await mira.reload();
  const returned = mira.getByTestId("task-STEP-CONFIRM-VENUE");
  await expect(mira.getByTestId("task-status-STEP-CONFIRM-VENUE")).toContainText("returned");
  await expect(returned).toContainText("Owner: Isha");
  await returned.getByText("Handoff history").click();
  await expect(returned).toContainText("returned — Isha");
  await expect(returned).toContainText("phone number is missing");
  // Administrative edit: due and note change; no clinical review goes stale.
  await returned.getByRole("button", { name: "Edit owner / due" }).click();
  await returned.getByLabel("Due (relative day)").fill("5");
  await returned.getByLabel("Note").fill("Phone number added to the packet.");
  await returned.getByRole("button", { name: "Save task changes" }).click();
  await announced(mira, "Task updated");
  await expect(returned).toContainText("due Day 5");
  await rao.goto(`/w/${s.ws}/patients/${s.meera}/decisions`);
  await expect(rao.getByTestId("plan-currency")).toContainText("review current");

  // External report: performer and transcribing account are recorded separately; time may be unknown.
  await isha.reload();
  const form = isha.getByTestId("care-events");
  await form.getByLabel("Status", { exact: true }).selectOption("performed");
  await form.getByLabel("Source of this record").selectOption("external_report");
  await form.getByLabel("Actual time (relative day)").fill("4");
  await form.getByLabel("What happened").fill("Blood draw at the outside clinic, per the faxed note.");
  await form.getByRole("button", { name: "Save care record" }).click();
  await expect(isha.getByTestId("error-summary").first()).toHaveAttribute("data-error-code", "performer_required");
  await form.getByLabel("Performed by (external)").fill("Nurse at Fictional Lakeside Clinic");
  await form.getByRole("button", { name: "Save care record" }).click();
  await announced(isha, "Care record saved");
  await expect(form.getByTestId("care-performed")).toContainText("Performed by Nurse at Fictional Lakeside Clinic");
  await expect(form.getByTestId("care-performed")).toContainText("transcribed from an external report by Isha");
  await form.getByLabel("Status", { exact: true }).selectOption("unknown");
  await form.getByLabel("Source of this record").selectOption("direct");
  await form.getByLabel("What happened").fill("Outside visit reported by phone; details not confirmed.");
  await form.getByRole("button", { name: "Save care record" }).click();
  await expect(form.getByTestId("care-unknown")).toContainText("time not recorded");
});
