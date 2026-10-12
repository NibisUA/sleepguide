import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-3xl bg-surface p-5 ${className}`}>{children}</section>;
}

export function PrimaryButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className={`mt-4 w-full rounded-2xl bg-primary py-4 text-lg font-semibold text-on-primary transition active:scale-[0.98] disabled:opacity-60 ${className}`}
    />
  );
}

/** A selectable pill (workout type, intensity, ...). */
export function Chip({
  selected,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { selected: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      {...props}
      className={`rounded-full border px-3 py-1.5 text-sm transition active:scale-[0.97] disabled:opacity-60 ${
        selected ? "border-primary bg-primary/15 font-semibold text-primary" : "border-muted/30 text-muted"
      }`}
    >
      {children}
    </button>
  );
}
