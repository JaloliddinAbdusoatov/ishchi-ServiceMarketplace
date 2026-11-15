import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, CheckCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { notificationsApi } from "@/services/api";
import { formatDateTime } from "@/lib/utils";
import type { NotificationItem } from "@/types/api";

export function NotificationBell() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data } = useQuery({
    queryKey: ["notifications", "dropdown"],
    queryFn: () => notificationsApi.list({ page_size: 6 }),
    refetchInterval: 15000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const unread = data?.unread_count ?? 0;
  const items = data?.results ?? [];

  const handleNavigate = (item: NotificationItem) => {
    if (!item.is_read) {
      markReadMutation.mutate(item.id);
    }
    setOpen(false);
    const payload = item.data || {};
    if (typeof payload.conversation_id === "string") {
      navigate("/dashboard/messages");
    } else if (typeof payload.order_id === "string") {
      navigate(`/orders/${payload.order_id}`);
    } else {
      navigate("/notifications");
    }
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("notifications.title")}
        onClick={() => setOpen((o) => !o)}
        className="relative"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-80 sm:w-96 rounded-xl border bg-card shadow-xl">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div>
                <h4 className="text-sm font-semibold">{t("notifications.title")}</h4>
                <p className="text-xs text-muted-foreground">
                  {t("notifications.unreadCount", { count: unread })}
                </p>
              </div>
              {unread > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => markAllMutation.mutate()}
                  disabled={markAllMutation.isPending}
                >
                  <CheckCheck className="h-4 w-4" />
                  {t("notifications.markAllRead")}
                </Button>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto divide-y">
              {items.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  {t("notifications.empty")}
                </div>
              ) : (
                items.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-start gap-2 px-4 py-3 text-sm transition-colors hover:bg-muted/50 ${
                      !item.is_read ? "bg-accent/50" : ""
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleNavigate(item)}
                      className="flex-1 text-left"
                    >
                      <p className="font-medium text-foreground">{item.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                        {item.message}
                      </p>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        {formatDateTime(item.created_at, i18n.language)}
                      </p>
                    </button>
                    {!item.is_read && (
                      <button
                        type="button"
                        onClick={() => markReadMutation.mutate(item.id)}
                        title={t("notifications.markRead")}
                        className="rounded p-1 text-primary hover:bg-primary/10"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="border-t p-2 text-center">
              <Link
                to="/notifications"
                onClick={() => setOpen(false)}
                className="block rounded-md py-1.5 text-xs font-medium text-primary hover:bg-muted"
              >
                {t("common.viewAll")}
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
