import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Search, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PaginationBar } from "@/components/shared/PaginationBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { adminApi } from "@/services/api";
import { extractApiErrorMessage, formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function AdminUsersPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);

  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const [suspendTarget, setSuspendTarget] = useState<string | null>(null);
  const [suspendReason, setSuspendReason] = useState("");

  const usersQuery = useQuery({
    queryKey: ["admin", "users", { search, role, status, page }],
    queryFn: () =>
      adminApi.listUsers({
        search: search || undefined,
        role: role || undefined,
        account_status: status || undefined,
        page,
        page_size: 15,
      }),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminApi.suspendUser(userId, reason),
    onSuccess: () => {
      toast.success(t("admin.suspendUser"));
      setSuspendTarget(null);
      setSuspendReason("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const activateMutation = useMutation({
    mutationFn: (userId: string) => adminApi.activateUser(userId),
    onSuccess: () => {
      toast.success(t("admin.activateUser"));
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const items = usersQuery.data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.adminUsers")}</h1>

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-3">
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
            value={role}
            onChange={(e) => {
              setRole(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t("common.all")} (Role)</option>
            <option value="WORKER">WORKER</option>
            <option value="EMPLOYER">EMPLOYER</option>
            <option value="ADMIN">ADMIN</option>
          </NativeSelect>
          <NativeSelect
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t("common.all")} ({t("common.status")})</option>
            <option value="ACTIVE">{t("statuses.ACTIVE")}</option>
            <option value="SUSPENDED">{t("statuses.SUSPENDED")}</option>
            <option value="DELETED">{t("statuses.DELETED")}</option>
          </NativeSelect>
        </div>
      </Card>

      {usersQuery.isLoading ? (
        <Skeleton className="h-64" />
      ) : usersQuery.isError ? (
        <ErrorState onRetry={() => void usersQuery.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<Users className="h-6 w-6" />} title={t("common.noData")} />
      ) : (
        <>
          <div className="space-y-2.5">
            {items.map((u) => {
              const isSelf = u.id === currentUser?.id;
              return (
                <Card
                  key={u.id}
                  className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{u.full_name}</span>
                      <Badge variant="outline">{u.role}</Badge>
                      {u.is_worker && u.is_employer && (
                        <Badge variant="secondary">WORKER + EMPLOYER</Badge>
                      )}
                      <StatusBadge status={u.account_status} showIcon />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {u.phone_number || "—"} {u.email ? `• ${u.email}` : ""} •{" "}
                      {formatDate(u.created_at, i18n.language)}
                    </p>
                  </div>

                  {!isSelf && u.account_status !== "DELETED" && (
                    <div className="flex gap-2">
                      {u.account_status === "ACTIVE" ? (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            setSuspendTarget(u.id);
                            setSuspendReason("");
                          }}
                        >
                          {t("admin.suspendUser")}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={activateMutation.isPending}
                          onClick={() => activateMutation.mutate(u.id)}
                        >
                          {t("admin.activateUser")}
                        </Button>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>

          <PaginationBar
            currentPage={usersQuery.data?.current_page || 1}
            totalPages={usersQuery.data?.total_pages || 1}
            count={usersQuery.data?.count || 0}
            onPageChange={setPage}
          />
        </>
      )}

      <Dialog open={Boolean(suspendTarget)} onOpenChange={(o) => !o && setSuspendTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("admin.suspendUser")}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!suspendTarget) return;
              suspendMutation.mutate({ userId: suspendTarget, reason: suspendReason });
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="suspend-reason">{t("settings.deleteReasonLabel")}</Label>
              <Input
                id="suspend-reason"
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setSuspendTarget(null)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" variant="destructive" disabled={suspendMutation.isPending}>
                {t("admin.suspendUser")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
