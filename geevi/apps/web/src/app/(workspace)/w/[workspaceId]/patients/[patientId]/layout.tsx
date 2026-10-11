import type { ReactNode } from "react";
import { PatientFrame } from "@/features/patients/PatientFrame";

export default async function PatientLayout({ children, params }: { children: ReactNode; params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <PatientFrame workspaceId={p.workspaceId} patientId={p.patientId}>{children}</PatientFrame>;
}
