import { Modal } from "../../components/Modal";
import { useTranslation } from "react-i18next";

import type { QuickTarget } from "../../lib/focusCard";

const OPTIONS: { target: QuickTarget; icon: string }[] = [
  { target: "sleep", icon: "🌙" },
  { target: "workout", icon: "🏋️" },
  { target: "stress", icon: "🧠" },
  { target: "screen", icon: "📱" },
];

export function QuickAddSheet({
  onPick,
  onClose,
}: {
  onPick: (target: QuickTarget) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Modal title={t("quick.title")} onClose={onClose}>
        <h2 className="font-semibold">{t("quick.title")}</h2>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {OPTIONS.map(({ target, icon }) => (
            <button
              key={target}
              type="button"
              onClick={() => onPick(target)}
              className="rounded-2xl bg-surface p-4 text-left transition active:scale-[0.98]"
            >
              <span className="text-2xl">{icon}</span>
              <span className="mt-2 block font-medium">{t(`quick.${target}`)}</span>
              <span className="block text-xs text-muted">{t(`quick.${target}Hint`)}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("day.close")}
        </button>
    </Modal>
  );
}
