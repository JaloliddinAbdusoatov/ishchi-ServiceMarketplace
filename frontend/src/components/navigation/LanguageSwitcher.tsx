import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";
import { useUIStore, type SupportedLang } from "@/stores/uiStore";

const LANGS: Array<{ code: SupportedLang; label: string }> = [
  { code: "uz", label: "O'zbek" },
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
];

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const { language, setLanguage } = useUIStore();

  const handleChange = (next: SupportedLang) => {
    setLanguage(next);
    void i18n.changeLanguage(next);
  };

  return (
    <div className="inline-flex items-center gap-1 rounded-lg border bg-card px-2 py-1 text-xs">
      <Globe className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <label htmlFor="lang-select" className="sr-only">
        {t("common.language")}
      </label>
      <select
        id="lang-select"
        aria-label={t("common.language")}
        value={language}
        onChange={(e) => handleChange(e.target.value as SupportedLang)}
        className="bg-transparent font-medium text-foreground focus:outline-none cursor-pointer"
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code} className="bg-card text-foreground">
            {l.label}
          </option>
        ))}
      </select>
    </div>
  );
}
