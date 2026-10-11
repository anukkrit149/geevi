"use client";

import { useEffect, useId, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { ApiError } from "@/lib/api/client";

export function Button({ variant = "secondary", busy, children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "quiet"; busy?: boolean }) {
  return (
    <button type="button" {...rest} className={`btn btn-${variant} ${rest.className ?? ""}`} disabled={rest.disabled || busy} aria-busy={busy || undefined}>
      {busy ? "Working…" : children}
    </button>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id)}
      {hint ? <p id={`${id}-hint`} className="hint">{hint}</p> : null}
    </div>
  );
}

export function TextInput({ label, hint, value, onChange, ...rest }: { label: string; hint?: string; value: string; onChange: (v: string) => void } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value">) {
  return <Field label={label} hint={hint}>{(id) => <input id={id} aria-describedby={hint ? `${id}-hint` : undefined} value={value} onChange={(e) => onChange(e.target.value)} {...rest} />}</Field>;
}

export function TextArea({ label, hint, value, onChange, rows = 3, ...rest }: { label: string; hint?: string; value: string; onChange: (v: string) => void; rows?: number } & Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange" | "value">) {
  return <Field label={label} hint={hint}>{(id) => <textarea id={id} aria-describedby={hint ? `${id}-hint` : undefined} rows={rows} value={value} onChange={(e) => onChange(e.target.value)} {...rest} />}</Field>;
}

export function Select({ label, hint, value, onChange, options, ...rest }: { label: string; hint?: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] } & Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "onChange" | "value">) {
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <select id={id} aria-describedby={hint ? `${id}-hint` : undefined} value={value} onChange={(e) => onChange(e.target.value)} {...rest}>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )}
    </Field>
  );
}

export function Card({ title, actions, children, testId, level = 2, tone }: { title: string; actions?: ReactNode; children: ReactNode; testId?: string; level?: 2 | 3; tone?: "plain" | "warn" }) {
  const Heading = level === 2 ? "h2" : "h3";
  return (
    <section className={`card ${tone === "warn" ? "card-warn" : ""}`} id={testId} data-testid={testId} aria-label={title}>
      <header className="card-head">
        <Heading>{title}</Heading>
        {actions ? <div className="row">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

const TONES: Record<string, string> = {
  approved: "good", accepted: "good", effective: "good", published: "good", verified: "good", current: "good", completed: "good", active: "good",
  associated: "good", fulfilled: "good", closed: "good", performed: "good", validated: "good", activated: "good", received: "good", responded: "good", match: "good",
  pending: "warn", draft: "muted", in_review: "warn", submitted: "warn", review_needed: "warn", open: "warn", sent: "warn", unreviewed: "warn",
  changes_requested: "warn", more_information: "warn", scheduled: "info", acknowledged: "warn", transferred: "info", staged: "info", partial: "warn",
  unknown: "warn", difference: "warn", held: "warn", corrected: "info", escalated: "warn", returned: "warn", blocked: "bad", deferred: "warn",
  rejected: "bad", withdrawn: "bad", expired: "bad", quarantined: "bad", failed: "bad", missed: "bad", superseded: "muted", cancelled: "muted",
  retired: "muted", discarded: "muted", not_performed: "muted", not_applicable: "muted", amended: "muted", reviewed: "info",
};

export function Badge({ value, label }: { value: string | null | undefined; label?: string }) {
  if (!value) return null;
  return <span className={`badge badge-${TONES[value] ?? "info"}`} data-status={value}>{label ?? value.replaceAll("_", " ")}</span>;
}

function detailLines(error: ApiError): string[] {
  const d = error.details ?? {};
  const lines: string[] = [];
  for (const gate of (d.gates as { requirement_id: string; message: string }[] | undefined) ?? []) lines.push(`${gate.requirement_id}: ${gate.message}`);
  for (const c of (d.changes as { scope?: string; reason?: string; last_change?: { event?: string; actor?: string; title?: string } }[] | undefined) ?? []) {
    lines.push(c.reason ?? `Changed: ${c.scope?.split("/").slice(2).join("/")} - ${c.last_change?.event ?? "updated"}${c.last_change?.title ? ` “${c.last_change.title}”` : ""} by ${c.last_change?.actor ?? "another account"}`);
  }
  for (const c of (d.criteria as { requirement_id: string; message: string }[] | undefined) ?? []) lines.push(`${c.requirement_id}: ${c.message}`);
  for (const f of (d.fields as { field: string; message: string }[] | undefined) ?? []) lines.push(`${f.field}: ${f.message}`);
  for (const r of (d.reasons as { scope?: string; owner?: string; state?: string }[] | undefined) ?? []) lines.push(`Open impact review (${r.state}) owned by ${r.owner}`);
  if (typeof d.current_revision === "number") lines.push(`You loaded revision ${String(d.expected_revision)}; the current revision is ${String(d.current_revision)}.`);
  return lines;
}

/** Focused, announced error summary. The user's draft is never cleared when this appears. */
export function ErrorSummary({ error, onDismiss }: { error: ApiError | null; onDismiss?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error) ref.current?.focus();
  }, [error]);
  if (!error) return null;
  const lines = detailLines(error);
  return (
    <div ref={ref} className="error-summary" role="alert" tabIndex={-1} data-testid="error-summary" data-error-code={error.code}>
      <p className="error-title">{error.outcomeUnknown ? "Not confirmed - nothing is shown as saved" : "This action was not applied"}</p>
      <p>{error.message}</p>
      {lines.length ? <ul>{lines.map((line) => <li key={line}>{line}</li>)}</ul> : null}
      {error.nextAction ? <p><strong>Next:</strong> {error.nextAction}</p> : null}
      {error.outcomeUnknown ? <p className="hint">Your entries are kept. Retrying re-sends the same command, which is applied at most once.</p> : <p className="hint">Your entries are kept.</p>}
      {onDismiss ? <Button variant="quiet" onClick={onDismiss}>Dismiss</Button> : null}
    </div>
  );
}

/** Modal dialog on the native element: focus is trapped, Escape closes, focus returns to the opener. */
export function Dialog({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      // Start in the first field (or the first action) rather than on the Close button.
      const first = dialog.querySelector<HTMLElement>("input, textarea, select") ?? dialog.querySelector<HTMLElement>(".btn-primary");
      first?.focus();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    // Escape (cancel) updates state immediately. The native close event is queued, so a stale one that
    // arrives after the dialog was reopened is ignored.
    <dialog ref={ref} className="dialog" aria-labelledby={titleId} onCancel={onClose} onClose={() => { if (!ref.current?.open) onClose(); }}>
      {open ? (
        <>
          <header className="card-head">
            <h2 id={titleId}>{title}</h2>
            <Button variant="quiet" onClick={onClose} aria-label={`Close ${title}`}>Close</Button>
          </header>
          {children}
        </>
      ) : null}
    </dialog>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Meta({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="meta">
      {items.filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => (
        <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
      ))}
    </dl>
  );
}

export function Loading({ what }: { what: string }) {
  return <div className="loading-state" role="status" aria-busy="true"><p>Loading {what}…</p><div aria-hidden="true"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div></div>;
}

/** Native disclosure preserves form drafts and keyboard support while reducing visual load. */
export function Disclosure({ title, children, open = false }: { title: string; children: ReactNode; open?: boolean }) {
  return <details className="disclosure" open={open || undefined}><summary>{title}</summary><div className="disclosure-body">{children}</div></details>;
}
