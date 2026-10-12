import { QueryError, Skeleton } from "../../components/QueryState";
import { FeedbackCard } from "../personal/FeedbackCard";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

import { addDays, formatDate, formatDuration, isoDate } from "../../lib/format";
import { scoreColor } from "../../lib/score";
import type { SleepScoreComponent } from "../../types/api";
import { useSleepList, useSleepScore } from "./api";

const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const COMPONENT_LABELS: Record<string, string> = {
  duration: "score.duration",
  consistency: "score.consistency",
  sleep_debt: "score.sleepDebt",
  bedtime_timing: "score.bedtimeTiming",
};

function Shell({ children }: { children: ReactNode }) {
  return <section className="rounded-3xl bg-surface p-5">{children}</section>;
}

function Ring({ value }: { value: number }) {
  const score = Math.min(Math.max(value, 0), 100);
  const offset = CIRCUMFERENCE * (1 - score / 100);
  return (
    <div className="relative h-36 w-36 shrink-0">
      <svg aria-hidden="true" viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r={RADIUS}
          fill="none"
          strokeWidth="10"
          className="stroke-muted/20"
        />
        <circle
          cx="60"
          cy="60"
          r={RADIUS}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className={`stroke-current transition-all duration-700 ${scoreColor(score)}`}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`text-4xl font-semibold ${scoreColor(score)}`}>{Math.round(score)}</span>
      </div>
    </div>
  );
}

function componentHint(component: SleepScoreComponent, t: TFunction): string | null {
  const detail = component.detail;
  switch (component.key) {
    case "duration":
      return t("score.durationHint", {
        minutes: formatDuration(t, Number(detail.minutes ?? 0)),
        goal: formatDuration(t, Number(detail.goal_minutes ?? 0)),
      });
    case "consistency":
      return t("score.consistencyHint", {
        bed: Number(detail.bedtime_spread_minutes ?? 0),
        wake: Number(detail.wake_spread_minutes ?? 0),
        nights: Number(detail.nights ?? 0),
      });
    case "sleep_debt":
      return t("score.debtHint", {
        deficit: formatDuration(t, Number(detail.deficit_minutes ?? 0)),
        days: Number(detail.days_counted ?? 0),
      });
    case "bedtime_timing":
      return detail.used_default_target
        ? t("score.bedtimeHintDefault", {
            bedtime: String(detail.bedtime ?? ""),
            target: String(detail.target_bedtime ?? ""),
          })
        : t("score.bedtimeHint", {
            bedtime: String(detail.bedtime ?? ""),
            target: String(detail.target_bedtime ?? ""),
          });
    default:
      return null;
  }
}

function ComponentRow({ component }: { component: SleepScoreComponent }) {
  const { t } = useTranslation();
  const hint = componentHint(component, t);
  const ratio = component.max > 0 ? component.earned / component.max : 0;
  return (
    <li className="py-2">
      <div className="flex items-baseline justify-between text-sm">
        <span>{t(COMPONENT_LABELS[component.key] ?? component.key)}</span>
        <span className="tabular-nums text-muted">
          {component.earned}/{component.max}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted/20">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${Math.round(ratio * 100)}%` }}
        />
      </div>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </li>
  );
}

export function SleepScoreCard() {
  const { t, i18n } = useTranslation();
  const list = useSleepList(10);
  const lastNight = list.data?.find(
    (session) => session.ended_at !== null && !session.is_nap && session.local_date !== null,
  );
  const score = useSleepScore(lastNight?.local_date ?? undefined);

  if (list.isPending || score.isLoading) return <Skeleton />;
  if (list.isError || score.isError) return <QueryError error={list.error ?? score.error} retry={() => { void list.refetch(); void score.refetch(); }} />;

  const data = score.data;
  if (!data) {
    return (
      <Shell>
        <p className="text-sm text-muted">{t("score.empty")}</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="flex items-center gap-5">
        <Ring value={data.score} />
        <div className="min-w-0">
          <p className="text-sm text-muted">{t("score.title")}</p>
          <p className="mt-0.5 text-sm">
            {formatDate(data.date, i18n.language, { day: "numeric", month: "long" })}
          </p>
          <p className="mt-1 text-sm text-muted">{formatDuration(t, data.sleep_minutes)}</p>
          {data.limited_data && (
            <p className="mt-2 inline-block rounded-full bg-warning/15 px-2 py-0.5 text-xs text-warning">
              {t("score.limited")}
            </p>
          )}
        </div>
      </div>
      <ul className="mt-4 border-t border-muted/10">
        {data.components.map((component) => (
          <ComponentRow key={component.key} component={{ ...component, detail: component.detail ?? {} }} />
        ))}
      </ul>
      {data.date >= addDays(isoDate(new Date()), -179) && <FeedbackCard key={data.date} day={data.date} />}
    </Shell>
  );
}
