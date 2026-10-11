import { SourceReview } from "@/features/sources/SourceReview";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; patientId: string; documentId: string }> }) {
  const p = await params;
  return <SourceReview workspaceId={p.workspaceId} patientId={p.patientId} documentId={p.documentId} />;
}
