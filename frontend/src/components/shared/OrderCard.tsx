import { Link } from "react-router-dom";
import { Briefcase, Calendar, Heart, MapPin, Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatCurrencyUZS, formatDate } from "@/lib/utils";
import type { ServiceOrder } from "@/types/api";

interface OrderCardProps {
  order: ServiceOrder;
  isFavorite?: boolean;
  onToggleFavorite?: (orderId: string) => void;
}

export function OrderCard({ order, isFavorite = false, onToggleFavorite }: OrderCardProps) {
  const { t, i18n } = useTranslation();

  return (
    <Card className="group flex flex-col justify-between p-5 transition-all hover:border-primary/40 hover:shadow-md">
      <div>
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="default">{order.category_name}</Badge>
            <StatusBadge status={order.status} />
          </div>
          {onToggleFavorite && (
            <button
              type="button"
              onClick={() => onToggleFavorite(order.id)}
              aria-label={
                isFavorite ? t("marketplace.removeFavorite") : t("marketplace.addFavorite")
              }
              className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-red-500 transition-colors"
            >
              <Heart className={`h-4 w-4 ${isFavorite ? "fill-red-500 text-red-500" : ""}`} />
            </button>
          )}
        </div>

        <Link
          to={`/orders/${order.id}`}
          className="line-clamp-2 text-base font-semibold text-foreground group-hover:text-primary transition-colors"
        >
          {order.title}
        </Link>

        <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{order.description}</p>

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-primary/70" />
            {order.location}
            {order.district ? `, ${order.district}` : ""}
          </span>
          <span className="inline-flex items-center gap-1">
            <Briefcase className="h-3.5 w-3.5 text-primary/70" />
            {t(`statuses.${order.work_type}`, order.work_type)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Users className="h-3.5 w-3.5 text-primary/70" />
            {t("marketplace.applicationsCount", { count: order.applications_count })}
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t pt-3">
        <div>
          <p className="text-xs text-muted-foreground">{order.employer_name}</p>
          <p className="text-sm font-bold text-foreground">
            {formatCurrencyUZS(order.budget)}{" "}
            <span className="text-xs font-normal text-muted-foreground">
              ({t(`statuses.${order.budget_type}`, order.budget_type)})
            </span>
          </p>
        </div>
        <div className="text-right">
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <Calendar className="h-3 w-3" />
            {formatDate(order.published_at || order.created_at, i18n.language)}
          </span>
          <div>
            <Link
              to={`/orders/${order.id}`}
              className="text-xs font-medium text-primary hover:underline"
            >
              {t("common.details")} →
            </Link>
          </div>
        </div>
      </div>
    </Card>
  );
}
