import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { CheckCircle2, PlusCircle, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ordersApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDate } from "@/lib/utils";

export function EmployerOrdersPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");

  const ordersQuery = useQuery({
    queryKey: ["orders", "mine", statusFilter],
    queryFn: () =>
      ordersApi.list({
        mine: true,
        status: statusFilter || undefined,
        page_size: 50,
      }),
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      id,
      action,
    }: {
      id: string;
      action: "publish" | "pause" | "close" | "cancel" | "complete" | "delete";
    }) => {
      if (action === "publish") return ordersApi.publish(id);
      if (action === "pause") return ordersApi.pause(id);
      if (action === "close") return ordersApi.close(id);
      if (action === "cancel") return ordersApi.cancel(id);
      if (action === "complete") return ordersApi.complete(id);
      return ordersApi.remove(id);
    },
    onSuccess: () => {
      toast.success(t("common.save"));
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "employer"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t("nav.myOrders")}</h1>
        <div className="flex items-center gap-3">
          <NativeSelect
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-44"
          >
            <option value="">{t("common.all")}</option>
            {["DRAFT", "PUBLISHED", "PAUSED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "CLOSED"].map(
              (s) => (
                <option key={s} value={s}>
                  {t(`statuses.${s}`, s)}
                </option>
              )
            )}
          </NativeSelect>
          <Link to="/employer/orders/new">
            <Button className="gap-1.5">
              <PlusCircle className="h-4 w-4" />
              {t("nav.createOrder")}
            </Button>
          </Link>
        </div>
      </div>

      {ordersQuery.isLoading ? (
        <Skeleton className="h-64" />
      ) : ordersQuery.isError ? (
        <ErrorState onRetry={() => void ordersQuery.refetch()} />
      ) : (ordersQuery.data?.results.length ?? 0) === 0 ? (
        <EmptyState
          title={t("common.noData")}
          action={
            <Link to="/employer/orders/new">
              <Button>{t("nav.createOrder")}</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {ordersQuery.data?.results.map((order) => (
            <Card key={order.id} className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/orders/${order.id}`}
                    className="font-semibold text-base hover:text-primary hover:underline"
                  >
                    {order.title}
                  </Link>
                  <StatusBadge status={order.status} showIcon />
                </div>
                <p className="text-sm font-medium text-primary">
                  {formatCurrencyUZS(order.budget)} • {order.category_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {order.location} • {t("marketplace.applicationsCount", { count: order.applications_count })} •{" "}
                  {formatDate(order.created_at, i18n.language)}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Link to={`/orders/${order.id}`}>
                  <Button size="sm" variant="outline">
                    {t("common.details")}
                  </Button>
                </Link>
                {["DRAFT", "PUBLISHED", "PAUSED"].includes(order.status) && (
                  <Link to={`/employer/orders/${order.id}/edit`}>
                    <Button size="sm" variant="secondary">
                      {t("common.edit")}
                    </Button>
                  </Link>
                )}
                {(order.status === "DRAFT" || order.status === "PAUSED") && (
                  <Button
                    size="sm"
                    onClick={() => actionMutation.mutate({ id: order.id, action: "publish" })}
                  >
                    {t("employer.publishBtn")}
                  </Button>
                )}
                {order.status === "PUBLISHED" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => actionMutation.mutate({ id: order.id, action: "pause" })}
                  >
                    {t("employer.pauseBtn")}
                  </Button>
                )}
                {order.status === "IN_PROGRESS" && (
                  <Button
                    size="sm"
                    variant="success"
                    onClick={() => actionMutation.mutate({ id: order.id, action: "complete" })}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t("employer.completeOrderBtn")}
                  </Button>
                )}
                {order.status === "DRAFT" && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => actionMutation.mutate({ id: order.id, action: "delete" })}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    {t("common.delete")}
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
