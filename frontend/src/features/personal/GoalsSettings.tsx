import { useTranslation } from "react-i18next";
import { useMe, useUpdateMe } from "../profile/api";

export function GoalsSettings() {
  const { t } = useTranslation();
  const me = useMe();
  const update = useUpdateMe();
  if (!me.data) return null;
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("personal.goals.title")}</h2>
    <p className="mt-1 text-sm text-muted">{t("personal.goals.hint")}</p>
    <div className="mt-4 space-y-3">
      {(["sleep", "workout", "stress", "screen"] as const).map(kind => <label key={kind} className="flex items-center justify-between gap-3 text-sm">
        <span>{t(`personal.goals.${kind}`)}</span>
        <select value={me.data![`weekly_${kind}_days`]} disabled={update.isPending}
          onChange={e => update.mutate({ [`weekly_${kind}_days`]: Number(e.target.value) })}
          className="rounded-xl border border-muted/30 bg-bg p-2">
          {[0, 1, 2, 3, 4, 5, 6, 7].map(n => <option key={n} value={n}>{n === 0 ? t("personal.goals.off") : t("personal.goals.days", { n })}</option>)}
        </select>
      </label>)}
    </div>
    {update.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
  </section>;
}
