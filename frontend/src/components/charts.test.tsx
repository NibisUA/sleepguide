import { render } from "@testing-library/react";
import { expect, it } from "vitest";
import { ScoreLine } from "./charts";

it("does not connect score points across missing days", () => {
  const { container } = render(<ScoreLine locale="en" days={[
    { date: "2026-10-01", score: 80 }, { date: "2026-10-02", score: null },
    { date: "2026-10-03", score: 90 },
  ]} />);
  const path = container.querySelector("path")!.getAttribute("d")!;
  expect(path.match(/M/g)?.length).toBe(2);
  expect(path.includes("L")).toBe(false);
});
