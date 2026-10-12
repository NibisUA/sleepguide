import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { ApiToken, ApiTokenCreated } from "../../types/api";

export const TOKENS_KEY = ["api-tokens"] as const;

export function useApiTokens() {
  return useQuery({
    queryKey: TOKENS_KEY,
    queryFn: () => api<ApiToken[]>("/me/api-tokens"),
  });
}

/** The response contains the secret exactly once: keep it in component state, never in the cache. */
export function useCreateApiToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (label: string) =>
      api<ApiTokenCreated>("/me/api-tokens", { method: "POST", body: JSON.stringify({ label }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: TOKENS_KEY }),
  });
}

export function useRevokeApiToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/me/api-tokens/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: TOKENS_KEY }),
  });
}
