import { useTranslation } from "react-i18next";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useInsights } from "./api";
import { InsightCard } from "./InsightCard";

export function LatestInsight() {
  const { t } = useTranslation();
  const list = useInsights();
  if (list.isPending) return <Skeleton />;
  if (list.isError) return <QueryError error={list.error} retry={() => void list.refetch()} />;
  if (!list.data.length) return null;
  return <section aria-label={t("insights.latest")}>
    <h2 className="mb-2 text-sm text-muted">{t("insights.latest")}</h2>
    <InsightCard insight={list.data[0]} />
  </section>;
}
