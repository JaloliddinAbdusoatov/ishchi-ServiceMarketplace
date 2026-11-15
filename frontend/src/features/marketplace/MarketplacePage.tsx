import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { LayoutGrid, List, Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { OrderCard } from "@/components/shared/OrderCard";
import { PaginationBar } from "@/components/shared/PaginationBar";
import { WorkerCard } from "@/components/shared/WorkerCard";
import { categoriesApi, favoritesApi, ordersApi, workersApi } from "@/services/api";
import { extractApiErrorMessage, getLocalizedCategoryName } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function MarketplacePage({ defaultTab = "orders" }: { defaultTab?: "orders" | "workers" } = {}) {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const tabParam = searchParams.get("tab");
  const activeTab = (
    tabParam === "workers" || tabParam === "orders" ? tabParam : defaultTab
  ) as "orders" | "workers";
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  // Shared & filter state derived cleanly from URL params + local inputs
  const search = searchParams.get("search") || "";
  const category = searchParams.get("category") || "";
  const location = searchParams.get("location") || "";
  const district = searchParams.get("district") || "";
  const budgetMin = searchParams.get("budget_min") || "";
  const budgetMax = searchParams.get("budget_max") || "";
  const budgetType = searchParams.get("budget_type") || "";
  const workType = searchParams.get("work_type") || "";
  const isVerified = searchParams.get("is_verified") || "";
  const isAvailable = searchParams.get("is_available") || "";
  const minRating = searchParams.get("min_rating") || "";
  const minExperience = searchParams.get("min_experience") || "";
  const maxHourlyRate = searchParams.get("max_hourly_rate") || "";
  const ordering = searchParams.get("ordering") || (activeTab === "orders" ? "-created_at" : "-rating_avg");
  const page = Number(searchParams.get("page") || "1");

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  };

  const resetFilters = () => {
    setSearchParams({ tab: activeTab });
  };

  const categoriesQuery = useQuery({
    queryKey: ["categories", "all"],
    queryFn: () => categoriesApi.list({ page_size: 100 }),
  });

  const flatCategories = useMemo(() => {
    const items = categoriesQuery.data?.results || [];
    const out: Array<{ id: string; label: string }> = [];
    items.forEach((cat) => {
      out.push({ id: cat.id, label: getLocalizedCategoryName(cat, i18n.language) });
    });
    return out;
  }, [categoriesQuery.data, i18n.language]);

  const ordersQuery = useQuery({
    queryKey: [
      "orders",
      "marketplace",
      { search, category, location, district, budgetMin, budgetMax, budgetType, workType, ordering, page },
    ],
    queryFn: () =>
      ordersApi.list({
        status: "PUBLISHED",
        search: search || undefined,
        category: category || undefined,
        location: location || undefined,
        district: district || undefined,
        budget_min: budgetMin || undefined,
        budget_max: budgetMax || undefined,
        budget_type: budgetType || undefined,
        work_type: workType || undefined,
        ordering: ordering || undefined,
        page,
        page_size: 12,
      }),
    enabled: activeTab === "orders",
  });

  const workersQuery = useQuery({
    queryKey: [
      "workers",
      "marketplace",
      {
        search,
        category,
        location,
        district,
        isVerified,
        isAvailable,
        minRating,
        minExperience,
        maxHourlyRate,
        ordering,
        page,
      },
    ],
    queryFn: () =>
      workersApi.list({
        search: search || undefined,
        category: category || undefined,
        location: location || undefined,
        district: district || undefined,
        is_verified: isVerified || undefined,
        is_available: isAvailable || undefined,
        min_rating: minRating || undefined,
        min_experience: minExperience || undefined,
        max_hourly_rate: maxHourlyRate || undefined,
        ordering: ordering || undefined,
        page,
        page_size: 12,
      }),
    enabled: activeTab === "workers",
  });

  const favOrdersQuery = useQuery({
    queryKey: ["favorites", "orders"],
    queryFn: favoritesApi.listOrders,
    enabled: Boolean(user),
  });

  const favWorkersQuery = useQuery({
    queryKey: ["favorites", "workers"],
    queryFn: favoritesApi.listWorkers,
    enabled: Boolean(user),
  });

  const favOrderIds = new Set((favOrdersQuery.data?.results || []).map((f) => f.order));
  const favWorkerIds = new Set((favWorkersQuery.data?.results || []).map((f) => f.worker));

  const toggleOrderFav = useMutation({
    mutationFn: async (orderId: string) => {
      if (favOrderIds.has(orderId)) return favoritesApi.removeOrder(orderId);
      return favoritesApi.addOrder(orderId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["favorites", "orders"] });
      toast.success(t("common.save"));
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const toggleWorkerFav = useMutation({
    mutationFn: async (workerId: string) => {
      if (favWorkerIds.has(workerId)) return favoritesApi.removeWorker(workerId);
      return favoritesApi.addWorker(workerId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["favorites", "workers"] });
      toast.success(t("common.save"));
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  return (
    <div className="container py-8">
      {/* Header + Tab Switcher */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("nav.marketplace")}</h1>
          <p className="text-sm text-muted-foreground">{t("brand.tagline")}</p>
        </div>

        <div className="flex items-center gap-3">
          <Tabs
            value={activeTab}
            onValueChange={(val) => setSearchParams({ tab: val })}
          >
            <TabsList>
              <TabsTrigger value="orders">{t("marketplace.ordersTab")}</TabsTrigger>
              <TabsTrigger value="workers">{t("marketplace.workersTab")}</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="hidden sm:flex rounded-lg border bg-card p-1">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              aria-label="Grid View"
              className={`rounded-md p-1.5 ${viewMode === "grid" ? "bg-muted text-primary" : "text-muted-foreground"}`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              aria-label="List View"
              className={`rounded-md p-1.5 ${viewMode === "list" ? "bg-muted text-primary" : "text-muted-foreground"}`}
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar Filters */}
        <Card className="h-fit p-5 lg:col-span-1 space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <span className="inline-flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal className="h-4 w-4 text-primary" />
              {t("marketplace.filtersTitle")}
            </span>
            <button
              type="button"
              onClick={resetFilters}
              className="text-xs font-medium text-primary hover:underline"
            >
              {t("common.resetFilters")}
            </button>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="mkt-search">{t("common.search")}</Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="mkt-search"
                className="pl-8"
                value={search}
                onChange={(e) => updateParam("search", e.target.value)}
                placeholder={t("landing.searchPlaceholder")}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="mkt-cat">{t("marketplace.category")}</Label>
            <NativeSelect
              id="mkt-cat"
              value={category}
              onChange={(e) => updateParam("category", e.target.value)}
            >
              <option value="">{t("common.all")}</option>
              {flatCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </NativeSelect>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1.5">
              <Label htmlFor="mkt-loc">{t("marketplace.location")}</Label>
              <Input
                id="mkt-loc"
                value={location}
                onChange={(e) => updateParam("location", e.target.value)}
                placeholder="Toshkent"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="mkt-dist">{t("marketplace.district")}</Label>
              <Input
                id="mkt-dist"
                value={district}
                onChange={(e) => updateParam("district", e.target.value)}
                placeholder="Chilonzor"
              />
            </div>
          </div>

          {activeTab === "orders" ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="mkt-bmin">{t("marketplace.budgetMin")}</Label>
                  <Input
                    id="mkt-bmin"
                    type="number"
                    value={budgetMin}
                    onChange={(e) => updateParam("budget_min", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="mkt-bmax">{t("marketplace.budgetMax")}</Label>
                  <Input
                    id="mkt-bmax"
                    type="number"
                    value={budgetMax}
                    onChange={(e) => updateParam("budget_max", e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="mkt-btype">{t("marketplace.budgetType")}</Label>
                <NativeSelect
                  id="mkt-btype"
                  value={budgetType}
                  onChange={(e) => updateParam("budget_type", e.target.value)}
                >
                  <option value="">{t("common.all")}</option>
                  <option value="FIXED">{t("statuses.FIXED")}</option>
                  <option value="HOURLY">{t("statuses.HOURLY")}</option>
                  <option value="NEGOTIABLE">{t("statuses.NEGOTIABLE")}</option>
                </NativeSelect>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="mkt-wtype">{t("marketplace.workType")}</Label>
                <NativeSelect
                  id="mkt-wtype"
                  value={workType}
                  onChange={(e) => updateParam("work_type", e.target.value)}
                >
                  <option value="">{t("common.all")}</option>
                  <option value="ONSITE">{t("statuses.ONSITE")}</option>
                  <option value="REMOTE">{t("statuses.REMOTE")}</option>
                  <option value="HYBRID">{t("statuses.HYBRID")}</option>
                </NativeSelect>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="mkt-sort-o">{t("marketplace.sortBy")}</Label>
                <NativeSelect
                  id="mkt-sort-o"
                  value={ordering}
                  onChange={(e) => updateParam("ordering", e.target.value)}
                >
                  <option value="-created_at">{t("marketplace.sortNewest")}</option>
                  <option value="-budget">{t("marketplace.sortBudgetDesc")}</option>
                  <option value="budget">{t("marketplace.sortBudgetAsc")}</option>
                </NativeSelect>
              </div>
            </>
          ) : (
            <>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={isVerified === "true"}
                  onChange={(e) => updateParam("is_verified", e.target.checked ? "true" : "")}
                />
                <span>{t("marketplace.verifiedOnly")}</span>
              </label>

              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAvailable === "true"}
                  onChange={(e) => updateParam("is_available", e.target.checked ? "true" : "")}
                />
                <span>{t("marketplace.availableOnly")}</span>
              </label>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="mkt-rating">{t("marketplace.minRating")}</Label>
                  <Input
                    id="mkt-rating"
                    type="number"
                    step="0.5"
                    min="0"
                    max="5"
                    value={minRating}
                    onChange={(e) => updateParam("min_rating", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="mkt-exp">{t("marketplace.minExperience")}</Label>
                  <Input
                    id="mkt-exp"
                    type="number"
                    min="0"
                    value={minExperience}
                    onChange={(e) => updateParam("min_experience", e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="mkt-hr">{t("marketplace.maxHourlyRate")}</Label>
                <Input
                  id="mkt-hr"
                  type="number"
                  value={maxHourlyRate}
                  onChange={(e) => updateParam("max_hourly_rate", e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="mkt-sort-w">{t("marketplace.sortBy")}</Label>
                <NativeSelect
                  id="mkt-sort-w"
                  value={ordering}
                  onChange={(e) => updateParam("ordering", e.target.value)}
                >
                  <option value="-rating_avg">{t("marketplace.sortRatingDesc")}</option>
                  <option value="-experience_years">{t("marketplace.sortExpDesc")}</option>
                  <option value="hourly_rate">{t("marketplace.sortBudgetAsc")}</option>
                </NativeSelect>
              </div>
            </>
          )}
        </Card>

        {/* Results Panel */}
        <div className="lg:col-span-3">
          {activeTab === "orders" ? (
            ordersQuery.isLoading ? (
              <div className="grid gap-4 md:grid-cols-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-52" />
                ))}
              </div>
            ) : ordersQuery.isError ? (
              <ErrorState onRetry={() => void ordersQuery.refetch()} />
            ) : (ordersQuery.data?.results.length ?? 0) === 0 ? (
              <EmptyState
                title={t("marketplace.emptyOrders")}
                action={
                  <Button variant="outline" onClick={resetFilters}>
                    {t("common.resetFilters")}
                  </Button>
                }
              />
            ) : (
              <>
                <div
                  className={
                    viewMode === "grid" ? "grid gap-4 md:grid-cols-2" : "flex flex-col gap-4"
                  }
                >
                  {ordersQuery.data?.results.map((order) => (
                    <OrderCard
                      key={order.id}
                      order={order}
                      isFavorite={favOrderIds.has(order.id)}
                      onToggleFavorite={
                        user ? (id) => toggleOrderFav.mutate(id) : undefined
                      }
                    />
                  ))}
                </div>
                <PaginationBar
                  currentPage={ordersQuery.data?.current_page || 1}
                  totalPages={ordersQuery.data?.total_pages || 1}
                  count={ordersQuery.data?.count || 0}
                  onPageChange={(p) => updateParam("page", String(p))}
                />
              </>
            )
          ) : workersQuery.isLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-52" />
              ))}
            </div>
          ) : workersQuery.isError ? (
            <ErrorState onRetry={() => void workersQuery.refetch()} />
          ) : (workersQuery.data?.results.length ?? 0) === 0 ? (
            <EmptyState
              title={t("marketplace.emptyWorkers")}
              action={
                <Button variant="outline" onClick={resetFilters}>
                  {t("common.resetFilters")}
                </Button>
              }
            />
          ) : (
            <>
              <div
                className={
                  viewMode === "grid" ? "grid gap-4 md:grid-cols-2" : "flex flex-col gap-4"
                }
              >
                {workersQuery.data?.results.map((worker) => (
                  <WorkerCard
                    key={worker.id}
                    worker={worker}
                    isFavorite={favWorkerIds.has(worker.id)}
                    onToggleFavorite={
                      user ? (id) => toggleWorkerFav.mutate(id) : undefined
                    }
                  />
                ))}
              </div>
              <PaginationBar
                currentPage={workersQuery.data?.current_page || 1}
                totalPages={workersQuery.data?.total_pages || 1}
                count={workersQuery.data?.count || 0}
                onPageChange={(p) => updateParam("page", String(p))}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
