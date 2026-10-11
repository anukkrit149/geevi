import { Today } from "@/features/today/Today";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <Today workspaceId={p.workspaceId} />;
}
