import { QuestionDetail } from "@/features/research/QuestionDetail";

export default async function Page({ params }: { params: Promise<{ workspaceId: string; questionId: string }> }) {
  const p = await params;
  return <QuestionDetail workspaceId={p.workspaceId} questionId={p.questionId} />;
}
