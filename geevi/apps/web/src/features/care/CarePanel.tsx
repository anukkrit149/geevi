"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, relDay, when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

const STATUSES = ["performed", "partial", "deferred", "not_performed", "unknown"];

export function CarePanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const planned = useWs(workspaceId, ["patient", patientId, "planned"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/planned-events", { params: { path } }));
  const care = useWs(workspaceId, ["patient", patientId, "care"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/care-events", { params: { path } }));
  const plans = useWs(workspaceId, ["patient", patientId, "plans"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", { params: { path } }));
  const action = useAction(workspaceId);
  const signed = (plans.data ?? []).filter((v) => ["approved", "superseded"].includes(v.plan.status));
  const current = [...signed].reverse().find((v) => v.plan.status === "approved");
  const [schedule, setSchedule] = useState({ description: "", day: "", location: "" });
  const [event, setEvent] = useState({ status: "performed", day: "", narrative: "", source: "direct", performer_name: "", plan_version_id: "", planned_event_id: "" });
  const planId = event.plan_version_id || current?.plan.id || "";
  const canSchedule = can("task.act") || can("followup.manage") || can("task.assign");

  return (
    <div className="grid grid-2">
      <Card title="Planned events (not delivery)" testId="planned-events">
        <ErrorSummary error={action.error} onDismiss={action.clearError} />
        <p className="small">A schedule entry says what is planned. It never records that anything happened.</p>
        {planned.data?.length ? planned.data.map((p) => (
          <div className="item" key={p.id}><div className="row"><strong>{p.description}</strong><Badge value={p.status === "scheduled" ? "scheduled" : p.status} /></div>
            <p className="small">{day(p.scheduled_time)}{p.location ? ` · ${p.location}` : ""} · scheduled by {p.recorded_by_name}</p></div>
        )) : <Empty>Nothing is scheduled.</Empty>}
        {canSchedule ? (
          <form onSubmit={async (e) => {
            e.preventDefault();
            const done = await action.run("schedule", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/planned-events", {
              params: { path }, body: { command_id, event_type: "visit", description: schedule.description, scheduled_time: relDay(Number(schedule.day)) as never,
                location: schedule.location || null, plan_version_id: current?.plan.id ?? null } }), "Event scheduled (no delivery recorded)");
            if (done) setSchedule({ description: "", day: "", location: "" });
          }}>
            <fieldset>
              <legend>Schedule an event</legend>
              <TextInput label="What is scheduled" value={schedule.description} onChange={(description) => setSchedule({ ...schedule, description })} required />
              <div className="grid grid-2">
                <TextInput label="Scheduled for (relative day)" inputMode="numeric" value={schedule.day} onChange={(d) => setSchedule({ ...schedule, day: d })} required />
                <TextInput label="Location" value={schedule.location} onChange={(location) => setSchedule({ ...schedule, location })} />
              </div>
              <Button type="submit" busy={action.pending === "schedule"}>Schedule</Button>
            </fieldset>
          </form>
        ) : null}
      </Card>

      <Card title="Actual care (attributed)" testId="care-events">
        <p className="small">What actually happened, who did it and who recorded it. Recording care never reactivates an older plan or infers an outcome.</p>
        {care.data?.length ? care.data.map((c) => (
          <div className="item" key={c.id} data-testid={`care-${c.status}`}>
            <div className="row"><Badge value={c.status} /><span>{c.actual_time ? day(c.actual_time) : "time not recorded"}</span></div>
            <p className="quote">{c.narrative}</p>
            <p className="small">Performed by {c.performer_name}{c.transcriber_name ? ` · transcribed from an external report by ${c.transcriber_name}` : ""} · recorded {when(c.recorded_at)}
              {" · "}under plan v{signed.find((v) => v.plan.id === c.plan_version_id)?.plan.version_no ?? "?"} (historical reference)</p>
          </div>
        )) : <Empty>No care has been recorded.</Empty>}
        {can("care.record") && signed.length ? (
          <form onSubmit={async (e) => {
            e.preventDefault();
            const done = await action.run("care", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/care-events", {
              params: { path }, body: { command_id, status: event.status as never, actual_time: event.day ? relDay(Number(event.day)) as never : null, narrative: event.narrative,
                source: event.source as never, performer_name: event.source === "external_report" ? event.performer_name : null, plan_version_id: planId,
                planned_event_id: event.planned_event_id || null } }), "Care record saved");
            if (done) setEvent({ ...event, day: "", narrative: "", performer_name: "", planned_event_id: "" });
          }}>
            <fieldset>
              <legend>Record what actually happened</legend>
              <div className="grid grid-2">
                <Select label="Status" value={event.status} onChange={(status) => setEvent({ ...event, status })} options={STATUSES.map((s) => ({ value: s, label: words(s) }))} />
                <TextInput label="Actual time (relative day)" inputMode="numeric" value={event.day} onChange={(d) => setEvent({ ...event, day: d })} hint="Leave empty only when the time is genuinely unknown." />
                <Select label="Source of this record" value={event.source} onChange={(source) => setEvent({ ...event, source })}
                  options={[{ value: "direct", label: "I performed or witnessed it" }, { value: "external_report", label: "Transcribed from an external report" }]} />
                {event.source === "external_report" ? <TextInput label="Performed by (external)" value={event.performer_name} onChange={(performer_name) => setEvent({ ...event, performer_name })} /> : null}
                <Select label="Plan version this was done under" value={planId} onChange={(plan_version_id) => setEvent({ ...event, plan_version_id })}
                  options={signed.map((v) => ({ value: v.plan.id, label: `Plan v${v.plan.version_no} (${v.plan.status})` }))} />
                <Select label="Related scheduled event (optional)" value={event.planned_event_id} onChange={(planned_event_id) => setEvent({ ...event, planned_event_id })}
                  options={[{ value: "", label: "None" }, ...(planned.data ?? []).map((p) => ({ value: p.id, label: `${p.description} — ${day(p.scheduled_time)}` }))]} />
              </div>
              <TextArea label="What happened" value={event.narrative} onChange={(narrative) => setEvent({ ...event, narrative })} required />
              <Button variant="primary" type="submit" busy={action.pending === "care"}>Save care record</Button>
            </fieldset>
          </form>
        ) : null}
      </Card>
    </div>
  );
}
