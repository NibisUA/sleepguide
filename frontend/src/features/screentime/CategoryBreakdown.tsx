import { useTranslation } from "react-i18next";
import { formatDuration } from "../../lib/format";
import { categoryDistribution, SCREEN_CATEGORIES, type ScreenCategories } from "./categories";

export function CategoryBreakdown({ total, categories, compact = false }: { total: number; categories: ScreenCategories; compact?: boolean }) {
  const { t } = useTranslation();
  const distribution = categoryDistribution(total, categories);
  if (!distribution.valid) return <p role="alert" className="mt-2 text-sm text-danger">{t("screen.categoriesInvalid")}</p>;
  return <div className="mt-3">
    <div aria-hidden="true" className="flex h-2 overflow-hidden rounded-full bg-muted/20">
      {total > 0 && SCREEN_CATEGORIES.map(({ field, color }) => <span key={field} className={color} style={{ width: `${(categories[field] ?? 0) / total * 100}%` }} />)}
    </div>
    <dl className={compact ? "mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs" : "mt-3 grid grid-cols-3 gap-3 text-sm"}>
      {SCREEN_CATEGORIES.map(({ field, textColor }) => <div key={field} className="min-w-0">
        <dt className={`${textColor} break-words`}>{t(`screen.categoryLabels.${field}`)}</dt>
        <dd className="mt-0.5 font-medium">{categories[field] == null ? "—" : formatDuration(t, categories[field])}</dd>
      </div>)}
    </dl>
    <p className="mt-2 text-xs text-muted">{t(distribution.complete ? "screen.categoriesOther" : "screen.categoriesUnassigned")}: {formatDuration(t, distribution.remaining)}</p>
  </div>;
}
