import type { NextConfig } from "next";

// Same-origin interface (KTD10): the browser only ever talks to this origin. `/api/v1/*` is a
// documented transparent proxy to the FastAPI service, which owns every domain rule. Next.js
// implements no workflow backend and never touches the database.
const API_ORIGIN = process.env.GEEVI_API_ORIGIN ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.GEEVI_NEXT_DIST ?? ".next",
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "Cache-Control", value: "no-store" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "same-origin" },
    ] }];
  },
};

export default config;
