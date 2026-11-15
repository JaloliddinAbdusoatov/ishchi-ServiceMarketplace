import { Link } from "react-router-dom";
import { Heart, MapPin, ShieldCheck, Star } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { UserAvatar } from "@/components/ui/avatar";
import { formatCurrencyUZS, getLocalizedCategoryName } from "@/lib/utils";
import type { WorkerProfile } from "@/types/api";

interface WorkerCardProps {
  worker: WorkerProfile;
  isFavorite?: boolean;
  onToggleFavorite?: (workerId: string) => void;
  actionSlot?: React.ReactNode;
}

export function WorkerCard({
  worker,
  isFavorite = false,
  onToggleFavorite,
  actionSlot,
}: WorkerCardProps) {
  const { t, i18n } = useTranslation();

  const priceDisplay =
    worker.pricing_type === "HOURLY" && worker.hourly_rate
      ? `${formatCurrencyUZS(worker.hourly_rate)} ${t("common.perHour")}`
      : worker.fixed_rate_from
        ? `${t("common.fromPrice")} ${formatCurrencyUZS(worker.fixed_rate_from)}`
        : t(`statuses.${worker.pricing_type}`, worker.pricing_type);

  return (
    <Card className="group flex flex-col justify-between p-5 transition-all hover:border-primary/40 hover:shadow-md">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <UserAvatar src={worker.photo} name={worker.full_name} className="h-12 w-12" />
            <div>
              <Link
                to={`/workers/${worker.id}`}
                className="inline-flex items-center gap-1.5 text-base font-semibold hover:text-primary transition-colors"
              >
                <span>{worker.full_name}</span>
                {worker.is_verified && (
                  <ShieldCheck
                    className="h-4 w-4 text-emerald-600 shrink-0"
                    aria-label={t("statuses.VERIFIED")}
                  />
                )}
              </Link>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400">
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                  {Number(worker.rating_avg || 0).toFixed(1)}
                </span>
                <span>({t("marketplace.reviewsCount", { count: worker.review_count })})</span>
                <span>•</span>
                <span>{t("marketplace.yearsExp", { years: worker.experience_years })}</span>
              </div>
            </div>
          </div>

          {onToggleFavorite && (
            <button
              type="button"
              onClick={() => onToggleFavorite(worker.id)}
              aria-label={
                isFavorite ? t("marketplace.removeFavorite") : t("marketplace.addFavorite")
              }
              className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-red-500 transition-colors"
            >
              <Heart className={`h-4 w-4 ${isFavorite ? "fill-red-500 text-red-500" : ""}`} />
            </button>
          )}
        </div>

        <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">{worker.bio || "—"}</p>

        {worker.categories?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {worker.categories.slice(0, 3).map((cat) => (
              <Badge key={cat.id} variant={cat.is_primary ? "default" : "secondary"}>
                {getLocalizedCategoryName(cat, i18n.language)}
              </Badge>
            ))}
          </div>
        )}

        {worker.skills?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {worker.skills.slice(0, 4).map((skill) => (
              <span
                key={skill}
                className="rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
              >
                {skill}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between gap-2 border-t pt-3">
        <div>
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 text-primary/70" />
            {worker.location || "—"}
          </span>
          <p className="text-sm font-bold text-foreground">{priceDisplay}</p>
        </div>
        <div className="flex items-center gap-2">
          {actionSlot}
          <Link
            to={`/workers/${worker.id}`}
            className="text-xs font-medium text-primary hover:underline"
          >
            {t("common.details")} →
          </Link>
        </div>
      </div>
    </Card>
  );
}
