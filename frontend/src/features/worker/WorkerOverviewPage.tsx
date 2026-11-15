import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Bell,
  Briefcase,
  CheckCircle2,
  FileText,
  Mail,
  Search,
  ShieldCheck,
  Star,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ErrorState } from "@/components/shared/ErrorState";
import { dashboardApi } from "@/services/api";

export function WorkerOverviewPage() {
  const { t } = useTranslation();

  const statsQuery = useQuery({
    queryKey: ["dashboard", "worker"],
    queryFn: dashboardApi.worker,
  });

  if (statsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
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
        <div>
          <h1 className="text-2xl font-bold">{t("worker.dashboardTitle")}</h1>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={stats.verification_status} showIcon />
          </div>
        </div>

        <Link to="/marketplace?tab=orders">
          <Button className="gap-2">
            <Search className="h-4 w-4" />
            {t("nav.browseOrders")}
          </Button>
        </Link>
      </div>

      {!stats.is_verified && (
        <Card className="border-blue-200 bg-blue-50/50 p-4 dark:border-blue-900/50 dark:bg-blue-950/20">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <ShieldCheck className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <p className="text-sm text-blue-950 dark:text-blue-200">
                {stats.verification_status === "PENDING"
                  ? t("worker.verificationBannerPending")
                  : stats.verification_status === "REJECTED"
                    ? t("worker.verificationBannerRejected")
                    : t("worker.verificationBannerUnverified")}
              </p>
            </div>
            <Link to="/worker/profile" className="shrink-0">
              <Button size="sm" variant="outline" className="bg-card">
                {t("nav.profile")}
              </Button>
            </Link>
          </div>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: t("landing.statsCompleted"),
            value: stats.completed_orders_count,
            icon: CheckCircle2,
            color: "text-emerald-600",
          },
          {
            label: t("admin.activeOrders"),
            value: stats.active_assigned_orders_count,
            icon: Briefcase,
            color: "text-primary",
          },
          {
            label: t("nav.invitations"),
            value: stats.pending_invitations_count,
            icon: Mail,
            color: "text-indigo-600",
          },
          {
            label: t("reviews.title"),
            value: `${Number(stats.rating_avg || 0).toFixed(1)} (${stats.review_count})`,
            icon: Star,
            color: "text-amber-500",
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label} className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="mt-1 text-2xl font-bold">{item.value}</p>
              </div>
              <div className={`rounded-xl bg-muted p-3 ${item.color}`}>
                <Icon className="h-5 w-5" />
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" />
              {t("nav.applications")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {["PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"].map((st) => (
              <div key={st} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                <StatusBadge status={st} />
                <span className="font-semibold">{stats.applications_summary[st] || 0}</span>
              </div>
            ))}
            <div className="pt-2">
              <Link to="/worker/applications">
                <Button variant="outline" size="sm" className="w-full">
                  {t("common.viewAll")}
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bell className="h-4 w-4 text-primary" />
              {t("notifications.title")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {t("notifications.unreadCount", { count: stats.unread_notifications })}
            </p>
            <div className="flex flex-wrap gap-2">
              <Link to="/notifications">
                <Button variant="outline" size="sm">
                  {t("notifications.title")}
                </Button>
              </Link>
              <Link to="/worker/invitations">
                <Button variant="outline" size="sm">
                  {t("nav.invitations")}
                </Button>
              </Link>
              <Link to="/worker/categories">
                <Button variant="outline" size="sm">
                  {t("nav.categories")}
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
