import { Decisions } from "@/features/plans/Decisions";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <Decisions workspaceId={p.workspaceId} patientId={p.patientId} />;
}
