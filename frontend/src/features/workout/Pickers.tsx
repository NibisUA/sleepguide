import { useTranslation } from "react-i18next";

import { Chip } from "../../components/ui";
import type { WorkoutIntensity, WorkoutType } from "../../types/api";
import { TYPE_ICON, WORKOUT_INTENSITIES, WORKOUT_TYPES } from "./meta";

export function TypePicker({
  value,
  onChange,
  disabled,
}: {
  value: WorkoutType;
  onChange: (value: WorkoutType) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-2">
      {WORKOUT_TYPES.map((type) => (
        <Chip key={type} selected={value === type} disabled={disabled} onClick={() => onChange(type)}>
          {TYPE_ICON[type]} {t(`workout.types.${type}`)}
        </Chip>
      ))}
    </div>
  );
}

export function IntensityPicker({
  value,
  onChange,
  disabled,
}: {
  value: WorkoutIntensity;
  onChange: (value: WorkoutIntensity) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap gap-2">
      {WORKOUT_INTENSITIES.map((intensity) => (
        <Chip
          key={intensity}
          selected={value === intensity}
          disabled={disabled}
          onClick={() => onChange(intensity)}
        >
          {t(`workout.intensities.${intensity}`)}
        </Chip>
      ))}
    </div>
  );
}
