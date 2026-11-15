import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { FileText, FolderKanban, Mail, PlusCircle, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { OrderCard } from "@/components/shared/OrderCard";
import { dashboardApi } from "@/services/api";

export function EmployerOverviewPage() {
  const { t } = useTranslation();

  const statsQuery = useQuery({
    queryKey: ["dashboard", "employer"],
    queryFn: dashboardApi.employer,
  });

  if (statsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (statsQuery.isError || !statsQuery.data) {
    return <ErrorState onRetry={() => void statsQuery.refetch()} />;
  }

  const stats = statsQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t("employer.dashboardTitle")}</h1>
        <Link to="/employer/orders/new">
          <Button className="gap-2">
            <PlusCircle className="h-4 w-4" />
            {t("nav.createOrder")}
          </Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: t("employer.totalOrdersStat"),
            value: stats.total_orders,
            icon: FolderKanban,
            color: "text-primary",
          },
          {
            label: t("employer.pendingAppsStat"),
            value: stats.pending_applications_received,
            icon: FileText,
            color: "text-amber-600",
          },
          {
            label: t("employer.pendingInvsStat"),
            value: stats.pending_invitations_sent,
            icon: Mail,
            color: "text-indigo-600",
          },
          {
            label: t("employer.employerRatingStat"),
            value: `${Number(stats.rating_avg || 0).toFixed(1)} (${stats.review_count})`,
            icon: Star,
            color: "text-emerald-600",
          },
        ].map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label} className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{card.label}</p>
                <p className="mt-1 text-2xl font-bold">{card.value}</p>
              </div>
              <div className={`rounded-xl bg-muted p-3 ${card.color}`}>
                <Icon className="h-5 w-5" />
              </div>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t("nav.myOrders")}</CardTitle>
          <Link to="/employer/orders" className="text-sm font-medium text-primary hover:underline">
            {t("common.viewAll")} →
          </Link>
        </CardHeader>
        <CardContent>
          {stats.recent_orders.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {stats.recent_orders.map((order) => (
                <OrderCard key={order.id} order={order} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
