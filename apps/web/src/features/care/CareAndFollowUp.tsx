"use client";

import { WorkflowViews } from "@/components/workflow-views";
import { ConcernPanel } from "@/features/follow-up/ConcernPanel";
import { FollowUpPanel } from "@/features/follow-up/FollowUpPanel";
import { CarePanel } from "./CarePanel";
import { TaskBoard } from "./TaskBoard";

export function CareAndFollowUp({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const props = { workspaceId, patientId };
  return <WorkflowViews label="Care workflow" initial="tasks" views={[
    { id: "tasks", label: "Handoff tasks", content: <TaskBoard {...props} /> },
    { id: "care-events", label: "Care record", content: <CarePanel {...props} /> },
    { id: "concerns", label: "Concerns", content: <ConcernPanel {...props} /> },
    { id: "follow-ups", label: "Follow-up", content: <FollowUpPanel {...props} /> },
  ]} />;
}
