"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loading } from "@/components/ui";
import { useSession } from "@/lib/session/session";

export function landingPath(workspace: { id: string; capabilities: string[] }): string {
  return workspace.capabilities.includes("records.read") ? `/w/${workspace.id}/today` : `/w/${workspace.id}/imports`;
}

export function HomeRedirect() {
  const { session, loading } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    if (!session) router.replace("/login");
    else if (session.workspaces.length) router.replace(landingPath(session.workspaces[0]));
  }, [loading, session, router]);
  if (!loading && session && !session.workspaces.length) {
    return <main id="main" className="login"><h1>No workspace</h1><p>This development account has no workspace grant. Run the demo seed script.</p></main>;
  }
  return <main id="main" className="login"><Loading what="session" /></main>;
}
