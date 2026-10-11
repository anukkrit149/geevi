import { EvidenceDetail } from "@/features/research/EvidenceDetail";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; sourceId: string }> }) {
  const p = await params;
  return <EvidenceDetail workspaceId={p.workspaceId} sourceId={p.sourceId} />;
}
