import { describe, expect, it } from "vitest";
import { durationCandidates } from "./ocrParser";
describe("OCR duration choices", () => {
  it("reads Ukrainian and English units, zeroes, and deduplicates", () => {
    expect(durationCandidates("Екранний час: 4 год 25 хв\n4h 25m\nTotal 0 min\nMail 35 minutes").map(c => c.minutes)).toEqual([265,0,35]);
  });
  it("does not interpret a clock, week number or partial word as a duration", () => {
    expect(durationCandidates("12:30\n1500 minutes\n4 hours 99 minutes\n25h 0min\n3 hello\n7 may")).toEqual([]);
  });
  it("does not claim a weekly average is a total", () => {
    expect(durationCandidates("Screen Time weekly average 5h 3m")[0].suggested).toBe(false);
    expect(durationCandidates("Загальний час 5 год 3 хв")[0].suggested).toBe(true);
  });
});
