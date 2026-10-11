"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSyncExternalStore, useState, type FormEvent } from "react";
import { Button, ErrorSummary, TextInput, Field } from "@/components/ui";
import { ApiError, api, setCsrfToken, unwrap } from "@/lib/api/client";
import { clearRecords } from "@/lib/session/session";
import { Brand } from "@/components/brand";
import { Appearance } from "@/components/appearance";
import { ArrowRight, Eye, EyeSlash, Files, UsersThree, ListChecks } from "@phosphor-icons/react";
import { landingPath } from "./HomeRedirect";

export function LoginForm({ returnTo }: { returnTo?: string }) {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [showPassword, setShowPassword] = useState(false);
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
      // Start the authenticated route afresh and preserve its section fragment exactly.
      window.location.replace(destination);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError("unexpected_failure", "Sign-in failed.", 0));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="login-layout">
      <section className="login-story" aria-label="About Geevi">
        <Brand />
        <div className="login-story-body"><h1>A clearer view of every next step.</h1><p>A shared workspace for the people, evidence and decisions behind oncology care.</p>
          <div className="login-principles"><div><Files aria-hidden="true" />Follow every finding back to its source</div><div><UsersThree aria-hidden="true" />Keep the care team on the same page</div><div><ListChecks aria-hidden="true" />See what needs attention next</div></div>
        </div>
        <p className="login-story-footer">A fictional demonstration of the oncology department journey. Built around source provenance and human review.</p>
      </section>
      <section className="login-form-area" aria-label="Workspace access">
        <div className="appearance-row"><Appearance /></div>
        <form onSubmit={submit} aria-label="Sign in" data-ready={ready}>
          <h2>Welcome to Geevi</h2><p className="login-intro">Sign in to your workspace.</p>
          {identities.data?.length ? <details className="disclosure"><summary>Choose a demonstration identity</summary>
            <p className="small" id="identity-help">Choose a demonstration identity, then enter the password supplied by the app owner.</p>
            <div className="identity-pick" role="group" aria-describedby="identity-help">{identities.data.map((identity) => <button type="button" key={identity.username} className="btn" aria-pressed={username === identity.username} onClick={() => setUsername(identity.username)}><strong>{identity.display_name}</strong><span className="small">{identity.role_title}</span><span className="sr-only">{identity.label}</span></button>)}</div>
          </details> : null}
          <ErrorSummary error={error} />
          <TextInput label="Username" value={username} onChange={setUsername} autoComplete="username" autoCapitalize="none" spellCheck={false} required />
          <Field label="Password" hint="Ask the app owner for access to this fictional demonstration.">{(id) => <div className="password-field"><input id={id} aria-describedby={`${id}-hint`} value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" required /><button type="button" className="icon-button" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeSlash aria-hidden="true" /> : <Eye aria-hidden="true" />}</button></div>}</Field>
          <Button variant="primary" type="submit" busy={busy}>Sign in<ArrowRight aria-hidden="true" /></Button>
          <div className="login-notice" role="note">Development identities only. These are fictional accounts with demonstration grants, not institutional accounts. Patients and approvals are fictional. Research briefs cite published sources. Clinical use remains unvalidated.</div>
        </form>
      </section>
    </main>
  );
}
