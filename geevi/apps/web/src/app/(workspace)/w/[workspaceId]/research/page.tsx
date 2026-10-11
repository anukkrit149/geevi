import { ResearchHome } from "@/features/research/ResearchHome";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <ResearchHome workspaceId={p.workspaceId} />;
}
