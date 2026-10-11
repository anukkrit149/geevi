/** Geevi's identity is a wordmark, with no separate symbol. */
export function Brand() {
  return <span className="brand-lockup" aria-label="Geevi"><span className="brand-wordmark">geevi<span className="brand-period">.</span></span></span>;
}

export function Initials({ name, className = "" }: { name: string; className?: string }) {
  const letters = name.replace(/\([^)]*\)/g, "").replace(/^(Dr\.?|Mr\.?|Ms\.?)\s+/i, "").trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("");
  return <span className={`avatar ${className}`} aria-hidden="true">{letters}</span>;
}
