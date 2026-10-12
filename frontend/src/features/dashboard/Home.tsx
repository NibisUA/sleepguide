import { useTranslation } from "react-i18next";

import { TodayTiles } from "../day/TodayTiles";
import { LatestInsight } from "../insights/LatestInsight";
import { SleepCard } from "../sleep/SleepCard";
import { SleepScoreCard } from "../sleep/SleepScoreCard";
import { ScreenTimeCard } from "../screentime/ScreenTimeCard";
import { StressCard } from "../stress/StressCard";
import { WorkoutCard } from "../workout/WorkoutCard";
import { StreakCard } from "../progress/StreakCard";

// The wrappers carry the ids the "+" quick-add sheet scrolls to (see lib/focusCard.ts).
export function Home() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-semibold">{t("home.title")}</h1>
      <SleepScoreCard />
      <TodayTiles />
      <StreakCard />
      <LatestInsight />
      <div id="card-sleep" className="scroll-mt-4 transition">
        <SleepCard />
      </div>
      <div id="card-workout" className="scroll-mt-4 transition">
        <WorkoutCard />
      </div>
      <div id="card-stress" className="scroll-mt-4 transition">
        <StressCard />
      </div>
      <div id="card-screen" className="scroll-mt-4 transition">
        <ScreenTimeCard />
      </div>
    </main>
  );
}
