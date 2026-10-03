// Interim hand-written types. Replace with generated ones: `npm run gen:api`
// (writes src/types/api.gen.ts from the backend OpenAPI schema).

export interface User {
  id: number;
  language: string;
  timezone: string;
  sleep_goal_minutes: number;
  target_bedtime: string | null; // HH:MM:SS, null = default (23:00)
  reminder_evening_time: string | null; // HH:MM:SS, null = evening reminder off
  reminder_morning_on: boolean;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SleepSession {
  id: number;
  started_at: string;
  ended_at: string | null;
  local_date: string | null;
  duration_minutes: number | null;
  is_nap: boolean;
  source: string;
}

/** One line of the Sleep Score breakdown (duration / consistency / debt / bedtime). */
export interface SleepScoreComponent {
  key: string;
  earned: number;
  max: number;
  detail: Record<string, string | number | boolean | null>;
}

export interface SleepScore {
  date: string;
  score: number;
  limited_data: boolean;
  sleep_minutes: number;
  components: SleepScoreComponent[];
  algorithm_version: string;
}

/** Aggregated day used by the history charts and the yearly heatmap. */
export interface SleepDay {
  date: string;
  sleep_minutes: number;
  nap_minutes: number;
  bedtime: string | null;
  wake_time: string | null;
  score: number | null;
  score_limited_data: boolean;
}
