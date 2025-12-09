import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import nb from "./nb.json";
import nn from "./nn.json";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    nb: { translation: nb },
    nn: { translation: nn },
  },
  lng: localStorage.getItem("language") || "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;

