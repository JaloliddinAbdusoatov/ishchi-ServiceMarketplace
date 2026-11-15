import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Briefcase, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PaginationBar } from "@/components/shared/PaginationBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { adminApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDate } from "@/lib/utils";

export function AdminOrdersPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["admin", "orders", { search, status, page }],
    queryFn: () =>
      adminApi.listOrders({
        search: search || undefined,
        status: status || undefined,
        page,
        page_size: 15,
      }),
  });

  const moderateMutation = useMutation({
    mutationFn: ({ orderId, action }: { orderId: string; action: "CANCEL" | "CLOSE" }) =>
      adminApi.moderateOrder(orderId, action, "Moderated by admin"),
    onSuccess: (_, vars) => {
      toast.success(
        vars.action === "CANCEL" ? t("admin.moderateCancel") : t("admin.moderateClose")
      );
      void queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const items = query.data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.adminOrders")}</h1>

      <Card className="p-4 grid gap-3 sm:grid-cols-2">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder={t("common.search")}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <NativeSelect
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("common.all")}</option>
          {["DRAFT", "PUBLISHED", "PAUSED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "CLOSED"].map(
            (st) => (
              <option key={st} value={st}>
                {t(`statuses.${st}`)}
              </option>
            )
          )}
        </NativeSelect>
      </Card>

      {query.isLoading ? (
        <Skeleton className="h-64" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<Briefcase className="h-6 w-6" />} title={t("common.noData")} />
      ) : (
        <>
          <div className="space-y-3">
            {items.map((order) => (
              <Card
                key={order.id}
                className="p-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/orders/${order.id}`}
                      className="font-semibold hover:text-primary hover:underline"
                    >
                      {order.title}
                    </Link>
                    <StatusBadge status={order.status} showIcon />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {order.employer_name} • {order.category_name} •{" "}
                    {formatCurrencyUZS(order.budget)} • {formatDate(order.created_at, i18n.language)}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 shrink-0">
                  <Link to={`/orders/${order.id}`}>
                    <Button variant="outline" size="sm">
                      {t("common.details")}
                    </Button>
                  </Link>
                  {!["COMPLETED", "CANCELLED", "CLOSED"].includes(order.status) && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={moderateMutation.isPending}
                        onClick={() =>
                          moderateMutation.mutate({ orderId: order.id, action: "CLOSE" })
                        }
                      >
                        {t("admin.moderateClose")}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={moderateMutation.isPending}
                        onClick={() =>
                          moderateMutation.mutate({ orderId: order.id, action: "CANCEL" })
                        }
                      >
                        {t("admin.moderateCancel")}
                      </Button>
                    </>
                  )}
                </div>
              </Card>
            ))}
          </div>

          <PaginationBar
            currentPage={query.data?.current_page || 1}
            totalPages={query.data?.total_pages || 1}
            count={query.data?.count || 0}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
