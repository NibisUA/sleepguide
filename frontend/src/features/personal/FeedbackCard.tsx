import { useTranslation } from "react-i18next";
import { useFeedback, useSaveFeedback } from "./api";

export function FeedbackCard({ day }: { day: string }) {
  const { t } = useTranslation();
  const query = useFeedback(day);
  const save = useSaveFeedback(day);
  return <div className="mt-4 border-t border-muted/10 pt-4">
    <p className="text-sm font-medium">{t("personal.feedback.title")}</p>
    <p className="mt-1 text-xs text-muted">{t("personal.feedback.hint")}</p>
    <div className="mt-3 grid grid-cols-5 gap-2" role="group" aria-label={t("personal.feedback.title")}>
      {[1, 2, 3, 4, 5].map(rating => <button key={rating} type="button" disabled={save.isPending || query.isPending || query.isError}
        aria-label={t(`personal.feedback.r${rating}`)} aria-pressed={query.data?.rating === rating}
        onClick={() => save.mutate(rating)}
        className={`rounded-xl border py-3 disabled:opacity-50 ${query.data?.rating === rating ? "border-primary bg-primary/15 text-primary" : "border-muted/30"}`}>{rating}</button>)}
    </div>
    <p className="mt-2 text-xs text-muted">{t("personal.feedback.scale")}</p>
    {query.data && <button type="button" disabled={save.isPending} className="mt-2 text-xs text-muted" onClick={() => save.mutate(null)}>{t("personal.feedback.remove")}</button>}
    {(query.isError || save.isError) && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}
      {query.isError && <button type="button" className="ml-2 underline" onClick={() => void query.refetch()}>{t("common.retry")}</button>}
    </p>}
  </div>;
}
