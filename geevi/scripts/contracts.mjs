#!/usr/bin/env node
// Generates (or checks) the API contract: FastAPI OpenAPI -> contracts/openapi.json -> TypeScript types.
// The TypeScript schema is never hand-maintained; `check` fails when either artifact is stale.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const openapiPath = join(root, "contracts", "openapi.json");
const typesPath = join(root, "apps", "web", "src", "lib", "api", "schema.d.ts");
const mode = process.argv[2] ?? "check";

function openapi() {
  return execFileSync("uv", ["run", "--project", join(root, "apps", "api"), "python", "-m", "app.export_openapi"], {
    cwd: join(root, "apps", "api"), encoding: "utf8", maxBuffer: 64 * 1024 * 1024, env: { ...process.env, GEEVI_DEV_MODE: "false" },
  });
}
function types(specPath, outPath) {
  execFileSync("pnpm", ["--dir", join(root, "apps", "web"), "exec", "openapi-typescript", specPath, "-o", outPath, "--default-non-nullable", "false"], { stdio: "pipe" });
  return readFileSync(outPath, "utf8");
}

const spec = openapi();
if (mode === "generate") {
  writeFileSync(openapiPath, spec);
  types(openapiPath, typesPath);
  console.log("contracts: wrote contracts/openapi.json and apps/web/src/lib/api/schema.d.ts");
} else {
  const temp = mkdtempSync(join(tmpdir(), "geevi-contracts-"));
  const tempSpec = join(temp, "openapi.json");
  writeFileSync(tempSpec, spec);
  const stale = [];
  if (readFileSync(openapiPath, "utf8") !== spec) stale.push("contracts/openapi.json");
  if (readFileSync(typesPath, "utf8") !== types(tempSpec, join(temp, "schema.d.ts"))) stale.push("apps/web/src/lib/api/schema.d.ts");
  if (stale.length) {
    console.error(`contracts: STALE -> ${stale.join(", ")}. Run \`pnpm contracts:generate\`.`);
    process.exit(1);
  }
  console.log("contracts: OpenAPI artifact and generated TypeScript types are current");
}
