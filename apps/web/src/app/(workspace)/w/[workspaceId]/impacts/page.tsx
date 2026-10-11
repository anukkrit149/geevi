import { ImpactQueue } from "@/features/impacts/ImpactQueue";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <ImpactQueue workspaceId={p.workspaceId} />;
}
