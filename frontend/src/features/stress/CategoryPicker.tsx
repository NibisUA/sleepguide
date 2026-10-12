import { useTranslation } from "react-i18next";

import { Chip } from "../../components/ui";
import { STRESS_CATEGORIES } from "../../lib/stress";
import type { StressCategory } from "../../types/api";

/** Optional reason chips. Tapping the selected chip again clears it (`null`). */
export function CategoryPicker({
  value,
  onChange,
  disabled,
}: {
  value: StressCategory | null;
  onChange: (value: StressCategory | null) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-2">
      {STRESS_CATEGORIES.map((category) => (
        <Chip
          key={category}
          selected={value === category}
          disabled={disabled}
          onClick={() => onChange(value === category ? null : category)}
        >
          {t(`stress.categories.${category}`)}
        </Chip>
      ))}
    </div>
  );
}
