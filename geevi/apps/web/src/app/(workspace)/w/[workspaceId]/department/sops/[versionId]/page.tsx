import { SopDetail } from "@/features/department/SopDetail";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; versionId: string }> }) {
  const p = await params;
  return <SopDetail workspaceId={p.workspaceId} versionId={p.versionId} />;
}
