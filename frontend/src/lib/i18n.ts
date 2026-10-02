import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "../locales/en.json";
import uk from "../locales/uk.json";
import { getTelegramLanguage } from "./telegram";

const lng = (getTelegramLanguage() ?? navigator.language).toLowerCase().startsWith("uk")
  ? "uk"
  : "en";

void i18n.use(initReactI18next).init({
  resources: { uk: { translation: uk }, en: { translation: en } },
  lng,
  fallbackLng: "uk",
  interpolation: { escapeValue: false },
});

export default i18n;
