import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { StatusProvider } from "@/components/status";
import { useAction } from "@/lib/api/useAction";

function setup() {
  const client = new QueryClient();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}><StatusProvider>{children}</StatusProvider></QueryClientProvider>;
  return { ...renderHook(() => useAction("ws-1"), { wrapper }), invalidate };
}
const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const fail = (status: number, code: string) => ({ error: { error: { code, message: code } }, response: new Response(null, { status }) });
const status = () => document.querySelector("[data-testid='status']")?.textContent;

describe("useAction", () => {
  it("re-sends the SAME command id while the outcome is unknown, and announces success only after a durable result", async () => {
    const { result, invalidate } = setup();
    const ids: string[] = [];
    const call = vi.fn()
      .mockImplementationOnce(async (id: string) => { ids.push(id); throw new TypeError("network down"); })
      .mockImplementationOnce(async (id: string) => { ids.push(id); return fail(500, "storage_failure"); })
      .mockImplementationOnce(async (id: string) => { ids.push(id); return ok({ replayed: true }); });

    await act(async () => { expect(await result.current.run("sign", call, "Plan approved")).toBeNull(); });
    expect(result.current.error?.code).toBe("network_unknown_outcome");
    expect(status()).toBe("");
    await act(async () => { expect(await result.current.run("sign", call, "Plan approved")).toBeNull(); });
    expect(result.current.error?.outcomeUnknown).toBe(true);
    expect(invalidate).not.toHaveBeenCalled(); // nothing was refetched or shown as saved
    await act(async () => { expect(await result.current.run("sign", call, "Plan approved")).toEqual({ replayed: true }); });
    expect(new Set(ids).size).toBe(1); // one command id across all three attempts
    expect(result.current.error).toBeNull();
    expect(status()).toBe("Plan approved");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["ws", "ws-1"] });
  });

  it("uses a fresh command id after a definitive rejection and never announces a rejected command", async () => {
    const { result } = setup();
    const ids: string[] = [];
    const call = vi.fn()
      .mockImplementationOnce(async (id: string) => { ids.push(id); return fail(409, "stale_dependency"); })
      .mockImplementationOnce(async (id: string) => { ids.push(id); return ok({}); });
    await act(async () => { await result.current.run("sign", call, "Plan approved"); });
    expect(result.current.error?.code).toBe("stale_dependency");
    expect(status()).toBe("");
    await act(async () => { await result.current.run("sign", call, "Plan approved"); });
    expect(ids[0]).not.toBe(ids[1]); // a corrected action is a new command, never a silent re-issue
  });

  it("keeps separate actions on separate command ids", async () => {
    const { result } = setup();
    const ids: Record<string, string> = {};
    await act(async () => {
      await result.current.run("a", async (id) => { ids.a = id; return ok({}); });
      await result.current.run("b", async (id) => { ids.b = id; return ok({}); });
    });
    expect(ids.a).not.toBe(ids.b);
  });
});
