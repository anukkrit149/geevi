/**
 * Server-enforced guards seen from the browser: scoped currency and stale signatures (AE5), failure
 * recovery with idempotent retries, unauthorized requests, account isolation and keyboard access.
 */
import { expect, test } from "@playwright/test";
import { announced, as, draftPlan, errorCode, intake, login, makeTasks, meeraPlanned, meeraReady, signIn, submitPlan, W } from "./driver";

test("AE5 · an unrelated task update in another session does not stale an open signature; a relevant result does", async ({ browser }) => {
  const s = await meeraPlanned("Stale signature");
  const tasks = await makeTasks(s.ws, s.plan, s.sop);
  const successor = await draftPlan(s.ws, s.meera, s.applicability, [s.venue], "Successor plan held open in a browser tab (fictional).");
  await submitPlan(s.ws, successor);
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${s.ws}/patients/${s.meera}/decisions`);
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  await expect(rao.getByTestId("sign-dialog")).toBeVisible();

  // Another session edits a task: an unrelated write that advances the workspace.
  const mira = await as("mira");
  await mira.post(`${W(s.ws)}/tasks/${tasks["STEP-CONFIRM-VENUE"].id}/update`, { expected_revision: tasks["STEP-CONFIRM-VENUE"].revision, note: "Moved by a day", owner_username: "mira" });
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  await announced(rao, "Plan version 2 approved");
  expect((await mira.get(`${W(s.ws)}/tasks`)).find((t: any) => t.sop_step_id === "STEP-CONFIRM-VENUE").note).toBe("Moved by a day"); // nothing was lost

  // A third version is frozen; while its dialog is open a relevant new report is associated by Mira.
  const third = await draftPlan(s.ws, s.meera, s.applicability, [s.venue], "Third plan version frozen before a new result arrived (fictional).");
  await submitPlan(s.ws, third);
  await rao.reload();
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  await intake(s.ws, s.meera, "meera-molecular-preliminary");
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  const summary = rao.getByTestId("sign-dialog").getByTestId("error-summary");
  await expect(summary).toHaveAttribute("data-error-code", "stale_dependency");
  await expect(summary).toBeFocused();
  await expect(summary).toContainText("by Mira");
  await expect(summary).toContainText("reopen the draft");
  await expect(rao.getByTestId("status")).not.toContainText("Plan version 3 approved");
  const view = await (await as("rao")).get(`${W(s.ws)}/plans/${third}`);
  expect(view.approval).toBeNull(); // no partial or stale signature exists on the server
  expect(view.plan.status).toBe("submitted");

  // Authorised path: the change is shown, the draft is reopened with its text intact, re-frozen and signed.
  await rao.keyboard.press("Escape");
  await rao.reload();
  await expect(rao.getByTestId("packet-changes")).toContainText("Relevant material changed");
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Reopen draft" }).click();
  await announced(rao, "Plan reopened as a draft");
  await expect(rao.getByTestId("plan-editor").getByLabel("Individual intent")).toHaveValue(/Third plan version frozen/);
  // The previously signed version stays in force while the draft is open.
  await expect(rao.getByTestId("plan-current")).toContainText("Plan version 2");
  // New material for a patient with a signed plan must be classified before a new approval.
  await rao.getByTestId("plan-editor").getByRole("button", { name: "Save and submit for signature" }).click();
  await announced(rao, "frozen for signature");
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  await expect(rao.getByTestId("sign-dialog").getByTestId("error-summary")).toHaveAttribute("data-error-code", "classification_required");
  await rao.keyboard.press("Escape");
  const other = await rao.context().newPage();
  await other.goto(`/w/${s.ws}/impacts`);
  const impact = other.getByTestId("impacts-open").getByTestId("impact-meera");
  await impact.getByLabel("Rationale").fill("Preliminary molecular report does not bear on the preparation pathway.");
  await impact.getByRole("button", { name: "Not relevant (close)" }).click();
  await announced(other, "Classified as not relevant");
  await other.close();
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  await rao.getByTestId("sign-dialog").getByRole("button", { name: "Sign plan" }).click();
  await announced(rao, "Plan version 3 approved");
});

test("failure recovery · a lost response shows no success; retrying re-sends the same command exactly once; drafts survive", async ({ browser }) => {
  const s = await meeraReady("Failure recovery");
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${s.ws}/patients/${s.meera}/decisions`);
  const editor = rao.getByTestId("plan-editor");
  const intent = "Individual intent typed before the connection dropped (fictional).";
  await editor.getByLabel("Individual intent").fill(intent);
  await editor.getByLabel(/REQ-VENUE — operational exception/).check();

  // 1. The request never reaches the server: nothing is saved, the draft text stays, no success is announced.
  await rao.route("**/patients/*/plans", (route) => (route.request().method() === "POST" ? route.abort("connectionfailed") : route.continue()));
  await editor.getByRole("button", { name: "Create plan draft" }).click();
  await errorCode(rao, "network_unknown_outcome");
  await expect(rao.getByTestId("error-summary").first()).toContainText("nothing is shown as saved");
  await expect(editor.getByLabel("Individual intent")).toHaveValue(intent);
  await expect(rao.getByTestId("status")).not.toContainText("Plan draft created");
  await rao.unroute("**/patients/*/plans");
  await editor.getByRole("button", { name: "Save and submit for signature" }).click();
  await announced(rao, "frozen for signature");

  // 2. The server commits the signature but the response is lost. The UI must not claim success.
  const commandIds: string[] = [];
  let drop = true;
  await rao.route("**/plans/*/approve", async (route) => {
    commandIds.push(route.request().postDataJSON().command_id);
    if (drop) {
      drop = false;
      await route.fetch(); // reaches FastAPI and commits
      await route.abort("connectionfailed"); // ...but the browser never sees the answer
    } else await route.continue();
  });
  await rao.getByTestId("plan-submitted").getByRole("button", { name: "Review and sign…" }).click();
  const dialog = rao.getByTestId("sign-dialog");
  await dialog.getByRole("button", { name: "Sign plan" }).click();
  await expect(dialog.getByTestId("error-summary")).toHaveAttribute("data-error-code", "network_unknown_outcome");
  await expect(dialog.getByTestId("error-summary")).toContainText("Not confirmed");
  await expect(rao.getByTestId("status")).not.toContainText("approved");
  // Retry: the SAME command id is re-sent and the stored receipt is returned; nothing is signed twice.
  await dialog.getByRole("button", { name: "Sign plan" }).click();
  await announced(rao, "Plan version 1 approved");
  expect(commandIds).toHaveLength(2);
  expect(commandIds[0]).toBe(commandIds[1]);
  const audit = await (await as("rao")).get(`${W(s.ws)}/audit`);
  expect(audit.filter((e: any) => e.action === "plan.approve")).toHaveLength(1);
  await expect(rao.getByTestId("plan-current")).toContainText("Plan version 1");

  // 3. A conflict from another session keeps the draft and names the newer revision.
  const mira = await signIn(browser, "mira");
  await mira.goto(`/w/${s.ws}/today`);
  await mira.getByLabel("Add a team note").fill("Bring the referral folder");
  await mira.getByRole("button", { name: "Add note" }).click();
  await announced(mira, "Note added");
  const note = (await (await as("mira")).get(`${W(s.ws)}/notes`))[0];
  await (await as("rao")).post(`${W(s.ws)}/notes/${note.id}/update`, { expected_revision: 1, text: "Changed elsewhere" });
  const stale = await (await as("mira")).fail(`${W(s.ws)}/notes/${note.id}/update`, { expected_revision: 1, text: "Stale overwrite attempt" });
  expect(stale.status).toBe(409);
  expect(stale.error.details).toEqual({ expected_revision: 1, current_revision: 2 });
});

test("unauthorized requests fail below the UI; controls are only a convenience", async ({ browser }) => {
  const s = await meeraReady("Authorization");
  const plan = await draftPlan(s.ws, s.meera, s.applicability, [s.venue]);
  await submitPlan(s.ws, plan);
  const view = await (await as("rao")).get(`${W(s.ws)}/plans/${plan}`);
  const signature = { expected_revision: view.plan.revision, packet_id: view.packet.id, digest: view.packet.target_digest };
  // No UI control exists for these accounts...
  const mira = await signIn(browser, "mira");
  await mira.goto(`/w/${s.ws}/patients/${s.meera}/decisions`);
  await expect(mira.getByTestId("plan-submitted")).toContainText("Awaiting the treating clinician");
  await expect(mira.getByRole("button", { name: "Review and sign…" })).toHaveCount(0);
  // ...and the server refuses the direct request, whatever actor fields or headers are forged.
  for (const user of ["mira", "sen", "isha", "operator"] as const) {
    const refused = await (await as(user)).fail(`${W(s.ws)}/plans/${plan}/approve`, { ...signature, actor: "rao", role: "oncologist" }, { "X-Actor": "rao", "X-Role": "oncologist" });
    expect([refused.status, refused.code]).toEqual([403, "actor_not_permitted"]);
  }
  expect((await (await as("rao")).get(`${W(s.ws)}/plans/${plan}`)).approval).toBeNull();
  // Missing CSRF token, foreign Origin and no session are all refused.
  const rao = await as("rao");
  const noCsrf = await rao.ctx.post(`/api/v1${W(s.ws)}/plans/${plan}/approve`, { data: { command_id: crypto.randomUUID(), ...signature } });
  expect((await noCsrf.json()).error.code).toBe("csrf_rejected");
  const foreign = await rao.ctx.post(`/api/v1${W(s.ws)}/plans/${plan}/approve`, { data: { command_id: crypto.randomUUID(), ...signature }, headers: { "X-CSRF-Token": rao.csrf, Origin: "https://evil.example" } });
  expect((await foreign.json()).error.code).toBe("origin_rejected");
  const anonymous = await browser.newContext();
  expect((await anonymous.request.get(`/api/v1${W(s.ws)}/patients`)).status()).toBe(401);
  // The operator moves data but has no clinical read scope.
  expect((await (await as("operator")).ctx.get(`/api/v1${W(s.ws)}/patients/${s.meera}/profile`)).status()).toBe(403);
});

test("exact deep links work; wrong or cross-workspace links fail safely; sign-out isolates accounts", async ({ browser }) => {
  const a = await meeraPlanned("Workspace A");
  const b = await meeraReady("Workspace B");
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, "rao");
  await page.goto(`/w/${a.ws}/patients/${a.meera}/decisions`);
  await expect(page.getByTestId("patient-name")).toHaveText("Meera (fictional)");
  await page.getByTestId("plan-current").getByRole("link", { name: "Open pinned protocol version" }).click();
  await expect(page).toHaveURL(new RegExp(`/w/${a.ws}/department/protocols/${a.protocol}$`));
  await expect(page.getByTestId("lifecycle")).toContainText("effective");
  // Workspace A's patient and protocol addressed through workspace B: nothing is shown.
  await page.goto(`/w/${b.ws}/patients/${a.meera}/decisions`);
  await expect(page.getByTestId("record-unavailable")).toBeVisible();
  await expect(page.getByTestId("patient-name")).toHaveCount(0);
  await page.goto(`/w/${b.ws}/department/protocols/${a.protocol}`);
  await expect(page.getByTestId("record-unavailable")).toBeVisible();
  await page.goto(`/w/00000000-0000-4000-8000-000000000000/today`);
  await expect(page.getByTestId("workspace-denied")).toBeVisible();

  // Sign out: the server session is revoked and cached records are gone.
  await page.goto(`/w/${a.ws}/patients/${a.meera}`);
  await expect(page.getByTestId("dimension-biology")).toContainText("Karyotype");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.request.get(`/api/v1${W(a.ws)}/patients`)).status()).toBe(401);
  await page.goBack();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByTestId("patient-name")).toHaveCount(0);
  // A different account in the same browser: no prior data is exposed and its own scope applies.
  await login(page, "operator");
  await expect(page).toHaveURL(/\/imports$/);
  await expect(page.getByTestId("identity-name")).toHaveText("Development operator");
  await page.goto(`/w/${a.ws}/patients/${a.meera}`);
  await expect(page.getByTestId("record-unavailable")).toBeVisible();
  await expect(page.getByText("Karyotype")).toHaveCount(0);
});

test("R32 · keyboard, dialog focus, error summary and status work at a narrow width", async ({ browser }) => {
  const s = await meeraReady("Keyboard");
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await login(page, "mira");
  await page.goto(`/w/${s.ws}/patients`);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true); // no horizontal overflow
  // Skip link is the first tab stop.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  // Open the dialog from the keyboard; focus moves into it, Escape closes it and focus returns to the opener.
  const opener = page.getByRole("button", { name: "Register patient" });
  await opener.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Display name")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
  // A rejected command moves focus to the announced error summary; the typed draft is kept.
  await opener.press("Enter");
  await dialog.getByLabel("Display name").fill("Duplicate identifier");
  await dialog.getByLabel("Identifier value").fill("GEEVI-DEMO-0001");
  await page.keyboard.press("Enter");
  const summary = dialog.getByTestId("error-summary");
  await expect(summary).toHaveAttribute("data-error-code", "identifier_in_use");
  await expect(summary).toBeFocused();
  await expect(summary).toHaveAttribute("role", "alert");
  await expect(dialog.getByLabel("Display name")).toHaveValue("Duplicate identifier");
  await page.keyboard.press("Escape");
  // Source links, status region and page-by-page viewer controls work at this width.
  await page.goto(`/w/${s.ws}/patients/${s.meera}`);
  await page.getByTestId("dimension-biology").getByRole("link", { name: "Open source region" }).first().click();
  await expect(page.getByTestId("source-highlight")).toBeVisible();
  await expect(page.getByTestId("page-indicator")).toHaveText("Page 1 of 1");
  await expect(page.getByTestId("status")).toHaveAttribute("aria-live", "polite");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
