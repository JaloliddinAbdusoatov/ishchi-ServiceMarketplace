import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { reviewsApi } from "@/services/api";
import { formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import type { Review } from "@/types/api";

function ReviewList({
  items,
  lang,
  emptyLabel,
}: {
  items: Review[];
  lang: string;
  emptyLabel: string;
}) {
  if (items.length === 0) {
    return <EmptyState icon={<Star className="h-6 w-6" />} title={emptyLabel} />;
  }

  return (
    <div className="space-y-3">
      {items.map((review) => (
        <Card key={review.id} className="p-4 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <Link
                to={`/orders/${review.order}`}
                className="font-semibold text-sm hover:text-primary hover:underline"
              >
                {review.order_title}
              </Link>
              <p className="text-xs text-muted-foreground">
                {review.reviewer_name} → {review.reviewee_name}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{review.direction}</Badge>
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
                <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                {review.rating} / 5
              </span>
            </div>
          </div>
          {review.comment && <p className="text-sm text-foreground">{review.comment}</p>}
          <p className="text-[11px] text-muted-foreground">{formatDate(review.created_at, lang)}</p>
        </Card>
      ))}
    </div>
  );
}

export function ReviewsPage() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);

  const receivedQuery = useQuery({
    queryKey: ["reviews", "received", user?.id],
    queryFn: () => reviewsApi.list({ reviewee: user?.id, page_size: 50 }),
    enabled: Boolean(user?.id),
  });

  const givenQuery = useQuery({
    queryKey: ["reviews", "given", user?.id],
    queryFn: () => reviewsApi.list({ reviewer: user?.id, page_size: 50 }),
    enabled: Boolean(user?.id),
  });

  const received = receivedQuery.data?.results || [];
  const given = givenQuery.data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("reviews.title")}</h1>

      <Tabs defaultValue="received">
        <TabsList>
          <TabsTrigger value="received">Received ({received.length})</TabsTrigger>
          <TabsTrigger value="given">Submitted ({given.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="received" className="mt-4">
          {receivedQuery.isLoading ? (
            <Skeleton className="h-48" />
          ) : receivedQuery.isError ? (
            <ErrorState onRetry={() => void receivedQuery.refetch()} />
          ) : (
            <ReviewList items={received} lang={i18n.language} emptyLabel={t("reviews.noReviews")} />
          )}
        </TabsContent>

        <TabsContent value="given" className="mt-4">
          {givenQuery.isLoading ? (
            <Skeleton className="h-48" />
          ) : givenQuery.isError ? (
            <ErrorState onRetry={() => void givenQuery.refetch()} />
          ) : (
            <ReviewList items={given} lang={i18n.language} emptyLabel={t("reviews.noReviews")} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
