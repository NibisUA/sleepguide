import { QueryError, Skeleton } from "../../components/QueryState";
import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { formatDuration } from "../../lib/format";
import { IntegrationsSection } from "../integrations/IntegrationsSection";
import { useMe, useUpdateMe } from "../profile/api";
import { PrivacySection } from "../privacy/PrivacySection";
import { GoalsSettings } from "../personal/GoalsSettings";
import { useBaselines } from "../personal/api";

const GOAL_OPTIONS = [360, 390, 420, 450, 480, 510, 540, 570, 600]; // 6 h .. 10 h
const DEFAULT_BEDTIME = "23:00";
const DEFAULT_EVENING_REMINDER = "22:30";
const LANGUAGES = ["uk", "en"] as const;

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl bg-surface p-5">
      <h2 className="font-medium">{title}</h2>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function Settings({ onDeleted }: { onDeleted: () => void }) {
  const { t, i18n } = useTranslation();
  const me = useMe();
  const update = useUpdateMe();
  const baselines = useBaselines();
  const user = me.data;
  const [bedtime, setBedtime] = useState("");
  const [evening, setEvening] = useState("");

  // Keep the local field in sync with the saved value (e.g. after "reset").
  useEffect(() => {
    setBedtime(user?.target_bedtime?.slice(0, 5) ?? "");
  }, [user?.target_bedtime]);

  useEffect(() => {
    setEvening(user?.reminder_evening_time?.slice(0, 5) ?? "");
  }, [user?.reminder_evening_time]);

  if (me.isPending) {
    return <main className="mx-auto max-w-md p-4"><Skeleton /></main>;
  }
  if (me.isError || !user) {
    return <main className="mx-auto max-w-md p-4"><QueryError error={me.error} retry={() => void me.refetch()} /></main>;
  }

  const goals = GOAL_OPTIONS.includes(user.sleep_goal_minutes)
    ? GOAL_OPTIONS
    : [...GOAL_OPTIONS, user.sleep_goal_minutes].sort((a, b) => a - b);

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-semibold">{t("settings.title")}</h1>

      <Section title={t("settings.sleepGoal")} hint={t("settings.sleepGoalHint")}>
        <select
          aria-label={t("settings.sleepGoal")}
          value={user.sleep_goal_minutes}
          onChange={(event) => update.mutate({ sleep_goal_minutes: Number(event.target.value) })}
          className="w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        >
          {goals.map((minutes) => (
            <option key={minutes} value={minutes}>
              {formatDuration(t, minutes)}
            </option>
          ))}
        </select>
      </Section>

      <Section
        title={t("settings.targetBedtime")}
        hint={t("settings.targetBedtimeHint", { time: DEFAULT_BEDTIME })}
      >
        <input
          type="time"
          aria-label={t("settings.targetBedtime")}
          value={bedtime}
          onChange={(event) => {
            const value = event.target.value;
            setBedtime(value);
            if (/^\d{2}:\d{2}$/.test(value)) update.mutate({ target_bedtime: value });
          }}
          className="w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
        {user.target_bedtime !== null && (
          <button
            type="button"
            disabled={update.isPending}
            onClick={() => {
              setBedtime("");
              update.mutate({ target_bedtime: null });
            }}
            className="mt-2 text-sm text-primary disabled:opacity-60"
          >
            {t("settings.useDefault", { time: DEFAULT_BEDTIME })}
          </button>
        )}
      </Section>

      <Section title={t("settings.reminders")} hint={t("settings.remindersHint")}>
        <label className="mb-4 flex items-center justify-between gap-3">
          <span>{t("personal.reminder.title")}<span className="mt-1 block text-xs text-muted">{t("personal.reminder.hint")}</span></span>
          <input type="checkbox" className="h-5 w-5 shrink-0 accent-primary" disabled={update.isPending}
            checked={user.reminder_pattern_on} onChange={e => update.mutate({ reminder_pattern_on: e.target.checked })} />
        </label>
        {user.reminder_pattern_on && <p className="mb-4 rounded-xl bg-bg p-3 text-sm text-primary">
          {baselines.data?.reminder.time ? t("personal.reminder.ready", { time: baselines.data.reminder.time, bedtime: baselines.data.reminder.bedtime }) : t("personal.reminder.collecting")}
        </p>}
        <label className="flex items-center justify-between gap-3">
          <span>{user.reminder_pattern_on ? t("personal.reminder.fallback") : t("settings.eveningReminder")}</span>
          <input
            type="checkbox"
            className="h-5 w-5 accent-primary"
            checked={user.reminder_evening_time !== null}
            onChange={(event) =>
              update.mutate({
                reminder_evening_time: event.target.checked ? DEFAULT_EVENING_REMINDER : null,
              })
            }
          />
        </label>
        {user.reminder_evening_time !== null && (
          <input
            type="time"
            aria-label={t("settings.eveningReminder")}
            value={evening}
            onChange={(event) => {
              const value = event.target.value;
              setEvening(value);
              if (/^\d{2}:\d{2}$/.test(value)) update.mutate({ reminder_evening_time: value });
            }}
            className="mt-3 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
          />
        )}
        <label className="mt-4 flex items-center justify-between gap-3">
          <span>
            {t("settings.morningReminder")}
            <span className="block text-sm text-muted">{t("settings.morningReminderHint")}</span>
          </span>
          <input
            type="checkbox"
            className="h-5 w-5 shrink-0 accent-primary"
            checked={user.reminder_morning_on}
            onChange={(event) => update.mutate({ reminder_morning_on: event.target.checked })}
          />
        </label>
      </Section>

      <Section title={t("settings.language")}>
        <div className="flex gap-2">
          {LANGUAGES.map((language) => (
            <button
              key={language}
              aria-pressed={i18n.language === language}
              type="button"
              onClick={() => {
                void i18n.changeLanguage(language);
                update.mutate({ language });
              }}
              className={`flex-1 rounded-2xl border py-3 font-medium ${
                i18n.language === language
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-muted/30 text-muted"
              }`}
            >
              {t(`settings.lang.${language}`)}
            </button>
          ))}
        </div>
      </Section>

      <IntegrationsSection />
      <GoalsSettings />
      <PrivacySection onDeleted={onDeleted} />

      <Section title={t("settings.timezone")} hint={t("settings.timezoneHint")}>
        <p className="text-sm">{user.timezone}</p>
      </Section>

      {update.isError && <p className="text-sm text-danger">{t("common.error")}</p>}
    </main>
  );
}
