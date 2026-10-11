import { SourceList } from "@/features/sources/SourceList";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string }> }) {
  const p = await params;
  return <SourceList workspaceId={p.workspaceId} patientId={p.patientId} />;
}
