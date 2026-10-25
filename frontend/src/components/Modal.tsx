import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

export function Modal({ title, onClose, children }: {
  title: string; onClose: () => void; children: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const scroll = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const root = document.getElementById("root");
    const previousInert = root?.inert;
    if (root) root.inert = true;
    const box = panel.current!;
    const controls = () => Array.from(box.querySelectorAll<HTMLElement>(
      'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a[href], [tabindex="0"]',
    ));
    (controls()[0] ?? box).focus();
    function key(event: KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); close.current(); }
      if (event.key !== "Tab") return;
      const items = controls();
      if (!items.length) { event.preventDefault(); box.focus(); return; }
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === box)) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = scroll;
      if (root) root.inert = previousInert ?? false;
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return createPortal(<div className="fixed inset-0 z-50 flex items-end bg-black/60" onClick={onClose}>
    <div ref={panel} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1}
      onClick={event => event.stopPropagation()}
      className="mx-auto max-h-[88dvh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-bg p-5"
      style={{ paddingBottom: "max(2rem, env(safe-area-inset-bottom, 0px), var(--app-safe-bottom, 0px))" }}>
      {children}
    </div>
  </div>, document.body);
}
