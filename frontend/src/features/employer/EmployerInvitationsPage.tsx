import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invitationsApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDateTime } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function EmployerInvitationsPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const invQuery = useQuery({
    queryKey: ["invitations", "employer"],
    queryFn: () => invitationsApi.list({ page_size: 50 }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => invitationsApi.cancel(id),
    onSuccess: () => {
      toast.success(t("employer.cancelInvBtn"));
      void queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (invQuery.isLoading) return <Skeleton className="h-64" />;
  if (invQuery.isError) return <ErrorState onRetry={() => void invQuery.refetch()} />;

  const items = (invQuery.data?.results || []).filter(
    (inv) => !user?.employer_profile_id || inv.employer === user.employer_profile_id
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("nav.invitations")}</h1>
        <Link to="/employer/find-workers">
          <Button size="sm">{t("nav.findWorkers")}</Button>
        </Link>
      </div>

      {items.length === 0 ? (
        <EmptyState title={t("common.noData")} />
      ) : (
        <div className="space-y-3">
          {items.map((inv) => (
            <Card key={inv.id} className="p-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/orders/${inv.order}`}
                    className="font-semibold text-base hover:text-primary hover:underline"
                  >
                    {inv.order_title}
                  </Link>
                  <StatusBadge status={inv.status} showIcon />
                </div>
                <Link to={`/workers/${inv.worker}`} className="text-sm font-medium text-primary hover:underline">
                  {inv.worker_name}
                </Link>
                {inv.proposed_budget && (
                  <p className="text-xs font-semibold">{formatCurrencyUZS(inv.proposed_budget)}</p>
                )}
                {inv.message && <p className="text-xs text-muted-foreground">{inv.message}</p>}
                <p className="text-[11px] text-muted-foreground">
                  {formatDateTime(inv.expires_at, i18n.language)}
                </p>
              </div>

              <div className="flex gap-2">
                {inv.status === "PENDING" && (
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(inv.id)}
                  >
                    <XCircle className="h-4 w-4" />
                    {t("employer.cancelInvBtn")}
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
