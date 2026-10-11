"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useSyncExternalStore, useState, type FormEvent } from "react";
import { Button, ErrorSummary, TextInput } from "@/components/ui";
import { ApiError, api, setCsrfToken, unwrap } from "@/lib/api/client";
import { clearRecords } from "@/lib/session/session";
import { landingPath } from "./HomeRedirect";

export function LoginForm({ returnTo }: { returnTo?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  // True only on the client after hydration, so nothing is typed into a form React has not attached to yet.
  const ready = useSyncExternalStore(() => () => {}, () => true, () => false);
  const identities = useQuery({
    queryKey: ["dev-identities"],
    queryFn: async () => (await api.GET("/api/v1/dev/identities")).data ?? [],
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = await unwrap(api.POST("/api/v1/session", { body: { username, password } }));
      setCsrfToken(session.csrf_token);
      clearRecords(queryClient); // a new account never inherits the previous account's cached records
      queryClient.setQueryData(["session"], session);
      let destination = session.workspaces.length ? landingPath(session.workspaces[0]) : "/";
      if (returnTo && URL.canParse(returnTo, "https://geevi.invalid")) {
        const candidate = new URL(returnTo, "https://geevi.invalid");
        const match = candidate.pathname.match(/^\/w\/([0-9a-f-]{36})(?:\/|$)/);
        if (candidate.origin === "https://geevi.invalid" && match && session.workspaces.some((w) => w.id === match[1])) {
          destination = candidate.pathname + candidate.search + candidate.hash;
        }
      }
      router.replace(destination);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError("unexpected_failure", "Sign-in failed.", 0));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="login">
      <h1>Geevi</h1>
      <p>Oncology department journey — fictional full-stack demonstration.</p>
      <div className="banner" role="note">
        Development identities only. These are fictional accounts with demonstration grants, not institutional accounts.
        Patients and approvals are fictional. Research briefs cite published sources. Clinical use remains unvalidated.
      </div>
      <form className="card" onSubmit={submit} aria-label="Sign in" data-ready={ready}>
        <h2>Sign in</h2>
        {identities.data?.length ? (
          <>
            <p className="small" id="identity-help">Choose a demonstration identity, then enter the password supplied by the app owner.</p>
            <div className="identity-pick" role="group" aria-describedby="identity-help">
              {identities.data.map((identity) => (
                <button type="button" key={identity.username} className="btn" aria-pressed={username === identity.username} onClick={() => setUsername(identity.username)}>
                  <strong>{identity.display_name}</strong> <span className="badge badge-warn">{identity.label}</span>
                  <span className="small" style={{ display: "block" }}>{identity.role_title}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}
        <ErrorSummary error={error} />
        <TextInput label="Username" value={username} onChange={setUsername} autoComplete="username" required />
        <TextInput label="Password" value={password} onChange={setPassword} type="password" autoComplete="current-password" required
          hint="Ask the app owner for access to this fictional demonstration." />
        <Button variant="primary" type="submit" busy={busy}>Sign in</Button>
      </form>
    </main>
  );
}
