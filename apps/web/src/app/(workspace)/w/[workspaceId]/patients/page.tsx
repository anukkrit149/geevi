import { PatientList } from "@/features/patients/PatientList";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const p = await params;
  return <PatientList workspaceId={p.workspaceId} />;
}
