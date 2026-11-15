import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import axios from "axios";

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
  return `${new Intl.NumberFormat("uz-UZ", { maximumFractionDigits: 0 }).format(num)} UZS`;
}

export function formatDate(value: string | null | undefined, lang = "uz"): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const locale = lang === "ru" ? "ru-RU" : lang === "en" ? "en-US" : "uz-UZ";
  return d.toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value: string | null | undefined, lang = "uz"): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const locale = lang === "ru" ? "ru-RU" : lang === "en" ? "en-US" : "uz-UZ";
  return d.toLocaleString(locale, {
    year: "numeric",
    month: "short",
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

export function extractApiErrorMessage(err: unknown, fallback = "So'rovni bajarishda xatolik yuz berdi."): string {
  if (axios.isAxiosError(err)) {
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
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function getInitials(name: string | null | undefined): string {
  if (!name) return "U";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "U";
}
