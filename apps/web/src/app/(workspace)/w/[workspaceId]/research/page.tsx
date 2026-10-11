import { ResearchHome } from "@/features/research/ResearchHome";

export default async function Page({ params, searchParams }: { params: Promise<{ workspaceId: string }>; searchParams: Promise<{ patient?: string }> }) {
  const p = await params;
  const search = await searchParams;
  return <ResearchHome workspaceId={p.workspaceId} patientId={search.patient} />;
}
