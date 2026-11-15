import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { applicationsApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function WorkerApplicationsPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const appsQuery = useQuery({
    queryKey: ["applications", "mine"],
    queryFn: () => applicationsApi.list({ page_size: 50 }),
  });

  const withdrawMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.withdraw(id),
    onSuccess: () => {
      toast.success(t("worker.withdrawBtn"));
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (appsQuery.isLoading) return <Skeleton className="h-64" />;
  if (appsQuery.isError) return <ErrorState onRetry={() => void appsQuery.refetch()} />;

  const items = (appsQuery.data?.results || []).filter(
    (a) => !user?.worker_profile_id || a.worker === user.worker_profile_id
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.applications")}</h1>
      {items.length === 0 ? (
        <EmptyState
          title={t("common.noData")}
          action={
            <Link to="/marketplace?tab=orders">
              <Button>{t("nav.browseOrders")}</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {items.map((app) => (
            <Card key={app.id} className="p-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/orders/${app.order}`}
                    className="font-semibold text-base hover:text-primary hover:underline"
                  >
                    {app.order_title}
                  </Link>
                  <StatusBadge status={app.status} showIcon />
                </div>
                <p className="text-sm font-medium text-primary">
                  {formatCurrencyUZS(app.proposed_price)}
                </p>
                <p className="text-xs text-muted-foreground">{app.cover_message}</p>
                <p className="text-[11px] text-muted-foreground">
                  {formatDate(app.created_at, i18n.language)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link to={`/orders/${app.order}`}>
                  <Button variant="outline" size="sm">
                    {t("common.details")}
                  </Button>
                </Link>
                {app.status === "PENDING" && (
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={withdrawMutation.isPending}
                    onClick={() => withdrawMutation.mutate(app.id)}
                  >
                    {t("worker.withdrawBtn")}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
