import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Briefcase,
  CheckCircle2,
  Flag,
  Layers,
  ShieldCheck,
  Star,
  UserCheck,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { adminApi } from "@/services/api";

const PIE_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#6366f1", "#ef4444"];

export function AdminOverviewPage() {
  const { t } = useTranslation();

  const statsQuery = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => adminApi.stats(),
  });

  if (statsQuery.isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (statsQuery.isError || !statsQuery.data) {
    return <ErrorState onRetry={() => void statsQuery.refetch()} />;
  }

  const stats = statsQuery.data;
  const activeOrders =
    (stats.orders.by_status["PUBLISHED"] || 0) + (stats.orders.by_status["IN_PROGRESS"] || 0);
  const completedOrders = stats.orders.by_status["COMPLETED"] || 0;
  const pendingReports =
    (stats.reports.by_status["OPEN"] || 0) + (stats.reports.by_status["UNDER_REVIEW"] || 0);

  const ordersChartData = Object.entries(stats.orders.by_status).map(([status, count]) => ({
    status: t(`statuses.${status}`, status),
    count,
  }));

  const usersChartData = Object.entries(stats.users.by_role).map(([role, count]) => ({
    name: role,
    value: count,
  }));

  const cards = [
    { label: t("admin.totalUsers"), value: stats.users.total, icon: Users, color: "text-blue-600" },
    { label: t("admin.totalWorkers"), value: stats.workers.total, icon: UserCheck, color: "text-indigo-600" },
    {
      label: t("admin.verifiedWorkers"),
      value: stats.workers.verified,
      icon: ShieldCheck,
      color: "text-emerald-600",
    },
    {
      label: t("admin.totalEmployers"),
      value: stats.employers.total,
      icon: Layers,
      color: "text-violet-600",
    },
    { label: t("admin.totalOrders"), value: stats.orders.total, icon: Briefcase, color: "text-sky-600" },
    { label: t("nav.applications"), value: stats.applications_total, icon: UserCheck, color: "text-blue-600" },
    { label: t("reviews.title"), value: stats.reviews_total, icon: Star, color: "text-amber-600" },
    { label: t("admin.activeOrders"), value: activeOrders, icon: Briefcase, color: "text-amber-600" },
    {
      label: t("admin.completedOrders"),
      value: completedOrders,
      icon: CheckCircle2,
      color: "text-emerald-600",
    },
    { label: t("admin.pendingReports"), value: pendingReports, icon: Flag, color: "text-rose-600" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("admin.dashboardTitle")}</h1>
        <div className="flex flex-wrap gap-2">
          {stats.workers.pending_verification > 0 && (
            <Link to="/admin/verification">
              <Button size="sm">
                {t("nav.adminVerification")} ({stats.workers.pending_verification})
              </Button>
            </Link>
          )}
          {pendingReports > 0 && (
            <Link to="/admin/reports">
              <Button size="sm" variant="destructive">
                {t("nav.adminReports")} ({pendingReports})
              </Button>
            </Link>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label} className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
                <Icon className={`h-4 w-4 ${card.color}`} />
              </div>
              <p className="mt-2 text-2xl font-bold">{card.value}</p>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("admin.ordersChartTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ordersChartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("admin.usersChartTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={usersChartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label
                >
                  {usersChartData.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
