import { defineConfig } from "@playwright/test";

// Browser journeys run against the real FastAPI service, a dedicated PostgreSQL database and a
// production build of the Next.js app, using the seeded fictional development accounts.
const WEB = process.env.GEEVI_E2E_WEB_ORIGIN ?? "http://127.0.0.1:3010";
const API = `http://127.0.0.1:${process.env.GEEVI_E2E_API_PORT ?? "8010"}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: WEB, trace: "retain-on-failure", screenshot: "only-on-failure", viewport: { width: 1360, height: 900 } },
  webServer: [
    { command: "../../scripts/e2e-api.sh", url: `${API}/api/v1/health`, reuseExistingServer: false, timeout: 120_000, stdout: "pipe", stderr: "pipe" },
    {
      command: "pnpm exec next build && pnpm exec next start --hostname 127.0.0.1 --port 3010",
      url: `${WEB}/login`, reuseExistingServer: false, timeout: 240_000, stdout: "pipe", stderr: "pipe",
      env: { GEEVI_API_ORIGIN: API, GEEVI_NEXT_DIST: ".next-e2e" },
    },
  ],
});
