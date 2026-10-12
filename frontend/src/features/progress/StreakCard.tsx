import { useTranslation } from "react-i18next";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useProgress } from "./api";

export function StreakCard() {
  const { t } = useTranslation();
  const query = useProgress();
  if (query.isPending) return <Skeleton />;
  if (query.isError) return <QueryError error={query.error} retry={() => void query.refetch()} />;
  const all = query.data.streaks.find(row => row.kind === "all")!;
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("streaks.title")}</h2>
    <div className="mt-3 flex items-end justify-between gap-3">
      <p className="text-3xl font-semibold text-primary">{t("streaks.days", { n: all.current })}</p>
      <p className="text-right text-xs text-muted">{t("streaks.best", { n: all.longest })}</p>
    </div>
    <p className="mt-2 text-sm text-muted">{t(all.current === 0 ? "streaks.start" : all.counted_today ? "streaks.todayDone" : "streaks.todayOpen")}</p>
    <details className="mt-3"><summary className="cursor-pointer py-2 text-sm text-primary">{t("streaks.details")}</summary>
      <p className="mt-1 text-xs text-muted">{t("streaks.rules")}</p>
      <dl className="mt-3 space-y-3">{query.data.streaks.filter(row => row.kind !== "all").map(row => <div key={row.kind} className="flex items-start justify-between gap-3 text-sm">
        <dt>{t(`streaks.kinds.${row.kind}`)}</dt><dd className="text-right"><span className="font-semibold">{t("streaks.days", { n: row.current })}</span>
          <p className="text-xs text-muted">{t("streaks.best", { n: row.longest })}</p></dd>
      </div>)}</dl>
    </details>
  </section>;
}
