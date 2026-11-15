import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import uz from "@/i18n/locales/uz";
import ru from "@/i18n/locales/ru";
import en from "@/i18n/locales/en";
import { useUIStore } from "@/stores/uiStore";

const initialLang = useUIStore.getState().language || "uz";

i18n.use(initReactI18next).init({
  resources: {
    uz: { translation: uz },
    ru: { translation: ru },
    en: { translation: en },
  },
  lng: initialLang,
  fallbackLng: "uz",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
