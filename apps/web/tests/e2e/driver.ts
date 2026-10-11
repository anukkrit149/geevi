/**
 * Test driver. Everything goes through the real HTTP API via the Next.js same-origin proxy, signed
 * in as the proper fictional development account. There is no database or state injection.
 */
import { expect, request, type APIRequestContext, type Browser, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export const ROOT = join(__dirname, "..", "..", "..", "..");
export const FIXTURES = join(ROOT, "fixtures", "department-journey");
export const WEB = process.env.GEEVI_E2E_WEB_ORIGIN ?? "http://127.0.0.1:3010";
export const MANIFEST = JSON.parse(readFileSync(join(FIXTURES, "manifest.json"), "utf8"));
export const SCENARIO = JSON.parse(readFileSync(join(FIXTURES, "scenario.json"), "utf8"));
export type User = "rao" | "sen" | "mira" | "isha" | "operator";
export const input = (id: string): string => join(FIXTURES, [...MANIFEST.inputs, ...MANIFEST.research].find((e: any) => e.id === id).file);
const entry = (id: string) => [...MANIFEST.inputs, ...MANIFEST.research].find((e: any) => e.id === id);

function credentials(): Record<string, string> {
  return JSON.parse(readFileSync(join(ROOT, "apps", "api", ".e2e-credentials.json"), "utf8"));
}

export class Actor {
  constructor(readonly ctx: APIRequestContext, readonly csrf: string, readonly accountId: string) {}
  private headers() {
    return { "X-CSRF-Token": this.csrf, Origin: WEB };
  }
  async get(path: string): Promise<any> {
    const r = await this.ctx.get(`/api/v1${path}`);
    expect(r.status(), `GET ${path}: ${await r.text()}`).toBe(200);
    return r.json();
  }
  async raw(method: "get" | "post", path: string, body?: Record<string, unknown>, headers: Record<string, string> = {}) {
    return method === "get" ? this.ctx.get(`/api/v1${path}`, { headers }) : this.ctx.post(`/api/v1${path}`, { data: { command_id: randomUUID(), ...body }, headers: { ...this.headers(), ...headers } });
  }
  async post(path: string, body: Record<string, unknown> = {}): Promise<any> {
    const r = await this.raw("post", path, body);
    expect(r.status(), `POST ${path}: ${await r.text()}`).toBe(200);
    return r.json();
  }
  async fail(path: string, body: Record<string, unknown> = {}, headers: Record<string, string> = {}): Promise<{ status: number; code: string; error: any }> {
    const r = await this.raw("post", path, body, headers);
    expect(r.status(), `POST ${path} unexpectedly succeeded`).toBeGreaterThanOrEqual(400);
    const error = (await r.json()).error;
    return { status: r.status(), code: error.code, error };
  }
}

const actors = new Map<string, Actor>();
export async function as(user: User): Promise<Actor> {
  if (!actors.has(user)) {
    const ctx = await request.newContext({ baseURL: WEB });
    const r = await ctx.post("/api/v1/session", { data: { username: user, password: credentials()[user] }, headers: { Origin: WEB } });
    expect(r.status(), await r.text()).toBe(200);
    const session = await r.json();
    actors.set(user, new Actor(ctx, session.csrf_token, session.account.id));
  }
  return actors.get(user)!;
}

/** Sign in through the real login form in an isolated browser context. */
export async function signIn(browser: Browser, user: User): Promise<Page> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, user);
  return page;
}

export async function login(page: Page, user: User, destination = "/login"): Promise<void> {
  await page.goto(destination);
  await expect(page.locator("form[data-ready='true']")).toBeVisible();
  await page.getByLabel("Username").fill(user);
  await page.getByLabel("Password").fill(credentials()[user]);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByTestId("identity")).toBeVisible();
}

export async function newWorkspace(name: string, load: "none" | "patients" | "sources" = "none"): Promise<{ ws: string; patients: Record<string, string> }> {
  const operator = await as("operator");
  const r = await operator.ctx.post("/api/v1/dev/workspaces", { data: { name: `${name} ${randomUUID().slice(0, 6)}`, load }, headers: { "X-CSRF-Token": operator.csrf, Origin: WEB } });
  expect(r.status(), await r.text()).toBe(200);
  const body = await r.json();
  return { ws: body.workspace_id, patients: body.patients };
}

export const W = (ws: string) => `/workspaces/${ws}`;
export const DAY = (n: number) => ({ value: n, unit: "day", anchor: "episode-day-0", precision: "day", basis: "fictional relative demonstration day" });
const b64 = (id: string) => readFileSync(input(id)).toString("base64");

// ---- journey steps through HTTP (used to reach a starting state quickly) ---------------------------

export async function register(ws: string, key: "meera" | "arun"): Promise<string> {
  return (await (await as("mira")).post(`${W(ws)}/patients`, MANIFEST.patients[key])).target.id;
}

export async function upload(ws: string, pid: string, id: string): Promise<any> {
  const e = entry(id);
  return (await as("mira")).post(`${W(ws)}/sources`, { patient_id: pid, filename: e.file.split("/").pop(), media_type: e.media_type, content_base64: b64(id),
    doc_kind: e.doc_kind, title: e.title, issuer: e.issuer, accession: e.accession, received_time: e.received_time });
}

export async function intake(ws: string, pid: string, id: string): Promise<{ doc: string; observations: Record<string, string> }> {
  const mira = await as("mira");
  const doc = (await upload(ws, pid, id)).target.id;
  await mira.post(`${W(ws)}/sources/${doc}/associate`, { expected_revision: 1, patient_id: pid, checked: true, note: "Identifier and accession checked against the referral." });
  const observations: Record<string, string> = {};
  for (const c of (await mira.get(`${W(ws)}/sources/${doc}`)).candidates) {
    const fix = id === "meera-flow" && c.assertion.analyte === "Myeloid markers";
    const result = await mira.post(`${W(ws)}/candidates/${c.id}/review`, { expected_revision: c.revision, source_inspected: true, disposition: fix ? "corrected" : "verified",
      ...(fix ? { reason: "Transcription corrected against the original wording.", corrected: { result_state: "reported_value" } } : {}) });
    observations[c.assertion.analyte] = result.data.observation_id;
  }
  return { doc, observations };
}

export const BASELINE = { meera: ["meera-referral", "meera-blood-day-minus-1", "meera-marrow", "meera-flow", "meera-cyto"], arun: ["arun-referral", "arun-blood-day-2", "arun-marrow", "arun-cyto"] };

export async function baseline(ws: string, key: "meera" | "arun"): Promise<{ pid: string; docs: Record<string, string> }> {
  const pid = await register(ws, key);
  const docs: Record<string, string> = {};
  for (const id of BASELINE[key]) docs[id] = (await intake(ws, pid, id)).doc;
  return { pid, docs };
}

async function decide(ws: string, packetId: string) {
  await (await as("sen")).post(`${W(ws)}/review-packets/${packetId}/decide`, { expected_revision: 1, decision: "approve" });
}

export async function acceptedEvidence(ws: string, which: "v1" | "v2" = "v1"): Promise<{ question: string; appraisal: string }> {
  const rao = await as("rao");
  const research = which === "v1" ? "eln-aml-2022" : "viale-a-2020";
  const e = entry(research);
  const question = (await rao.post(`${W(ws)}/research/questions`, SCENARIO.research[`question_${which}`])).target.id;
  const source = (await rao.post(`${W(ws)}/research/sources`, { title: e.title, citation: e.citation, source_label: e.label, filename: "brief.pdf", media_type: "application/pdf", content_base64: b64(research) })).target.id;
  const passage = (await rao.get(`${W(ws)}/research/sources`)).find((s: any) => s.id === source).passages.find((p: any) => p.text.startsWith("Finding 1"));
  const appraisal = (await rao.post(`${W(ws)}/research/questions/${question}/appraisals`, { ...SCENARIO.research[`appraisal_${which}`], citations: [{ source_id: source, passage_id: passage.id }] })).target.id;
  await decide(ws, (await rao.post(`${W(ws)}/research/appraisals/${appraisal}/submit`, { expected_revision: 1, reviewer_username: "sen" })).data.packet_id);
  return { question, appraisal };
}

async function publish(ws: string, kind: "protocols" | "sops", id: string, revision: number) {
  const rao = await as("rao");
  await decide(ws, (await rao.post(`${W(ws)}/${kind}/${id}/submit`, { expected_revision: revision, reviewer_username: "sen" })).data.packet_id);
  return rao.post(`${W(ws)}/${kind}/${id}/publish`, { expected_revision: revision + 2 });
}

export async function knowledge(ws: string): Promise<{ appraisal: string; protocol: string; sop: string }> {
  const rao = await as("rao");
  const { appraisal } = await acceptedEvidence(ws);
  const p = SCENARIO.protocol;
  const protocol = (await rao.post(`${W(ws)}/protocols`, { title: p.title, scope: p.scope, summary: p.v1.summary, requirements: p.v1.requirements, evidence: [appraisal] })).target.id;
  await publish(ws, "protocols", protocol, 1);
  const s = SCENARIO.sop;
  const sop = (await rao.post(`${W(ws)}/sops`, { title: s.title, purpose: s.purpose, escalation: s.escalation, steps: s.steps, protocol_version_id: protocol })).target.id;
  await publish(ws, "sops", sop, 1);
  return { appraisal, protocol, sop };
}

export async function publishV2(ws: string, v1: string, evidence: string[]): Promise<string> {
  const rao = await as("rao");
  const p = SCENARIO.protocol;
  const v2 = (await rao.post(`${W(ws)}/protocols/${v1}/revise`, { rationale: "Add individual-context review before interpreting trial evidence.", evidence })).target.id;
  await rao.post(`${W(ws)}/protocols/${v2}/save`, { expected_revision: 1, title: p.title, scope: p.scope, summary: p.v2.summary, requirements: p.v2.requirements, evidence });
  await publish(ws, "protocols", v2, 2);
  return v2;
}

export async function assessAndDiscuss(ws: string, pid: string): Promise<void> {
  await (await as("rao")).post(`${W(ws)}/patients/${pid}/assessments`, { narrative: "Fictional encounter assessment for workflow demonstration.", uncertainty: "Final molecular report outstanding." });
  await (await as("mira")).post(`${W(ws)}/patients/${pid}/discussions`, { participants: ["Patient", "Mira"], attributed_to: "patient", goals: "Wants appointments close to home where possible.", preferences: "Prefers the satellite clinic." });
}

export async function acceptApplicability(ws: string, pid: string, protocol: string, assessments: Record<string, string> = {}): Promise<string> {
  const rao = await as("rao");
  const review = (await rao.post(`${W(ws)}/patients/${pid}/applicability`, { protocol_version_id: protocol })).target.id;
  const current = (await rao.get(`${W(ws)}/patients/${pid}/applicability`)).find((a: any) => a.id === review);
  const pick = { "REQ-MOLECULAR": "unknown", ...assessments } as Record<string, string>;
  const criteria = current.criteria.map((c: any) => ({ requirement_id: c.requirement_id, assessment: pick[c.requirement_id] ?? "match",
    rationale: (pick[c.requirement_id] ?? "match") === "match" ? "" : "Documented at the fictional encounter.", supporting: [] }));
  await rao.post(`${W(ws)}/applicability/${review}/save`, { expected_revision: current.revision, criteria });
  await rao.post(`${W(ws)}/applicability/${review}/accept`, { expected_revision: current.revision + 1 });
  return review;
}

export async function approvedVenueException(ws: string, pid: string, protocol: string): Promise<string> {
  const rao = await as("rao");
  const spec = SCENARIO.exceptions.venue;
  const id = (await rao.post(`${W(ws)}/patients/${pid}/exceptions`, { protocol_version_id: protocol, requirement_id: spec.requirement_id, exception_type: spec.type,
    departure: spec.departure, rationale: spec.rationale, review_trigger: "Review if travel circumstances change." })).target.id;
  await rao.post(`${W(ws)}/exceptions/${id}/decide`, { expected_revision: 1, decision: "approve", rationale: "Reviewed against the documented discussion." });
  return id;
}

export async function draftPlan(ws: string, pid: string, applicability: string, exceptions: string[] = [], intent = "Complete case preparation and arrange the planning visit as documented (fictional)."): Promise<string> {
  const rao = await as("rao");
  const discussion = (await rao.get(`${W(ws)}/patients/${pid}/discussions`)).at(-1).id;
  return (await rao.post(`${W(ws)}/patients/${pid}/plans`, { applicability_id: applicability, discussion_id: discussion, exception_ids: exceptions, intent,
    obligations: [{ id: "OBL-ROUTINE-REVIEW", purpose: "Routine follow-up review", due: DAY(14), owner_username: "mira" }] })).target.id;
}

export async function submitPlan(ws: string, plan: string): Promise<void> {
  const rao = await as("rao");
  await rao.post(`${W(ws)}/plans/${plan}/submit`, { expected_revision: (await rao.get(`${W(ws)}/plans/${plan}`)).plan.revision });
}

export async function signPlan(ws: string, plan: string): Promise<void> {
  const rao = await as("rao");
  const view = await rao.get(`${W(ws)}/plans/${plan}`);
  await rao.post(`${W(ws)}/plans/${plan}/approve`, { expected_revision: view.plan.revision, packet_id: view.packet.id, digest: view.packet.target_digest });
}

export type State = { ws: string; protocol: string; sop: string; appraisal: string; meera: string; docs: Record<string, string>; applicability: string; venue: string; plan?: string };

/** Meera with sources, assessment, discussion, accepted applicability and approved venue exception. */
export async function meeraReady(name: string): Promise<State> {
  const { ws } = await newWorkspace(name);
  const k = await knowledge(ws);
  const { pid, docs } = await baseline(ws, "meera");
  await assessAndDiscuss(ws, pid);
  const applicability = await acceptApplicability(ws, pid, k.protocol, { "REQ-VENUE": "difference" });
  return { ws, ...k, meera: pid, docs, applicability, venue: await approvedVenueException(ws, pid, k.protocol) };
}

export async function meeraPlanned(name: string): Promise<State & { plan: string }> {
  const s = await meeraReady(name);
  const plan = await draftPlan(s.ws, s.meera, s.applicability, [s.venue]);
  await submitPlan(s.ws, plan);
  await signPlan(s.ws, plan);
  return { ...s, plan };
}

export async function arunPlanned(ws: string, protocol: string): Promise<{ arun: string; arunPlan: string }> {
  const { pid } = await baseline(ws, "arun");
  await assessAndDiscuss(ws, pid);
  const plan = await draftPlan(ws, pid, await acceptApplicability(ws, pid, protocol));
  await submitPlan(ws, plan);
  await signPlan(ws, plan);
  return { arun: pid, arunPlan: plan };
}

export async function makeTasks(ws: string, plan: string, sop: string): Promise<Record<string, any>> {
  const mira = await as("mira");
  const steps = SCENARIO.sop.steps.map((s: any) => s.id);
  await mira.post(`${W(ws)}/plans/${plan}/tasks`, { sop_version_id: sop, owners: Object.fromEntries(steps.map((s: string) => [s, "isha"])), due: {} });
  return Object.fromEntries((await mira.get(`${W(ws)}/tasks`)).filter((t: any) => t.plan_version_id === plan).map((t: any) => [t.sop_step_id, t]));
}

/** Wait for the durable-result announcement. Nothing is asserted from optimistic UI state. */
export async function announced(page: Page, text: string | RegExp): Promise<void> {
  await expect(page.getByTestId("status")).toContainText(text);
}

export async function errorCode(page: Page, code: string): Promise<void> {
  await expect(page.getByTestId("error-summary").first()).toHaveAttribute("data-error-code", code);
}
