import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { confirmAction } from "../../lib/confirm";
import type { ApiToken, ApiTokenCreated } from "../../types/api";
import { useApiTokens, useCreateApiToken, useRevokeApiToken } from "./api";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false; // clipboard is not available in every WebView: the token stays selectable
  }
}

function NewTokenBox({ created, onDone }: { created: ApiTokenCreated; onDone: () => void }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  return (
    <div className="mt-4 rounded-2xl border border-warning/50 p-4">
      <p className="font-medium">{t("integrations.createdTitle")}</p>
      <p className="mt-1 text-sm text-warning">{t("integrations.createdWarning")}</p>
      <p className="mt-3 select-all break-all rounded-xl bg-bg p-3 font-mono text-sm">{created.token}</p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => void copyText(created.token).then(setCopied)}
          className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary"
        >
          {copied ? t("integrations.copied") : t("integrations.copy")}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="flex-1 rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("integrations.done")}
        </button>
      </div>
    </div>
  );
}

function TokenRow({ token, onRevoke, busy }: { token: ApiToken; onRevoke: () => void; busy: boolean }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const created = new Date(token.created_at).toLocaleDateString(locale, { day: "numeric", month: "short" });
  const lastUsed = token.last_used_at
    ? new Date(token.last_used_at).toLocaleString(locale, {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;
  return (
    <li className="flex items-center justify-between gap-2 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{token.label}</p>
        <p className="text-xs text-muted">
          <span className="font-mono">{token.prefix}…</span> · {t("integrations.createdOn", { date: created })}
        </p>
        <p className="text-xs text-muted">
          {lastUsed
            ? t("integrations.lastUsed", { when: lastUsed })
            : t("integrations.neverUsed")}
        </p>
      </div>
      <button
        type="button"
        disabled={busy}
        onClick={onRevoke}
        className="shrink-0 text-sm text-danger disabled:opacity-60"
      >
        {t("integrations.revoke")}
      </button>
    </li>
  );
}

export function IntegrationsSection() {
  const { t } = useTranslation();
  const tokens = useApiTokens();
  const create = useCreateApiToken();
  const revoke = useRevokeApiToken();
  const [label, setLabel] = useState("iPhone");
  const [created, setCreated] = useState<ApiTokenCreated | null>(null);

  const base = `${window.location.origin}/api/v1`;
  const tooMany = create.error instanceof ApiError && create.error.code === "too_many_tokens";

  async function revokeToken(token: ApiToken) {
    if (await confirmAction(t("integrations.revokeConfirm", { label: token.label }))) {
      revoke.mutate(token.id);
    }
  }

  return (
    <section className="rounded-3xl bg-surface p-5">
      <h2 className="font-medium">{t("integrations.title")}</h2>
      <p className="mt-1 text-sm text-muted">{t("integrations.hint")}</p>

      {created && <NewTokenBox created={created} onDone={() => setCreated(null)} />}

      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={label}
          maxLength={40}
          placeholder={t("integrations.labelPlaceholder")}
          aria-label={t("integrations.labelPlaceholder")}
          onChange={(event) => setLabel(event.target.value)}
          className="min-w-0 flex-1 rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
        <button
          type="button"
          disabled={create.isPending || label.trim() === ""}
          onClick={() => create.mutate(label.trim(), { onSuccess: (token) => setCreated(token) })}
          className="shrink-0 rounded-xl bg-primary px-4 font-semibold text-on-primary disabled:opacity-60"
        >
          {t("integrations.create")}
        </button>
      </div>
      {create.isError && (
        <p className="mt-2 text-sm text-danger">
          {tooMany ? t("integrations.tooMany") : t("common.error")}
        </p>
      )}

      {tokens.isPending ? (
        <Skeleton />
      ) : tokens.isError ? (
        <QueryError error={tokens.error} retry={() => void tokens.refetch()} />
      ) : tokens.data.length === 0 ? (
        <p className="mt-4 text-sm text-muted">{t("integrations.noTokens")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-muted/10">
          {tokens.data.map((token) => (
            <TokenRow
              key={token.id}
              token={token}
              busy={revoke.isPending}
              onRevoke={() => void revokeToken(token)}
            />
          ))}
        </ul>
      )}
      {revoke.isError && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}

      <p className="mt-4 text-sm font-medium">{t("integrations.usageTitle")}</p>
      <pre className="mt-2 overflow-x-auto rounded-xl bg-bg p-3 text-xs leading-relaxed text-muted">
        {`POST ${base}/sleep/start\nPOST ${base}/sleep/stop\nPUT  ${base}/screen-time/YYYY-MM-DD\nAuthorization: Bearer <token>`}
      </pre>
      <p className="mt-2 text-xs text-muted">{t("integrations.usageHint")}</p>
    </section>
  );
}
