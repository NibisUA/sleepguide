import { Component, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

function Fallback() {
  const { t } = useTranslation();
  return <main role="alert" className="mx-auto max-w-md space-y-4 p-5">
    <p className="text-danger">{t("common.error")}</p>
    <button type="button" onClick={() => window.location.reload()} className="rounded-2xl border border-primary/50 px-5 py-3 text-primary">
      {t("common.retry")}
    </button>
  </main>;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <Fallback /> : this.props.children; }
}
