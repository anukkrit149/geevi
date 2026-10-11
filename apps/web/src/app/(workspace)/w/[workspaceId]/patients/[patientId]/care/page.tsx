import { CareAndFollowUp } from "@/features/care/CareAndFollowUp";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <CareAndFollowUp workspaceId={p.workspaceId} patientId={p.patientId} />;
}
