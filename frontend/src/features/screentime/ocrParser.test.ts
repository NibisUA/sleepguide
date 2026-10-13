import { describe, expect, it } from "vitest";
import { categoryCandidates, durationCandidates, type OcrWord } from "./ocrParser";
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

describe("category suggestions", () => {
  it("reads English and Ukrainian labelled values", () => {
    expect(categoryCandidates("Social 5h 26m\nEntertainment 1h 13m\nGames 53m")).toEqual({ social_minutes: 326, entertainment_minutes: 73, games_minutes: 53 });
    expect(categoryCandidates("Соцмережі 2 год\nРозваги 30 хв\nІгри 0 хв")).toEqual({ social_minutes: 120, entertainment_minutes: 30, games_minutes: 0 });
  });
  it("reads a category header row followed by duration columns", () => {
    expect(categoryCandidates("Social Entertainment Games\n5h 26m 1h 13m 53m")).toEqual({ social_minutes: 326, entertainment_minutes: 73, games_minutes: 53 });
  });
  it("does not invent unknown categories or choose between conflicting values", () => {
    expect(categoryCandidates("Screen Time 9h 2m\n5h\n60m\n30m")).toEqual({});
    expect(categoryCandidates("Social 1h\nSocial 2h\nGames 0m")).toEqual({ games_minutes: 0 });
  });
  it("handles the iOS thin-font hour OCR without discarding the hour", () => {
    expect(categoryCandidates("Entertainment Th 13m")).toEqual({ entertainment_minutes: 73 });
    expect(categoryCandidates("Entertainment lh 13m")).toEqual({ entertainment_minutes: 73 });
    expect(categoryCandidates("Entertainment oh 13m")).toEqual({});
  });
  it("associates values below category labels using OCR positions", () => {
    const word = (text: string, x0: number, y0: number): OcrWord => ({ text, confidence: 95, bbox: { x0, y0, x1: x0 + 70, y1: y0 + 20 } });
    const words = [word("Social", 10, 100), word("Entertainment", 210, 100), word("Games", 410, 100),
      word("5h", 10, 135), word("26m", 80, 135), word("1h", 210, 135), word("13m", 280, 135), word("53m", 410, 135), word("60m", 500, 20)];
    expect(categoryCandidates("Social\nEntertainment\nGames\n5h\n26m\n1h\n13m\n53m", words)).toEqual({ social_minutes: 326, entertainment_minutes: 73, games_minutes: 53 });
  });
});
