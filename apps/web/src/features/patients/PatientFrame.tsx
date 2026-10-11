"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Initials } from "@/components/brand";
import { ArrowLeft, SquaresFour, Files, ClipboardText, Heartbeat, ClockCounterClockwise } from "@phosphor-icons/react";
import { Badge, Loading } from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import { usePatient } from "@/lib/api/hooks";

/** Patient header and section navigation. An unknown or cross-workspace patient link fails safely. */
export function PatientFrame({ workspaceId, patientId, children }: { workspaceId: string; patientId: string; children: ReactNode }) {
  const patient = usePatient(workspaceId, patientId);
  const pathname = usePathname();
  const base = `/w/${workspaceId}/patients/${patientId}`;
  if (patient.isLoading) return <Loading what="patient" />;
  if (patient.error || !patient.data) {
    const error = patient.error instanceof ApiError ? patient.error : null;
    return (
      <div className="card" data-testid="record-unavailable" role="alert">
        <h1>Record not available</h1>
        <p>{error?.message ?? "This patient could not be loaded."} No record from another workspace is ever shown.</p>
        <Link href={`/w/${workspaceId}/patients`}>Back to patients</Link>
      </div>
    );
  }
  const { patient: p, identifiers, episodes } = patient.data;
  const tabs: [string, string][] = [[base, "Clinical overview"], [`${base}/sources`, "Reports"], [`${base}/decisions`, "Plan & decisions"], [`${base}/care`, "Care & follow-up"], [`${base}/history`, "Record history"]];
  const icons = [SquaresFour, Files, ClipboardText, Heartbeat, ClockCounterClockwise];
  return (
    <>
      <Link className="back-link" href={`/w/${workspaceId}/patients`}><ArrowLeft aria-hidden="true" />Back to patients</Link>
      <div className="page-head">
        <div className="patient-heading"><Initials name={p.display_name} className="avatar-large" /><div>
          <h1 data-testid="patient-name">{p.display_name}</h1>
          <p>{identifiers.map((i) => `${i.system}: ${i.value}`).join(" · ")}</p>
          {episodes.map((e) => <p className="small" key={e.id}>{e.title}</p>)}
        </div></div>
        <div className="row">
          <Badge value={p.data_label} />
          {episodes.map((e) => <span key={e.id} data-testid="episode-status"><Badge value={e.status} label={`Episode ${e.status.replace("_", " ")} · ${e.responsible_team}`} /></span>)}
        </div>
      </div>
      <nav className="subnav" aria-label="Patient sections">
        {tabs.map(([href, label], index) => {
          const Icon = icons[index];
          const current = href === base ? pathname === base : pathname.startsWith(href);
          return <Link key={href} href={href} aria-current={current ? "page" : undefined}><Icon aria-hidden="true" />{label}</Link>;
        })}
      </nav>
      {children}
    </>
  );
}
