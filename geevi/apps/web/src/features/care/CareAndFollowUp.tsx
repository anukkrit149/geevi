"use client";

import { ConcernPanel } from "@/features/follow-up/ConcernPanel";
import { FollowUpPanel } from "@/features/follow-up/FollowUpPanel";
import { CarePanel } from "./CarePanel";
import { TaskBoard } from "./TaskBoard";

export function CareAndFollowUp({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  return (
    <>
      <TaskBoard workspaceId={workspaceId} patientId={patientId} />
      <CarePanel workspaceId={workspaceId} patientId={patientId} />
      <ConcernPanel workspaceId={workspaceId} patientId={patientId} />
      <FollowUpPanel workspaceId={workspaceId} patientId={patientId} />
    </>
  );
}
