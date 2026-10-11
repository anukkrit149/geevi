import { DepartmentHome } from "@/features/department/DepartmentHome";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <DepartmentHome workspaceId={p.workspaceId} />;
}
