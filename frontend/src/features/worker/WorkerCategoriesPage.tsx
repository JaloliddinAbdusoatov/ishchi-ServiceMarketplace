import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { categoriesApi, profilesApi } from "@/services/api";
import { extractApiErrorMessage, getLocalizedCategoryName } from "@/lib/utils";

export function WorkerCategoriesPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();

  const allCatsQuery = useQuery({
    queryKey: ["categories", "all"],
    queryFn: () => categoriesApi.list({ page_size: 100 }),
  });

  const myCatsQuery = useQuery({
    queryKey: ["my-worker-categories"],
    queryFn: profilesApi.getMyWorkerCategories,
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [primaryId, setPrimaryId] = useState<string | null>(null);

  useEffect(() => {
    if (myCatsQuery.data) {
      setSelectedIds(myCatsQuery.data.map((c) => c.category_id));
      const p = myCatsQuery.data.find((c) => c.is_primary);
      setPrimaryId(p ? p.category_id : null);
    }
  }, [myCatsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      profilesApi.updateMyWorkerCategories(
        selectedIds.map((id, idx) => ({
          category_id: id,
          is_primary: primaryId ? id === primaryId : idx === 0,
        }))
      ),
    onSuccess: () => {
      toast.success(t("common.save"));
      void queryClient.invalidateQueries({ queryKey: ["my-worker-categories"] });
      void queryClient.invalidateQueries({ queryKey: ["my-worker-profile"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const toggleCategory = (id: string) => {
    if (selectedIds.includes(id)) {
      const next = selectedIds.filter((x) => x !== id);
      setSelectedIds(next);
      if (primaryId === id) setPrimaryId(next[0] || null);
      return;
    }
    if (selectedIds.length >= 10) {
      toast.error(t("worker.categoriesTitle"));
      return;
    }
    const next = [...selectedIds, id];
    setSelectedIds(next);
    if (!primaryId) setPrimaryId(id);
  };

  if (allCatsQuery.isLoading || myCatsQuery.isLoading) {
    return <Skeleton className="h-80" />;
  }

  if (allCatsQuery.isError || myCatsQuery.isError) {
    return <ErrorState onRetry={() => void allCatsQuery.refetch()} />;
  }

  const allCategories = allCatsQuery.data?.results || [];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <CardTitle>{t("worker.categoriesTitle")}</CardTitle>
            <CardDescription className="mt-1">{t("worker.categoriesSubtitle")}</CardDescription>
          </div>
          <Badge variant={selectedIds.length >= 10 ? "warning" : "default"}>
            {selectedIds.length} / 10
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {allCategories.map((cat) => {
            const selected = selectedIds.includes(cat.id);
            const isPrimary = primaryId === cat.id;
            return (
              <div
                key={cat.id}
                className={`flex flex-col justify-between rounded-xl border p-4 transition-colors ${
                  selected ? "border-primary bg-accent/40" : "bg-card hover:bg-muted/40"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-sm">
                      {getLocalizedCategoryName(cat, i18n.language)}
                    </p>
                    {cat.parent_name && (
                      <p className="text-[11px] text-muted-foreground">{cat.parent_name}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleCategory(cat.id)}
                    className={`flex h-6 w-6 items-center justify-center rounded-md border ${
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input bg-card"
                    }`}
                    aria-label={cat.name}
                  >
                    {selected && <Check className="h-4 w-4" />}
                  </button>
                </div>

                {selected && (
                  <div className="mt-3 pt-2 border-t flex items-center justify-between">
                    {isPrimary ? (
                      <Badge variant="success" className="gap-1">
                        <Star className="h-3 w-3 fill-current" />
                        {t("worker.primaryCategory")}
                      </Badge>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setPrimaryId(cat.id)}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        {t("worker.setPrimary")}
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          {saveMutation.isPending ? t("common.loading") : t("common.save")}
        </Button>
      </CardContent>
    </Card>
  );
}
