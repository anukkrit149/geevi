import { expect, test } from "@playwright/test";
import { login, newWorkspace, signIn } from "./driver";

test("focused plan views preserve drafts and prerequisite links open the right section", async ({ browser }) => {
  const { ws, patients } = await newWorkspace("Focused views", "patients");
  const page = await (await browser.newContext()).newPage();
  await login(page, "rao", `/w/${ws}/patients/${patients.arun}/decisions#discussion`);
  const discussion = page.getByRole("tab", { name: "Patient discussion", exact: true });
  await expect(discussion).toHaveAttribute("aria-selected", "true");
  await page.getByLabel("Participants (comma separated)").fill("Draft participant");
  await page.getByRole("tab", { name: "Individual plan", exact: true }).click();
  await expect(page.getByLabel("Participants (comma separated)")).toBeHidden();
  await page.getByLabel("Individual intent").fill("Draft intent kept while reviewing inputs");
  await page.getByRole("link", { name: "Review applicability", exact: true }).click();
  await expect(page.getByRole("tab", { name: "Applicability", exact: true })).toHaveAttribute("aria-selected", "true");
  await discussion.click();
  await expect(page.getByLabel("Participants (comma separated)")).toHaveValue("Draft participant");
  await page.getByRole("tab", { name: "Individual plan", exact: true }).click();
  await expect(page.getByLabel("Individual intent")).toHaveValue("Draft intent kept while reviewing inputs");
  await page.getByRole("tab", { name: "All sections" }).click();
  await expect(page.getByLabel("Participants (comma separated)")).toBeVisible();
  await page.context().close();
});

test("patient search distinguishes no matches from an empty caseload", async ({ browser }) => {
  const { ws } = await newWorkspace("Patient search", "patients");
  const page = await signIn(browser, "rao");
  await page.goto(`/w/${ws}/patients`);
  const search = page.getByRole("textbox", { name: /Find a patient/ });
  await search.fill("no-such-person");
  await expect(page.getByRole("heading", { name: "No matching patients" })).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(page.getByRole("link", { name: "Arun (fictional)", exact: true })).toBeVisible();
  await page.context().close();
});

test("mobile navigation, theme persistence and reduced motion work together", async ({ browser }) => {
  const { ws } = await newWorkspace("Mobile workspace", "patients");
  const page = await signIn(browser, "rao");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`/w/${ws}/patients`);
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeHidden();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
  await page.getByRole("button", { name: "Theme: system. Switch to light", exact: true }).click();
  await page.getByRole("button", { name: "Theme: light. Switch to dark", exact: true }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator(".page-head").evaluate((el) => getComputedStyle(el).animationName)).toBe("none");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Research", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Research", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
  await page.context().close();
});
