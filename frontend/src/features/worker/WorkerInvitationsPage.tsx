import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { invitationsApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDateTime } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function WorkerInvitationsPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const invQuery = useQuery({
    queryKey: ["invitations", "worker"],
    queryFn: () => invitationsApi.list({ page_size: 50 }),
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => invitationsApi.accept(id),
    onSuccess: () => {
      toast.success(t("worker.acceptInvBtn"));
      void queryClient.invalidateQueries({ queryKey: ["invitations"] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => invitationsApi.reject(id),
    onSuccess: () => {
      toast.success(t("worker.rejectInvBtn"));
      void queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (invQuery.isLoading) return <Skeleton className="h-64" />;
  if (invQuery.isError) return <ErrorState onRetry={() => void invQuery.refetch()} />;

  const items = (invQuery.data?.results || []).filter(
    (inv) => !user?.worker_profile_id || inv.worker === user.worker_profile_id
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.invitations")}</h1>
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
                <p className="text-xs text-muted-foreground">{inv.employer_name}</p>
                {inv.proposed_budget && (
                  <p className="text-sm font-semibold text-primary">
                    {formatCurrencyUZS(inv.proposed_budget)}
                  </p>
                )}
                {inv.message && <p className="text-xs text-muted-foreground">{inv.message}</p>}
                <p className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {formatDateTime(inv.expires_at, i18n.language)}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Link to={`/orders/${inv.order}`}>
                  <Button variant="outline" size="sm">
                    {t("common.details")}
                  </Button>
                </Link>
                {inv.status === "PENDING" && (
                  <>
                    <Button
                      size="sm"
                      variant="success"
                      disabled={acceptMutation.isPending}
                      onClick={() => acceptMutation.mutate(inv.id)}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {t("worker.acceptInvBtn")}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={rejectMutation.isPending}
                      onClick={() => rejectMutation.mutate(inv.id)}
                    >
                      <XCircle className="h-4 w-4" />
                      {t("worker.rejectInvBtn")}
                    </Button>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
