import type { TokenOut } from "../types/api";
import { getInitData } from "./telegram";

const BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

let token: string | null = null;
let loginPromise: Promise<void> | null = null;
let sessionClosed = false;
let epoch = 0;
try { sessionClosed = sessionStorage.getItem("sleepguide.deleted") === "1"; } catch { /* WebView storage may be disabled */ }

export const isSessionClosed = () => sessionClosed;
export function resumeSession() {
  sessionClosed = false; token = null; loginPromise = null; epoch++;
  try { sessionStorage.removeItem("sleepguide.deleted"); } catch { /* memory guard still works */ }
}
function closeSession() {
  sessionClosed = true; token = null; loginPromise = null; epoch++;
  try { sessionStorage.setItem("sleepguide.deleted", "1"); } catch { /* memory guard still works */ }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(code);
  }
}

async function fetchResponse(url: string, init?: RequestInit): Promise<Response> {
  try { return await fetch(url, init); }
  catch { throw new ApiError(0, "network_error"); }
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "unknown_error";
  try {
    const body = await res.json();
    code = body?.detail?.code ?? code;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code);
}

async function login(): Promise<void> {
  if (sessionClosed) throw new ApiError(401, "account_deleted");
  const loginEpoch = epoch;
  const initData = getInitData();
  const path = initData ? "/auth/telegram" : import.meta.env.DEV ? "/auth/dev" : null;
  if (!path) throw new ApiError(401, "not_in_telegram");

  const res = await fetchResponse(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: initData ? JSON.stringify({ init_data: initData }) : undefined,
  });
  if (!res.ok) throw await parseError(res);
  const result = (await res.json()) as TokenOut;
  if (sessionClosed || loginEpoch !== epoch) throw new ApiError(401, "account_deleted");
  token = result.access_token;
}

function ensureLogin(): Promise<void> {
  loginPromise ??= login().finally(() => {
    loginPromise = null;
  });
  return loginPromise;
}

function send(path: string, init?: RequestInit): Promise<Response> {
  return fetchResponse(BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (sessionClosed) throw new ApiError(401, "account_deleted");
  const requestEpoch = epoch;
  if (!token) await ensureLogin();
  let res = await send(path, init);
  if (sessionClosed || requestEpoch !== epoch) throw new ApiError(401, "account_deleted");
  if (res.status === 401) {
    token = null;
    await ensureLogin();
    res = await send(path, init);
    if (sessionClosed || requestEpoch !== epoch) throw new ApiError(401, "account_deleted");
  }
  if (!res.ok) throw await parseError(res);
  // Close BEFORE resolving the mutation, so cache refreshes and stale requests
  // cannot auto-login and recreate the account that was just erased.
  if (path === "/me" && init?.method === "DELETE") closeSession();
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
