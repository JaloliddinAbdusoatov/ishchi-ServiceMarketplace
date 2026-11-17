import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import axios from "axios";
import i18n from "@/i18n";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Relative media paths use the Vite proxy locally and the web server in production.
const MEDIA_BASE = (import.meta.env.VITE_MEDIA_BASE_URL as string | undefined) || "";

export function resolveMediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("blob:")) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${MEDIA_BASE.replace(/\/$/, "")}${normalized}`;
}

export function formatCurrencyUZS(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return String(value);
  return `${new Intl.NumberFormat("uz-UZ", { minimumFractionDigits: Number.isInteger(num) ? 0 : 2, maximumFractionDigits: 2 }).format(num)} UZS`;
}

export function formatDate(value: string | null | undefined, lang = "uz"): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const locale = lang === "ru" ? "ru-RU" : lang === "en" ? "en-US" : "uz-UZ";
  // Numeric Uzbek months also work in WebKit builds with incomplete Uzbek CLDR
  // data, which otherwise display placeholder names such as "M11".
  return d.toLocaleDateString(locale, { year: "numeric", month: locale === "uz-UZ" ? "2-digit" : "short", day: "numeric" });
}

export function formatDateTime(value: string | null | undefined, lang = "uz"): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const locale = lang === "ru" ? "ru-RU" : lang === "en" ? "en-US" : "uz-UZ";
  return d.toLocaleString(locale, {
    year: "numeric",
    month: locale === "uz-UZ" ? "2-digit" : "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getLocalizedCategoryName(
  item: { name: string; name_uz?: string; name_ru?: string; name_en?: string },
  lang: string
): string {
  if (lang === "ru" && item.name_ru) return item.name_ru;
  if (lang === "en" && item.name_en) return item.name_en;
  if (lang === "uz" && item.name_uz) return item.name_uz;
  return item.name;
}

export function extractApiErrorMessage(err: unknown, fallback?: string): string {
  const generic = fallback || i18n.t("common.errorOccurred");
  if (axios.isAxiosError(err)) {
    if (!err.response) return fallback || i18n.t("errors.networkUnavailable");
    const payload = err.response?.data as
      | {
          error?: {
            code?: string;
            message?: string;
            details?: Record<string, string | string[]> | string[] | null;
          };
          detail?: string;
        }
      | undefined;

    if (payload?.error) {
      const knownErrors: Record<string, string> = {
        invalid_credentials: "errors.invalidCredentials",
        service_unavailable: "errors.serviceUnavailable",
        permission_denied: "errors.permissionDenied",
        forbidden: "errors.permissionDenied",
        not_found: "errors.notFound",
        throttled: "errors.rateLimited",
      };
      const translation = payload.error.code && knownErrors[payload.error.code];
      if (translation) return i18n.t(translation);
      const details = payload.error.details;
      if (details && typeof details === "object" && !Array.isArray(details)) {
        const firstEntry = Object.entries(details).find(([k]) => k !== "remaining_cooldown");
        if (firstEntry) {
          const [field, val] = firstEntry;
          const msg = Array.isArray(val) ? val[0] : String(val);
          return field === "non_field_errors" ? msg : `${field}: ${msg}`;
        }
      }
      if (Array.isArray(details) && details.length > 0) {
        return String(details[0]);
      }
      if (payload.error.message) return payload.error.message;
    }
    if (payload?.detail) return payload.detail;
    return generic;
  }
  if (err instanceof Error && err.message) return err.message;
  return generic;
}

export function getInitials(name: string | null | undefined): string {
  if (!name) return "U";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "U";
}
