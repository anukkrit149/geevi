import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge, ErrorSummary } from "@/components/ui";
import { hrefFor } from "@/features/today/Today";
import { ApiError, toApiError } from "@/lib/api/client";
import { day, relDay } from "@/lib/format";

describe("ErrorSummary", () => {
  it("is announced, focused, names the next action and says the draft is kept", () => {
    const error = new ApiError("stale_dependency", "Relevant material changed after this exact version was frozen.", 409, "Review the listed changes, reopen the draft and re-submit.", {
      changes: [{ scope: "patient/p1/reports/molecular", last_change: { event: "source.associated", actor: "Mira", title: "Molecular panel" } },
        { read: { kind: "observation_version" }, reason: "Cellularity is no longer current: Corrected by issuer report version 2." }],
    });
    render(<ErrorSummary error={error} />);
    const summary = screen.getByRole("alert");
    expect(document.activeElement).toBe(summary);
    expect(summary.getAttribute("data-error-code")).toBe("stale_dependency");
    expect(summary.textContent).toContain("This action was not applied");
    expect(summary.textContent).toContain("Changed: reports/molecular - source.associated “Molecular panel” by Mira");
    expect(summary.textContent).toContain("Cellularity is no longer current");
    expect(summary.textContent).toContain("Next: Review the listed changes");
    expect(summary.textContent).toContain("Your entries are kept.");
  });

  it("never claims success when the outcome is unknown", () => {
    render(<ErrorSummary error={new ApiError("network_unknown_outcome", "The server could not be reached, so the outcome is unknown.", 0)} />);
    expect(screen.getByRole("alert").textContent).toContain("Not confirmed - nothing is shown as saved");
    expect(screen.getByRole("alert").textContent).toContain("applied at most once");
  });

  it("lists failed requirement gates and revision conflicts", () => {
    const { rerender } = render(<ErrorSummary error={new ApiError("exception_not_approved", "Blocked", 422, null, { gates: [{ requirement_id: "REQ-VENUE", message: "The operational exception for REQ-VENUE is pending." }] })} />);
    expect(screen.getByRole("alert").textContent).toContain("REQ-VENUE: The operational exception for REQ-VENUE is pending.");
    rerender(<ErrorSummary error={new ApiError("stale_target", "Changed", 409, null, { expected_revision: 1, current_revision: 2 })} />);
    expect(screen.getByRole("alert").textContent).toContain("You loaded revision 1; the current revision is 2.");
  });

  it("renders nothing without an error", () => {
    const { container } = render(<ErrorSummary error={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("typed error mapping", () => {
  it("maps the API error envelope and falls back safely for anything else", () => {
    const mapped = toApiError({ error: { code: "actor_not_permitted", message: "No grant", next_action: "Ask", target: { kind: "plan", id: "1" }, details: { required_capability: "plan.approve" } } }, 403);
    expect([mapped.code, mapped.status, mapped.nextAction, mapped.outcomeUnknown]).toEqual(["actor_not_permitted", 403, "Ask", false]);
    const unknown = toApiError("<html>bad gateway</html>", 502);
    expect([unknown.code, unknown.outcomeUnknown]).toEqual(["unexpected_failure", true]);
  });
});

describe("presentation helpers", () => {
  it("shows statuses as text, never by colour alone, and source text is not interpreted as markup", () => {
    render(<Badge value="review_needed" />);
    expect(screen.getByText("review needed").getAttribute("data-status")).toBe("review_needed");
    render(<p data-testid="t">{"<img src=x onerror=alert(1)>"}</p>);
    expect(screen.getByTestId("t").querySelector("img")).toBeNull();
  });

  it("formats relative demonstration days without inventing a calendar", () => {
    expect(day(relDay(-1))).toBe("Day -1");
    expect(day(null)).toBe("time not recorded");
    expect(relDay(3)).toMatchObject({ unit: "day", anchor: "episode-day-0" });
  });

  it("links worklist items to exact, workspace-scoped pages", () => {
    expect(hrefFor("w1", { kind: "impact", patient_id: "p1", target_kind: "impact_review", target_id: "i1" })).toBe("/w/w1/impacts");
    expect(hrefFor("w1", { kind: "source", patient_id: "p1", target_kind: "source_document", target_id: "d1" })).toBe("/w/w1/patients/p1/sources/d1");
    expect(hrefFor("w1", { kind: "expected_input", patient_id: "p1", target_kind: "expected_input", target_id: "e1" })).toBe("/w/w1/patients/p1/sources#readiness");
    expect(hrefFor("w1", { kind: "review", patient_id: null, target_kind: "protocol_version", target_id: "v1" })).toBe("/w/w1/department/protocols/v1");
  });
});
