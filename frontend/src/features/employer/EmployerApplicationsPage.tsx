import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { CheckCircle2, MessageSquare, ShieldCheck, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { applicationsApi, chatApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function EmployerApplicationsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const appsQuery = useQuery({
    queryKey: ["applications", "employer"],
    queryFn: () => applicationsApi.list({ page_size: 50 }),
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.accept(id),
    onSuccess: () => {
      toast.success(t("employer.acceptApplicantBtn"));
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => applicationsApi.reject(id, ""),
    onSuccess: () => {
      toast.success(t("employer.rejectApplicantBtn"));
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const openChatMutation = useMutation({
    mutationFn: ({ orderId, workerId }: { orderId: string; workerId: string }) =>
      chatApi.openConversation({ order: orderId, worker: workerId }),
    onSuccess: (conv) => navigate(`/dashboard/messages?conversation=${conv.id}`),
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (appsQuery.isLoading) return <Skeleton className="h-64" />;
  if (appsQuery.isError) return <ErrorState onRetry={() => void appsQuery.refetch()} />;

  // Filter out own worker apps if dual-role
  const items = (appsQuery.data?.results || []).filter(
    (a) => !user?.worker_profile_id || a.worker !== user.worker_profile_id
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.applications")}</h1>
      {items.length === 0 ? (
        <EmptyState title={t("common.noData")} />
      ) : (
        <div className="space-y-3">
          {items.map((app) => (
            <Card key={app.id} className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
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
                <div className="flex items-center gap-2 text-sm">
                  <Link to={`/workers/${app.worker}`} className="font-medium text-primary hover:underline">
                    {app.worker_name}
                  </Link>
                  {app.worker_is_verified && <ShieldCheck className="h-4 w-4 text-emerald-600" />}
                  <span className="font-semibold">{formatCurrencyUZS(app.proposed_price)}</span>
                </div>
                <p className="text-xs text-muted-foreground">{app.cover_message}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                {app.status !== "WITHDRAWN" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      openChatMutation.mutate({ orderId: app.order, workerId: app.worker })
                    }
                  >
                    <MessageSquare className="h-4 w-4" />
                    {t("employer.openChatBtn")}
                  </Button>
                )}
                {app.status === "PENDING" && app.order_status === "PUBLISHED" && (
                  <>
                    <Button
                      size="sm"
                      variant="success"
                      disabled={acceptMutation.isPending}
                      onClick={() => acceptMutation.mutate(app.id)}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {t("employer.acceptApplicantBtn")}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={rejectMutation.isPending}
                      onClick={() => rejectMutation.mutate(app.id)}
                    >
                      <XCircle className="h-4 w-4" />
                      {t("employer.rejectApplicantBtn")}
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
