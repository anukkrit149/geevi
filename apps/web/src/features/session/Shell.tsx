"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { Button, Loading } from "@/components/ui";
import { useSession, useWorkspace } from "@/lib/session/session";

const NAV: { href: string; label: string; needs: string }[] = [
  { href: "today", label: "Today", needs: "records.read" },
  { href: "patients", label: "Patients", needs: "records.read" },
  { href: "research", label: "Research", needs: "records.read" },
  { href: "department", label: "Department", needs: "records.read" },
  { href: "impacts", label: "Impact queue", needs: "records.read" },
  { href: "imports", label: "Import & recovery", needs: "workspace.manage" },
];

/** Shared layout: navigation, the signed-in development identity, and the session guard. */
export function Shell({ workspaceId, children }: { workspaceId: string; children: ReactNode }) {
  const { session, loading, signOut } = useSession();
  const { workspace, can } = useWorkspace(workspaceId);
  const pathname = usePathname();
  const router = useRouter();
  const signingOut = useRef(false);

  useEffect(() => {
    if (!loading && !session && !signingOut.current) router.replace(`/login?returnTo=${encodeURIComponent(pathname + window.location.search)}`);
  }, [loading, session, router, pathname]);

  if (loading || !session) return <main id="main" className="login"><Loading what="session" /></main>;
  if (!workspace) {
    return (
      <main id="main" className="login">
        <h1>Workspace not available</h1>
        <p data-testid="workspace-denied">This link points to a workspace your account cannot access, or one that does not exist. No records were loaded.</p>
        <p><Link href="/">Go to your workspace</Link></p>
      </main>
    );
  }
  const base = `/w/${workspaceId}`;
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">Geevi<small>{workspace.name}</small></div>
        <nav className="nav" aria-label="Primary">
          {NAV.filter((n) => can(n.needs)).map((n) => (
            <Link key={n.href} href={`${base}/${n.href}`} aria-current={pathname.startsWith(`${base}/${n.href}`) ? "page" : undefined}>{n.label}</Link>
          ))}
        </nav>
        {session.workspaces.length > 1 ? (
          <label className="small">Workspace
            <select aria-label="Switch workspace" value={workspaceId} onChange={(e) => router.push(`/w/${e.target.value}/${can("records.read") ? "today" : "imports"}`)}>
              {session.workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </label>
        ) : null}
        <div className="identity" data-testid="identity">
          <span className="dev-tag">Development identity</span>
          <strong data-testid="identity-name">{session.account.display_name}</strong>
          <span>{session.account.role_title}</span>
          <div style={{ marginTop: ".5rem" }}>
            <Button onClick={async () => { signingOut.current = true; await signOut(); router.replace("/login"); }}>Sign out</Button>
          </div>
        </div>
      </aside>
      <main id="main" className="main" tabIndex={-1}>
        <div className="banner" role="note">
          Fictional demonstration data · Simulated approvals · Not for clinical use.
        </div>
        {children}
      </main>
    </div>
  );
}
