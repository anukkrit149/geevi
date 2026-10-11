/**
 * The one typed HTTP boundary (KTD9). Every request to FastAPI goes through this module, using
 * types generated from its OpenAPI document. Nothing here decides whether an action is allowed:
 * the server re-validates every write, and no approval is ever shown optimistically.
 */
import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type CommandResult = Schemas["CommandResult"];

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly nextAction: string | null = null,
    readonly details: Record<string, unknown> | null = null,
    readonly target: { kind: string; id?: string | null } | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
  /** The outcome is unknown (network loss or server failure): retry the SAME command id, never a fresh one. */
  get outcomeUnknown(): boolean {
    return this.status === 0 || this.status >= 500;
  }
}

let csrfToken: string | null = null;
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });

api.use({
  onRequest({ request }) {
    if (csrfToken && !["GET", "HEAD"].includes(request.method)) request.headers.set("X-CSRF-Token", csrfToken);
    return request;
  },
});

type Result<T> = { data?: T; error?: unknown; response: Response };

export function toApiError(error: unknown, status: number): ApiError {
  const body = (error as { error?: Record<string, unknown> } | undefined)?.error;
  if (body && typeof body.code === "string") {
    return new ApiError(body.code, String(body.message ?? "The request failed."), status, (body.next_action as string) ?? null,
      (body.details as Record<string, unknown>) ?? null, (body.target as ApiError["target"]) ?? null);
  }
  return new ApiError("unexpected_failure", "The request failed. Nothing is shown as saved.", status, "Retry the same action.");
}

/** Resolve an openapi-fetch call to its data or throw a typed ApiError. */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  let result: Result<T>;
  try {
    result = await call;
  } catch {
    throw new ApiError("network_unknown_outcome", "The server could not be reached, so the outcome is unknown.", 0,
      "Retry: the same command is re-sent and applied at most once.");
  }
  if (result.error !== undefined || !result.response.ok) throw toApiError(result.error, result.response.status);
  return result.data as T;
}

/** Authenticated original bytes (PDF/image) for the client-only source viewer. */
export async function fetchBinary(path: string): Promise<{ bytes: ArrayBuffer; mediaType: string; sha256: string | null }> {
  let response: Response;
  try {
    response = await fetch(path, { credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new ApiError("network_unknown_outcome", "The original could not be loaded.", 0, "Retry.");
  }
  if (!response.ok) throw toApiError(await response.json().catch(() => undefined), response.status);
  return { bytes: await response.arrayBuffer(), mediaType: response.headers.get("content-type") ?? "", sha256: response.headers.get("x-content-sha256") };
}

export function newCommandId(): string {
  return crypto.randomUUID();
}

export async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}
