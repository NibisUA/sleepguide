import { useEffect } from "react";
import { useTranslation } from "react-i18next";

const SECTIONS = ["data", "purpose", "sharing", "retention", "rights", "security", "contact", "basis"] as const;

export function PrivacyPage() {
  const { t, i18n } = useTranslation();
  const language = window.location.pathname.endsWith("/en") ? "en" : "uk";
  useEffect(() => { document.documentElement.lang = language; void i18n.changeLanguage(language); }, [language, i18n]);
  const owner = import.meta.env.VITE_PRIVACY_OWNER?.trim();
  const contact = import.meta.env.VITE_PRIVACY_CONTACT?.trim();
  const approved = import.meta.env.VITE_PRIVACY_APPROVED === "true" && owner && contact;
  return <main className="mx-auto max-w-md space-y-5 p-5">
    <h1 className="text-2xl font-semibold">{t("privacy.title")}</h1>
    <p className="text-sm text-muted">{t("privacy.updated")}</p>
    {!approved && <p role="note" className="rounded-2xl border border-warning/40 p-4 text-sm text-warning">{t("privacy.draft")}</p>}
    <nav aria-label={t("settings.language")} className="flex gap-4 text-primary">
      <a href="/privacy/uk" lang="uk">Українська</a><a href="/privacy/en" lang="en">English</a>
    </nav>
    {SECTIONS.map(key => <section key={key} className="rounded-2xl bg-surface p-4">
      <h2 className="font-semibold">{t(`privacy.policy.${key}.title`)}</h2>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-muted">{t(`privacy.policy.${key}.body`)}</p>
      {key === "contact" && <p className="mt-2 break-words text-sm">{owner || t("privacy.ownerMissing")}<br />{contact || t("privacy.contactMissing")}</p>}
    </section>)}
    <a href="/" className="inline-block py-3 text-primary">{t("privacy.back")}</a>
  </main>;
}
