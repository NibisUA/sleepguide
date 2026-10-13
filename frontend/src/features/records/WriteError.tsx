import { useTranslation } from "react-i18next";
import { ApiError } from "../../lib/api";

export function WriteError({ error }: { error: unknown }) {
  const { t, i18n } = useTranslation();
  if (!error) return null;
  const key = error instanceof ApiError ? `errors.${error.code}` : "common.error";
  return <p role="alert" className="mt-3 text-sm text-danger">{i18n.exists(key) ? t(key) : t("common.error")}</p>;
}

