import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { formatDuration, formatTime, toLocalInput } from "../../lib/format";
import { useNow } from "../../lib/useNow";
import type { SleepSession } from "../../types/api";
import { useCurrentSleep, useSleepList, useStartSleep, useStopSleep } from "./api";

const FORGOTTEN_STOP_MINUTES = 14 * 60;

function Card({ children }: { children: ReactNode }) {
  return <section className="rounded-3xl bg-surface p-5">{children}</section>;
}

function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="mt-4 w-full rounded-2xl bg-primary py-4 text-lg font-semibold text-bg transition active:scale-[0.98] disabled:opacity-60"
    />
  );
}

function WakeTimePicker({
  onConfirm,
  busy,
  invalid,
}: {
  onConfirm: (iso: string) => void;
  busy: boolean;
  invalid: boolean;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState(() => toLocalInput(new Date()));
  return (
    <div className="mt-4">
      <p className="font-medium">{t("sleep.wakeTitle")}</p>
      <p className="mt-1 text-sm text-muted">{t("sleep.wakeHint")}</p>
      <input
        type="datetime-local"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="mt-3 w-full rounded-xl border border-muted/30 bg-bg p-3"
      />
      {invalid && <p className="mt-2 text-sm text-danger">{t("sleep.invalidTime")}</p>}
      <PrimaryButton disabled={busy || !value} onClick={() => onConfirm(new Date(value).toISOString())}>
        {t("sleep.confirm")}
      </PrimaryButton>
    </div>
  );
}

function OpenSession({ session }: { session: SleepSession }) {
  const { t, i18n } = useTranslation();
  const now = useNow();
  const stop = useStopSleep();
  const elapsedMin = Math.max(0, Math.floor((now.getTime() - new Date(session.started_at).getTime()) / 60000));

  const err = stop.error instanceof ApiError ? stop.error : null;
  const needsWakeTime = elapsedMin > FORGOTTEN_STOP_MINUTES || err?.code === "wake_time_required";

  return (
    <Card>
      <p className="text-sm text-muted">{t("sleep.sleeping")}</p>
      <p className="mt-1 text-4xl font-semibold">{formatDuration(t, elapsedMin)}</p>
      <p className="mt-1 text-sm text-muted">{t("sleep.since", { time: formatTime(session.started_at, i18n.language) })}</p>
      {needsWakeTime ? (
        <WakeTimePicker
          busy={stop.isPending}
          invalid={err?.code === "invalid_time"}
          onConfirm={(iso) => stop.mutate(iso)}
        />
      ) : (
        <PrimaryButton disabled={stop.isPending} onClick={() => stop.mutate(undefined)}>
          {t("sleep.stop")}
        </PrimaryButton>
      )}
      {err && !["wake_time_required", "invalid_time"].includes(err.code) && (
        <p className="mt-2 text-sm text-danger">{t("common.error")}</p>
      )}
    </Card>
  );
}

function LastSleep({ session }: { session: SleepSession }) {
  const { t, i18n } = useTranslation();
  return (
    <div className="mt-4 border-t border-muted/20 pt-4">
      <p className="text-sm text-muted">{t(session.is_nap ? "sleep.nap" : "sleep.lastSleep")}</p>
      <p className="mt-1 text-3xl font-semibold">{formatDuration(t, session.duration_minutes ?? 0)}</p>
      <p className="mt-1 text-sm text-muted">
        {formatTime(session.started_at, i18n.language)} → {formatTime(session.ended_at!, i18n.language)}
      </p>
    </div>
  );
}

export function SleepCard() {
  const { t } = useTranslation();
  const current = useCurrentSleep();
  const list = useSleepList(5);
  const start = useStartSleep();

  if (current.isPending) return <Card>{t("common.loading")}</Card>;
  if (current.isError) return <Card>{t("common.error")}</Card>;
  if (current.data) return <OpenSession session={current.data} />;

  const last = list.data?.find((s) => s.ended_at !== null);
  return (
    <Card>
      {last ? <LastSleep session={last} /> : <p className="text-muted">{t("sleep.noData")}</p>}
      <PrimaryButton disabled={start.isPending} onClick={() => start.mutate()}>
        {t("sleep.start")}
      </PrimaryButton>
      {start.isError && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}
    </Card>
  );
}
