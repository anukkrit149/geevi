"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { CalendarBlank, Users, Books, Buildings, ArrowsClockwise, Tray, CaretRight, List, X, SignOut, ShieldCheck } from "@phosphor-icons/react";
import { Button, Loading } from "@/components/ui";
import { Brand, Initials } from "@/components/brand";
import { Appearance } from "@/components/appearance";
import { useSession, useWorkspace } from "@/lib/session/session";

const NAV = [
  { href: "today", label: "Today", needs: "records.read", icon: CalendarBlank },
  { href: "patients", label: "Patients", needs: "records.read", icon: Users },
  { href: "research", label: "Research", needs: "records.read", icon: Books },
  { href: "department", label: "Department", needs: "records.read", icon: Buildings },
  { href: "impacts", label: "Impact queue", needs: "records.read", icon: ArrowsClockwise },
  { href: "imports", label: "Import & recovery", needs: "workspace.manage", icon: Tray },
];

export function Shell({ workspaceId, children }: { workspaceId: string; children: ReactNode }) {
  const { session, loading, signOut } = useSession();
  const { workspace, can } = useWorkspace(workspaceId);
  const pathname = usePathname();
  const router = useRouter();
  const signingOut = useRef(false);
  const [menu, setMenu] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!loading && !session && !signingOut.current) router.replace(`/login?returnTo=${encodeURIComponent(pathname + window.location.search + window.location.hash)}`);
  }, [loading, session, router, pathname]);

  if (loading || !session) return <main id="main" className="login"><Loading what="session" /></main>;
  if (!workspace) return <main id="main" className="login"><h1>Workspace not available</h1><p data-testid="workspace-denied">This link points to a workspace your account cannot access, or one that does not exist. No records were loaded.</p><p><Link href="/">Go to your workspace</Link></p></main>;
  const base = `/w/${workspaceId}`;
  const section = NAV.find((n) => pathname.startsWith(`${base}/${n.href}`));
  return <div className="shell">
    <aside className="sidebar" data-expanded={menu} onKeyDown={(event) => { if (event.key === "Escape" && menu) { setMenu(false); menuButton.current?.focus(); } }}>
      <div className="sidebar-brand"><Link href={`${base}/${can("records.read") ? "today" : "imports"}`} aria-label="Geevi home" onClick={() => setMenu(false)}><Brand /></Link>
        <button ref={menuButton} className="icon-button mobile-menu-button" aria-label={menu ? "Close navigation" : "Open navigation"} aria-expanded={menu} aria-controls="workspace-navigation" onClick={() => setMenu(!menu)}>{menu ? <X aria-hidden="true" /> : <List aria-hidden="true" />}</button>
      </div>
      <div className="workspace-picker">
        {session.workspaces.length > 1 ? <><label htmlFor="workspace-switch">Workspace</label><select id="workspace-switch" aria-label="Switch workspace" value={workspaceId} onChange={(e) => { setMenu(false); router.push(`/w/${e.target.value}/${can("records.read") ? "today" : "imports"}`); }}>{session.workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}</select></> : <><span className="workspace-label">Workspace</span><strong>{workspace.name}</strong></>}
      </div>
      <nav id="workspace-navigation" className="nav" aria-label="Primary">
        {NAV.filter((n) => can(n.needs)).map((n) => <Link key={n.href} href={`${base}/${n.href}`} aria-current={pathname.startsWith(`${base}/${n.href}`) ? "page" : undefined} onClick={() => setMenu(false)}><n.icon aria-hidden="true" weight={pathname.startsWith(`${base}/${n.href}`) ? "duotone" : "regular"} />{n.label}</Link>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="workspace-note"><ShieldCheck aria-hidden="true" /><span>Source-linked records.<br />Human-reviewed decisions.</span></div>
        <div className="identity" data-testid="identity">
          <div className="identity-person"><Initials name={session.account.display_name} /><div><strong data-testid="identity-name">{session.account.display_name}</strong><span className="identity-role">{session.account.role_title}</span></div></div>
          <div className="identity-actions"><span className="dev-tag">Development identity</span><Button variant="quiet" onClick={async () => { signingOut.current = true; await signOut(); router.replace("/login"); }}><SignOut aria-hidden="true" />Sign out</Button></div>
        </div>
      </div>
    </aside>
    <div className="workspace-content">
      <header className="topbar"><div className="breadcrumb"><span>Workspace</span><CaretRight aria-hidden="true" /><strong>{section?.label ?? "Overview"}</strong></div><div className="topbar-actions"><span className="demo-chip">Fictional demo</span><Appearance /></div></header>
      <main id="main" className="main" tabIndex={-1}>
        <div className="banner" role="note"><ShieldCheck aria-hidden="true" /><span>Fictional demonstration data · Simulated approvals · Not for clinical use.</span></div>
        <div className="route-content">{children}</div>
      </main>
    </div>
  </div>;
}
