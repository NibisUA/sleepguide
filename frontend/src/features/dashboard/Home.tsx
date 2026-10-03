import { useTranslation } from "react-i18next";

import { SleepCard } from "../sleep/SleepCard";
import { SleepScoreCard } from "../sleep/SleepScoreCard";

export function Home() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-semibold">{t("home.title")}</h1>
      <SleepScoreCard />
      <SleepCard />
    </main>
  );
}
