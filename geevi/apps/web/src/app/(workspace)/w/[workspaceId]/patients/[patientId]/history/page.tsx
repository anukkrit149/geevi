import { ProfileTimeline } from "@/features/patients/ProfileTimeline";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <ProfileTimeline workspaceId={p.workspaceId} patientId={p.patientId} recordHistory />;
}
