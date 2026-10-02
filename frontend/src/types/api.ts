// Interim hand-written types. Replace with generated ones: `npm run gen:api`
// (writes src/types/api.gen.ts from the backend OpenAPI schema).

export interface User {
  id: number;
  language: string;
  timezone: string;
  sleep_goal_minutes: number;
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
