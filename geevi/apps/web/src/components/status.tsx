"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

type Status = { announce: (message: string) => void };
const StatusContext = createContext<Status>({ announce: () => {} });

/** One polite live region for durable results ("Plan approved"), so status changes are announced and visible. */
export function StatusProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const announce = useCallback((text: string) => {
    setMessage(text);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(""), 8000);
  }, []);
  const value = useMemo(() => ({ announce }), [announce]);
  return (
    <StatusContext.Provider value={value}>
      {children}
      <div className="status-toast" role="status" aria-live="polite" data-testid="status" data-visible={message ? "true" : "false"}>
        {message}
      </div>
    </StatusContext.Provider>
  );
}

export function useStatus(): Status {
  return useContext(StatusContext);
}
