import { useTranslation } from "react-i18next";

/** Two small number fields: hours and minutes (as strings, so an empty field means "not entered"). */
export function DurationInput({
  hours,
  minutes,
  onChange,
  disabled,
  label,
}: {
  hours: string;
  minutes: string;
  onChange: (hours: string, minutes: string) => void;
  disabled?: boolean;
  label?: string;
}) {
  const { t } = useTranslation();
  const field =
    "w-20 rounded-xl border border-muted/30 bg-bg p-3 text-center text-text disabled:opacity-60";
  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={24}
        step={1}
        value={hours}
        disabled={disabled}
        placeholder="0"
        aria-label={label ? `${label}: ${t("screen.hours")}` : t("screen.hours")}
        onChange={(event) => onChange(event.target.value, minutes)}
        className={field}
      />
      <span className="text-sm text-muted">{t("screen.hoursShort")}</span>
      <input
        type="number"
        inputMode="numeric"
        min={0}
        max={59}
        step={1}
        value={minutes}
        disabled={disabled}
        placeholder="0"
        aria-label={label ? `${label}: ${t("screen.minutes")}` : t("screen.minutes")}
        onChange={(event) => onChange(hours, event.target.value)}
        className={field}
      />
      <span className="text-sm text-muted">{t("screen.minutesShort")}</span>
    </div>
  );
}
