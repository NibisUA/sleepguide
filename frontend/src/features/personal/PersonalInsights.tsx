import { useTranslation } from "react-i18next";
import { Card } from "../../components/ui";
import { QueryError, Skeleton } from "../../components/QueryState";
import { formatDate, formatDuration } from "../../lib/format";
import { useBaselines, useCalibration, useMilestones } from "./api";
import { ShareCard } from "./ShareCard";

export function PersonalInsights() {
  const { t, i18n } = useTranslation();
  const baselines = useBaselines();
  const milestones = useMilestones();
  const calibration = useCalibration();
  function metric(key: string, value: number | null) {
    if (value === null) return "—";
    return key === "sleep" || key === "screen" ? formatDuration(t, Math.round(value)) :
      `${value.toLocaleString(i18n.language, { maximumFractionDigits: 1 })}${key === "stress" ? "/5" : ` ${t("personal.goals.daysUnit")}`}`;
  }
  return <>
    {baselines.isPending ? <Skeleton /> : baselines.isError ? <QueryError error={baselines.error} retry={() => void baselines.refetch()} /> : <Card>
      <h2 className="font-medium">{t("personal.baselines.title")}</h2>
      <p className="mt-2 text-xs text-muted">{t("personal.baselines.hint")}</p>
      <p className="mt-2 text-xs text-muted">{formatDate(baselines.data.recent_from, i18n.language)} – {formatDate(baselines.data.recent_to, i18n.language)} · {t("personal.baselines.recent")}</p>
      <p className="text-xs text-muted">{formatDate(baselines.data.baseline_from, i18n.language)} – {formatDate(baselines.data.baseline_to, i18n.language)} · {t("personal.baselines.baseline")}</p>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {baselines.data.metrics.map(m => <div key={m.key} className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t(`personal.baselines.${m.key}`)}</p>
          <p className="mt-1 text-lg font-semibold">{metric(m.key, m.recent)}</p>
          <p className="mt-1 text-xs text-muted">{t("personal.baselines.vs")} {metric(m.key, m.baseline)}</p>
          <p className="mt-2 text-xs text-primary">{m.ready && m.delta !== null ? `${m.delta > 0 ? "+" : m.delta < 0 ? "−" : ""}${m.key === "stress" ? Math.abs(m.delta).toLocaleString(i18n.language) : metric(m.key, Math.abs(m.delta))}` : t("personal.baselines.collecting")}</p>
          <p className="mt-1 text-xs text-muted">{t("personal.baselines.sample", { recent: m.recent_days, baseline: m.baseline_days })}</p>
        </div>)}
      </div>
      <p className="mt-3 text-xs text-muted">{t("personal.baselines.note")}</p>
      <ShareCard data={baselines.data} />
    </Card>}
    {milestones.isPending ? <Skeleton /> : milestones.isError ? <QueryError error={milestones.error} retry={() => void milestones.refetch()} /> : <Card>
      <h2 className="font-medium">{t("personal.goals.title")}</h2>
      <p className="mt-1 text-xs text-muted">{formatDate(milestones.data.week_from, i18n.language)} – {formatDate(milestones.data.week_to, i18n.language)}</p>
      <div className="mt-4 space-y-3">{milestones.data.goals.filter(g => g.target > 0).map(g => <div key={g.kind}>
        <p className="flex justify-between gap-2 text-sm"><span>{t(`personal.goals.${g.kind}`)}</span><span>{g.done}/{g.target} {g.done >= g.target ? "✓" : ""}</span></p>
        <progress className="mt-1 h-2 w-full accent-primary" aria-label={t(`personal.goals.${g.kind}`)} value={Math.min(g.done, g.target)} max={g.target} />
      </div>)}</div>
      {!milestones.data.goals.some(g => g.target > 0) && <p className="mt-3 text-sm text-muted">{t("personal.goals.allOff")}</p>}
      <p className="mt-3 text-xs text-muted">{t("personal.goals.settings")}</p>
      <h3 className="mt-5 font-medium">{t("personal.awards.title")}</h3>
      <div className="mt-3 grid grid-cols-2 gap-2">{milestones.data.achievements.map(a => <div key={a.key} className={`rounded-2xl border p-3 ${a.earned_on ? "border-primary/40 bg-primary/10" : "border-muted/20"}`}>
        <p className="text-sm">{a.earned_on ? "✓ " : "○ "}{t(`personal.awards.${a.key}`)}</p>
        <p className="mt-1 text-xs text-muted">{a.earned_on ? formatDate(a.earned_on, i18n.language, {day: "numeric", month: "short", year: "numeric"}) : `${a.done}/${a.target}`}</p>
      </div>)}</div>
      <p className="mt-3 text-xs text-muted">{t("personal.awards.hint")}</p>
    </Card>}
    {calibration.isPending ? <Skeleton /> : calibration.isError ? <QueryError error={calibration.error} retry={() => void calibration.refetch()} /> : <Card>
      <h2 className="font-medium">{t("personal.calibration.title")}</h2>
      <p className="mt-2 text-sm text-primary">{t(`personal.calibration.${calibration.data.status}`)}</p>
      <p className="mt-2 text-sm">{t("personal.calibration.progress", { n: calibration.data.matched_nights, total: calibration.data.required_nights })}</p>
      <p className="mt-2 text-xs text-muted">{t("personal.calibration.excluded", { stale: calibration.data.stale_ratings, limited: calibration.data.limited_nights })}</p>
      {calibration.data.correlation !== null && <p className="mt-2 text-sm">{t("personal.calibration.correlation", { n: calibration.data.correlation })}</p>}
      <p className="mt-3 text-xs text-muted">{t("personal.calibration.hint", { version: calibration.data.algorithm_version })}</p>
    </Card>}
  </>;
}
