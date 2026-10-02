import type { TokenOut } from "../types/api";
import { getInitData } from "./telegram";

const BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

let token: string | null = null;
let loginPromise: Promise<void> | null = null;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(code);
  }
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
  const initData = getInitData();
  const path = initData ? "/auth/telegram" : import.meta.env.DEV ? "/auth/dev" : null;
  if (!path) throw new ApiError(401, "not_in_telegram");

  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: initData ? JSON.stringify({ init_data: initData }) : undefined,
  });
  if (!res.ok) throw await parseError(res);
  token = ((await res.json()) as TokenOut).access_token;
}

function ensureLogin(): Promise<void> {
  loginPromise ??= login().finally(() => {
    loginPromise = null;
  });
  return loginPromise;
}

function send(path: string, init?: RequestInit): Promise<Response> {
  return fetch(BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (!token) await ensureLogin();
  let res = await send(path, init);
  if (res.status === 401) {
    token = null;
    await ensureLogin();
    res = await send(path, init);
  }
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as T;
}
