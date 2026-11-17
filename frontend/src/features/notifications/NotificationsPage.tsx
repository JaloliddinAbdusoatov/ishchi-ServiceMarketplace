import { notificationText } from "@/lib/notificationText";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Bell, CheckCheck, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PaginationBar } from "@/components/shared/PaginationBar";
import { notificationsApi } from "@/services/api";
import { extractApiErrorMessage, formatDateTime } from "@/lib/utils";

export function NotificationsPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [filterUnread, setFilterUnread] = useState(false);
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["notifications", { filterUnread, page }],
    queryFn: () =>
      notificationsApi.list({
        is_read: filterUnread ? false : undefined,
        page,
        page_size: 20,
      }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const markAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success(t("notifications.markAllRead"));
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const items = query.data?.results || [];
  const unreadCount = query.data?.unread_count ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{t("notifications.title")}</h1>
          {unreadCount > 0 && (
            <Badge variant="default">
              {t("notifications.unreadCount", { count: unreadCount })}
            </Badge>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={filterUnread ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setFilterUnread((prev) => !prev);
              setPage(1);
            }}
          >
            {filterUnread ? t("common.all") : t("notifications.unreadCount", { count: unreadCount })}
          </Button>
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              disabled={markAllMutation.isPending}
              onClick={() => markAllMutation.mutate()}
            >
              <CheckCheck className="h-4 w-4" />
              {t("notifications.markAllRead")}
            </Button>
          )}
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-64" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<Bell className="h-6 w-6" />} title={t("notifications.empty")} />
      ) : (
        <>
          <div className="space-y-2.5">
            {items.map((item) => {
              const orderId =
                typeof item.data?.order_id === "string" ? item.data.order_id : null;
              const conversationId =
                typeof item.data?.conversation_id === "string" ? item.data.conversation_id : null;

              return (
                <Card
                  key={item.id}
                  className={`p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between ${
                    !item.is_read ? "border-primary/40 bg-primary/5" : ""
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={item.is_read ? "secondary" : "default"}>
                        {notificationText(item, t).event}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(item.created_at, i18n.language)}
                      </span>
                    </div>
                    <p className="font-semibold text-sm">{notificationText(item, t).title}</p>
                    <p className="text-sm text-muted-foreground">{notificationText(item, t).message}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {orderId && (
                      <Link to={`/orders/${orderId}`}>
                        <Button variant="outline" size="sm">
                          {t("common.details")}
                        </Button>
                      </Link>
                    )}
                    {conversationId && (
                      <Link to={`/dashboard/messages?conversation=${conversationId}`}>
                        <Button variant="outline" size="sm">
                          {t("nav.messages")}
                        </Button>
                      </Link>
                    )}
                    {!item.is_read && (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={markReadMutation.isPending}
                        onClick={() => markReadMutation.mutate(item.id)}
                      >
                        {t("notifications.markRead")}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={t("common.delete")}
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(item.id)}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                    </Button>
                  </div>
                </Card>
              );
            })}
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
