import { ProtocolDetail } from "@/features/department/ProtocolDetail";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; versionId: string }> }) {
  const p = await params;
  return <ProtocolDetail workspaceId={p.workspaceId} versionId={p.versionId} />;
}
