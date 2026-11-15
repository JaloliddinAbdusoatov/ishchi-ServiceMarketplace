import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Heart } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { OrderCard } from "@/components/shared/OrderCard";
import { WorkerCard } from "@/components/shared/WorkerCard";
import { favoritesApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";

export function FavoritesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const workersQuery = useQuery({
    queryKey: ["favorites", "workers"],
    queryFn: () => favoritesApi.listWorkers(),
  });

  const ordersQuery = useQuery({
    queryKey: ["favorites", "orders"],
    queryFn: () => favoritesApi.listOrders(),
  });

  const removeWorkerMutation = useMutation({
    mutationFn: (workerId: string) => favoritesApi.removeWorker(workerId),
    onSuccess: () => {
      toast.success(t("marketplace.removeFavorite"));
      void queryClient.invalidateQueries({ queryKey: ["favorites", "workers"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const removeOrderMutation = useMutation({
    mutationFn: (orderId: string) => favoritesApi.removeOrder(orderId),
    onSuccess: () => {
      toast.success(t("marketplace.removeFavorite"));
      void queryClient.invalidateQueries({ queryKey: ["favorites", "orders"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const favWorkers = workersQuery.data?.results || [];
  const favOrders = ordersQuery.data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.favorites")}</h1>

      <Tabs defaultValue="orders">
        <TabsList>
          <TabsTrigger value="orders">
            {t("marketplace.ordersTab")} ({favOrders.length})
          </TabsTrigger>
          <TabsTrigger value="workers">
            {t("marketplace.workersTab")} ({favWorkers.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="orders" className="mt-4">
          {ordersQuery.isLoading ? (
            <Skeleton className="h-48" />
          ) : ordersQuery.isError ? (
            <ErrorState onRetry={() => void ordersQuery.refetch()} />
          ) : favOrders.length === 0 ? (
            <EmptyState icon={<Heart className="h-6 w-6" />} title={t("common.noData")} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {favOrders.map((fav) => (
                <OrderCard
                  key={fav.id}
                  order={fav.order_detail}
                  isFavorite
                  onToggleFavorite={(id) => removeOrderMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="workers" className="mt-4">
          {workersQuery.isLoading ? (
            <Skeleton className="h-48" />
          ) : workersQuery.isError ? (
            <ErrorState onRetry={() => void workersQuery.refetch()} />
          ) : favWorkers.length === 0 ? (
            <EmptyState icon={<Heart className="h-6 w-6" />} title={t("common.noData")} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {favWorkers.map((fav) => (
                <WorkerCard
                  key={fav.id}
                  worker={fav.worker_detail}
                  isFavorite
                  onToggleFavorite={(id) => removeWorkerMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
