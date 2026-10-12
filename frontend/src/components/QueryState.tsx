import { useTranslation } from "react-i18next";
import { ApiError } from "../lib/api";

export function Skeleton() {
  const { t } = useTranslation();
  return <div role="status" aria-label={t("common.loading")} className="animate-pulse rounded-3xl bg-surface p-5">
    <span className="sr-only">{t("common.loading")}</span>
    <div className="h-4 w-2/3 rounded bg-muted/20" />
    <div className="mt-4 h-12 rounded bg-muted/10" />
  </div>;
}
export function QueryError({ error, retry }: { error?: unknown; retry: () => void }) {
  const { t, i18n } = useTranslation();
  const key = error instanceof ApiError ? `errors.${error.code}` : "common.error";
  return <div role="alert" className="rounded-2xl border border-danger/30 bg-surface p-4">
    <p className="text-sm text-danger">{i18n.exists(key) ? t(key) : t("common.error")}</p>
    <button type="button" onClick={retry} className="mt-2 min-h-10 text-sm text-primary">{t("common.retry")}</button>
  </div>;
}
