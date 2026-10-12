import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

it("shows a named recovery control without revealing a failed chunk's details", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken(): never { throw new Error("internal-private-detail"); }
  try {
    render(<ErrorBoundary><Broken /></ErrorBoundary>);
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button").textContent).toBeTruthy();
    expect(screen.queryByText("internal-private-detail")).toBeNull();
  } finally { consoleError.mockRestore(); }
});
