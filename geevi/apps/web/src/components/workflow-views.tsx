"use client";

import { useId, useSyncExternalStore, type ReactNode } from "react";

type View = { id: string; label: string; content: ReactNode };
const subscribe = (notify: () => void) => {
  window.addEventListener("hashchange", notify);
  window.addEventListener("popstate", notify);
  return () => { window.removeEventListener("hashchange", notify); window.removeEventListener("popstate", notify); };
};
const getHash = () => window.location.hash.slice(1);

/** Panels remain mounted: switching tasks never discards an unfinished form. URL hashes deep-link a view. */
export function WorkflowViews({ label, views, initial }: { label: string; views: View[]; initial: string }) {
  const uid = useId();
  const hash = useSyncExternalStore(subscribe, getHash, () => "");
  const selected = hash === "all" || views.some((view) => view.id === hash) ? hash : initial;
  const options = [...views.map(({ id, label }) => ({ id, label })), { id: "all", label: "All sections" }];
  function select(id: string) {
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}#${id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }
  return <div className="workflow-views">
    <div className="workflow-tabs" role="tablist" aria-label={label}>
      {options.map((view, index) => <button type="button" role="tab" id={`${uid}-tab-${view.id}`} key={view.id} aria-controls={`${uid}-panel-${view.id}`} aria-selected={selected === view.id} tabIndex={selected === view.id ? 0 : -1} onClick={() => select(view.id)} onKeyDown={(event) => {
        const target = event.key === "ArrowRight" ? (index + 1) % options.length : event.key === "ArrowLeft" ? (index - 1 + options.length) % options.length : event.key === "Home" ? 0 : event.key === "End" ? options.length - 1 : null;
        if (target !== null) { event.preventDefault(); select(options[target].id); document.getElementById(`${uid}-tab-${options[target].id}`)?.focus(); }
      }}>{view.label}</button>)}
    </div>
    <div id={`${uid}-panel-all`} role={selected === "all" ? "tabpanel" : undefined} aria-labelledby={selected === "all" ? `${uid}-tab-all` : undefined}>
      {views.map((view) => <div id={`${uid}-panel-${view.id}`} role={selected === "all" ? undefined : "tabpanel"} aria-labelledby={`${uid}-tab-${view.id}`} key={view.id} hidden={selected !== "all" && selected !== view.id} className="workflow-panel">{view.content}</div>)}
    </div>
  </div>;
}
