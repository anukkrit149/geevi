export type RelTime = { value: number; unit?: string; anchor?: string; precision?: string; basis?: string };

/** Relative demonstration day. These illustrate workflow only; they are not recommended clinical timing. */
export function day(time: Record<string, unknown> | RelTime | null | undefined): string {
  if (!time || typeof time.value !== "number") return "time not recorded";
  return `Day ${time.value}`;
}

export function relDay(value: number): RelTime {
  return { value, unit: "day", anchor: "episode-day-0", precision: "day", basis: "fictional relative demonstration day" };
}

export function when(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function short(id: string | null | undefined): string {
  return id ? id.slice(0, 8) : "—";
}

export function words(value: string | null | undefined): string {
  return (value ?? "").replaceAll("_", " ");
}

/** A reported value with its units, without repeating units the source wording already contains. */
export function valueWithUnits(value: string | null | undefined, units: string | null | undefined): string {
  const text = value ?? "—";
  return units && !text.includes(units) ? `${text} ${units}` : text;
}
