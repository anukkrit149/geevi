import next from "eslint-config-next";

const config = [
  ...next,
  { ignores: [".next/**", ".next-e2e/**", "node_modules/**", "src/lib/api/schema.d.ts", "playwright-report/**", "test-results/**", "next-env.d.ts"] },
];

export default config;
