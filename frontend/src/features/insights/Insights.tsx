import { useTranslation } from "react-i18next";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useInsights, useInsightsProgress } from "./api";
import { InsightCard } from "./InsightCard";
import { PersonalInsights } from "../personal/PersonalInsights";

const TOPICS = ["screen", "workout", "stress", "bedtime"] as const;
export function Insights() {
  const { t } = useTranslation();
  const list = useInsights();
  const progress = useInsightsProgress();
  const p = progress.data;
  const shown = p ? Math.min(p.days, p.required_days) : 0;
  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-semibold">{t("insights.title")}</h1>
      <PersonalInsights />
      {progress.isPending ? <Skeleton /> : progress.isError ? (
        <QueryError error={progress.error} retry={() => void progress.refetch()} />
      ) : p && (
        <section className="rounded-3xl bg-surface p-5">
          <p className="font-medium">{p.ready ? t("insights.ready") : t("insights.locked", { n: p.required_days })}</p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-bg" role="progressbar"
            aria-label={t("insights.title")} aria-valuemin={0} aria-valuemax={p.required_days} aria-valuenow={shown}>
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${shown / p.required_days * 100}%` }} />
          </div>
          <p className="mt-2 text-sm text-muted">{t("insights.progress", { done: p.days, total: p.required_days })}</p>
          <p className="mt-2 text-xs text-muted">{t("insights.window", { n: p.window_days, minimum: p.minimum_group_days })}</p>
          <p className="mt-2 text-xs text-muted">{t("insights.paired", { screen: p.paired_screen_days, stress: p.paired_stress_days })}</p>
        </section>
      )}
      {list.isPending ? <Skeleton /> : list.isError ? (
        <QueryError error={list.error} retry={() => void list.refetch()} />
      ) : list.data.length ? list.data.map(insight => <InsightCard key={insight.id} insight={insight} />) : p?.ready && (
        <section className="rounded-3xl bg-surface p-5"><p>{t("insights.noPatterns")}</p></section>
      )}
      <section className="rounded-3xl bg-surface p-5">
        <h2 className="font-medium">{t("insights.willLook")}</h2>
        <ul className="mt-3 space-y-2 text-sm text-muted">
          {TOPICS.map(topic => <li key={topic}>• {t(`insights.topics.${topic}`)}</li>)}
        </ul>
        <p className="mt-4 text-xs text-muted">{t("insights.note")}</p>
      </section>
    </main>
  );
}
