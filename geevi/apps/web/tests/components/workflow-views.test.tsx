import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { WorkflowViews } from "@/components/workflow-views";

function Example() {
  return <WorkflowViews label="Patient workflow" initial="plan" views={[
    { id: "plan", label: "Individual plan", content: <label>Draft intent<input /></label> },
    { id: "discussion", label: "Discussion", content: <p>Discussion history</p> },
  ]} />;
}

beforeEach(() => window.history.replaceState({}, "", "/patient?episode=1"));

describe("focused workflows", () => {
  it("keeps unfinished entries when switching views or showing all sections", () => {
    render(<Example />);
    const input = screen.getByLabelText("Draft intent") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Unfinished clinical entry" } });
    fireEvent.click(screen.getByRole("tab", { name: "Discussion" }));
    expect(input.closest("[hidden]")).not.toBeNull();
    expect(window.location.hash).toBe("#discussion");
    expect(window.location.search).toBe("?episode=1");
    fireEvent.click(screen.getByRole("tab", { name: "All sections" }));
    expect(screen.getAllByRole("tabpanel")).toHaveLength(1);
    expect(input.closest("[hidden]")).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Individual plan" }));
    expect(screen.getByLabelText("Draft intent")).toBe(input);
    expect(input.value).toBe("Unfinished clinical entry");
  });

  it("opens linked sections and responds to hash navigation", () => {
    window.history.replaceState({}, "", "/patient#discussion");
    render(<Example />);
    expect(screen.getByRole("tab", { name: "Discussion" }).getAttribute("aria-selected")).toBe("true");
    window.history.replaceState({}, "", "/patient#unknown");
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(screen.getByRole("tab", { name: "Individual plan" }).getAttribute("aria-selected")).toBe("true");
  });

  it("supports arrow, Home and End navigation with one tab stop", () => {
    render(<Example />);
    const plan = screen.getByRole("tab", { name: "Individual plan" });
    plan.focus();
    fireEvent.keyDown(plan, { key: "ArrowRight" });
    const discussion = screen.getByRole("tab", { name: "Discussion" });
    expect(document.activeElement).toBe(discussion);
    expect(plan.tabIndex).toBe(-1);
    fireEvent.keyDown(discussion, { key: "End" });
    const all = screen.getByRole("tab", { name: "All sections" });
    expect(document.activeElement).toBe(all);
    fireEvent.keyDown(all, { key: "Home" });
    expect(document.activeElement).toBe(plan);
  });
});
