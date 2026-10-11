import { ProfileTimeline } from "@/features/patients/ProfileTimeline";
import { PatientOverview } from "@/features/patients/PatientOverview";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <><PatientOverview workspaceId={p.workspaceId} patientId={p.patientId} /><ProfileTimeline workspaceId={p.workspaceId} patientId={p.patientId} /></>;
}
