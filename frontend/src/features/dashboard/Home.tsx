import { useTranslation } from "react-i18next";

import { SleepCard } from "../sleep/SleepCard";

// Phase 2 vertical slice: only the sleep card. The Sleep Score hero,
// today's tiles and the latest insight arrive in later phases.
export function Home() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-semibold">{t("home.title")}</h1>
      <SleepCard />
    </main>
  );
}
