"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { useStatus } from "@/components/status";
import { ApiError, newCommandId, unwrap, type CommandResult } from "./client";

type Call<T> = (commandId: string) => Promise<{ data?: T; error?: unknown; response: Response }>;

/**
 * Runs one server command. Nothing is updated optimistically: success is announced only after the
 * durable result arrives, then server state is refetched. When the outcome is unknown (network or
 * commit failure) the SAME command id is kept and re-sent on retry, so a signature is never
 * duplicated or silently re-issued under a fresh id. Callers keep their own draft state untouched.
 */
export function useAction(workspaceId?: string) {
  const queryClient = useQueryClient();
  const { announce } = useStatus();
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const unknownOutcome = useRef(new Map<string, string>());

  const run = useCallback(async <T = CommandResult>(key: string, call: Call<T>, success?: string): Promise<T | null> => {
    const commandId = unknownOutcome.current.get(key) ?? newCommandId();
    setPending(key);
    setError(null);
    try {
      const result = await unwrap(call(commandId));
      unknownOutcome.current.delete(key);
      await queryClient.invalidateQueries({ queryKey: workspaceId ? ["ws", workspaceId] : undefined });
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      if (success) announce(success);
      return result;
    } catch (caught) {
      const failure = caught instanceof ApiError ? caught : new ApiError("unexpected_failure", "The request failed.", 0);
      if (failure.outcomeUnknown) unknownOutcome.current.set(key, commandId);
      else unknownOutcome.current.delete(key);
      setError(failure);
      // Another session may have changed things: refresh what we show, but never the user's draft.
      if (failure.status === 409 && workspaceId) void queryClient.invalidateQueries({ queryKey: ["ws", workspaceId] });
      return null;
    } finally {
      setPending(null);
    }
  }, [announce, queryClient, workspaceId]);

  return { run, error, pending, clearError: () => setError(null) };
}
