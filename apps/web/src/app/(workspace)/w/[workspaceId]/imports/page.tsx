import { ImportsHome } from "@/features/imports/ImportsHome";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <ImportsHome workspaceId={p.workspaceId} />;
}
