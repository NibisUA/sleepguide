export type QuickTarget = "sleep" | "workout" | "stress" | "screen";

/** Scroll a Home card into view and flash a ring around it (cards carry `id="card-<target>"`). */
export function focusCard(target: QuickTarget): void {
  const element = document.getElementById(`card-${target}`);
  if (!element) return;
  element.scrollIntoView({ behavior: "smooth", block: "start" });
  element.classList.add("ring-2", "ring-primary", "rounded-3xl");
  window.setTimeout(() => element.classList.remove("ring-2", "ring-primary"), 1600);
}
