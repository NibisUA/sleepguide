import { useTranslation } from "react-i18next";
import { formatDate } from "../../lib/format";
import type { Insight } from "../../types/api";

const ICON = { screen_sleep: "📱", workout_sleep: "🏋️", stress_score: "🧠", bedtime_score: "🌙" };
export function InsightCard({ insight }: { insight: Insight }) {
  const { t, i18n } = useTranslation();
  const format = (value: string | number) => typeof value === "number"
    ? value.toLocaleString(i18n.language, { maximumFractionDigits: 1 }) : value;
  const params = Object.fromEntries(Object.entries(insight.params).map(([key, value]) => [key, format(value)]));
  return (
    <article className="rounded-3xl border border-primary/20 bg-surface p-5">
      <h2 className="font-medium">{ICON[insight.type]} {t(`insights.types.${insight.type}`)}</h2>
      <p className="mt-3 leading-relaxed">{t(insight.message_key, params)}</p>
      <p className="mt-3 text-sm text-muted">{t("insights.basedOn", { n: insight.sample_days })}</p>
      <p className="mt-1 text-xs text-muted">{formatDate(insight.period_start, i18n.language)} – {formatDate(insight.period_end, i18n.language)}</p>
      <details className="mt-3 text-xs text-muted">
        <summary className="cursor-pointer text-primary">{t("insights.comparison")}</summary>
        <p className="mt-2">{t("insights.groups", { ...params, unit: t(insight.type.endsWith("sleep") ? "insights.minutes" : "insights.points") })}</p>
      </details>
    </article>
  );
}
