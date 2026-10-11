import { expect, test } from "@playwright/test";
import { announced, as, intake, login, newWorkspace, register, signIn, W } from "./driver";

test("a patient demo link resumes after sign-in and an external return URL is ignored", async ({ browser }) => {
  const { ws, patients } = await newWorkspace("Patient link", "patients");
  const context = await browser.newContext();
  const page = await context.newPage();
  const path = `/w/${ws}/patients/${patients.arun}`;
  await login(page, "rao", path);
  await expect(page).toHaveURL(new RegExp(path + "$"));
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "rao", "/login?returnTo=https%3A%2F%2Fexample.com%2F");
  await expect(page).toHaveURL(/\/w\/[0-9a-f-]{36}\/today$/);
  await context.close();
});

test("oncologist sees recorded treatment and response, then checks the depth and source of related evidence", async ({ browser }) => {
  const { ws } = await newWorkspace("Oncologist clinical overview");
  const arun = await register(ws, "arun");
  for (const id of ["arun-referral", "arun-marrow", "arun-treatment-summary", "arun-response-assessment"]) await intake(ws, arun, id);
  const rao = await signIn(browser, "rao");
  await rao.goto(`/w/${ws}/patients/${arun}`);
  await expect(rao.getByTestId("treatment-outcomes")).toContainText("Azacitidine plus venetoclax");
  await expect(rao.getByTestId("treatment-outcomes")).toContainText("Febrile neutropenia");
  await expect(rao.getByTestId("treatment-outcomes")).toContainText("formal remission category not assigned");
  await expect(rao.getByTestId("disease-burden")).toContainText("34 %");
  await expect(rao.getByTestId("disease-burden")).toContainText("8 %");
  await expect(rao.getByTestId("patient-overview")).toContainText("No signed plan yet");
  await expect(rao.getByTestId("cutoff")).toHaveCount(0);
  await expect(rao.getByTestId("unresolved")).toHaveCount(0);
  await rao.getByRole("link", { name: "Review evidence or ask a case-linked question" }).click();
  await expect(rao.getByTestId("reference-pack")).toContainText("Review depth");
  await expect(rao.getByTestId("reference-viale-a-2020")).toContainText("431 patients");
  await expect(rao.getByTestId("reference-viale-a-2020")).toContainText("14.7 versus 9.6");
  await rao.getByTestId("reference-viale-a-2020").getByRole("button", { name: "Add evidence brief to library" }).click();
  await announced(rao, "Published evidence brief added");
  const sources = await (await as("rao")).get(`${W(ws)}/research/sources`);
  const sen = await signIn(browser, "sen");
  await sen.goto(`/w/${ws}/research/sources/${sources[0].id}`);
  await expect(sen.getByRole("link", { name: "Open original publication" })).toHaveAttribute("href", /pubmed/);
  await expect(sen.getByTestId("source-frame")).toBeVisible();
  await expect(sen.getByRole("button", { name: "Withdraw source" })).toHaveCount(0);
});
