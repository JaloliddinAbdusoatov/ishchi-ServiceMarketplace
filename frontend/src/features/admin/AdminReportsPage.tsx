import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Flag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PaginationBar } from "@/components/shared/PaginationBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { adminApi } from "@/services/api";
import { extractApiErrorMessage, formatDateTime } from "@/lib/utils";
import type { ReportStatus } from "@/types/api";

export function AdminReportsPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const [actionTarget, setActionTarget] = useState<{
    id: string;
    nextStatus: ReportStatus;
  } | null>(null);
  const [resolutionText, setResolutionText] = useState("");

  const query = useQuery({
    queryKey: ["admin", "reports", { status, page }],
    queryFn: () =>
      adminApi.listReports({
        status: status || undefined,
        page,
        page_size: 15,
      }),
  });

  const resolveMutation = useMutation({
    mutationFn: ({
      reportId,
      nextStatus,
      adminResolution,
    }: {
      reportId: string;
      nextStatus: ReportStatus;
      adminResolution: string;
    }) => adminApi.resolveReport(reportId, nextStatus, adminResolution),
    onSuccess: () => {
      toast.success(t("common.confirm"));
      setActionTarget(null);
      setResolutionText("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "reports"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const items = query.data?.results || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.adminReports")}</h1>
        <NativeSelect
          className="w-52"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("common.all")}</option>
          <option value="OPEN">{t("statuses.OPEN")}</option>
          <option value="UNDER_REVIEW">{t("statuses.UNDER_REVIEW")}</option>
          <option value="RESOLVED">{t("statuses.RESOLVED")}</option>
          <option value="REJECTED">{t("statuses.REJECTED")}</option>
        </NativeSelect>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-64" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<Flag className="h-6 w-6" />} title={t("common.noData")} />
      ) : (
        <>
          <div className="space-y-3">
            {items.map((rep) => (
              <Card key={rep.id} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{rep.target_type}</Badge>
                    <Badge variant="secondary">{t(`reports.reasons.${rep.reason}`)}</Badge>
                    <StatusBadge status={rep.status} showIcon />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(rep.created_at, i18n.language)}
                  </span>
                </div>

                <p className="text-sm">{rep.description}</p>
                <p className="text-xs text-muted-foreground">Reporter: {rep.reporter_name}</p>

                {rep.admin_resolution && (
                  <p className="rounded-md bg-muted px-3 py-1.5 text-xs">
                    <strong>Resolution:</strong> {rep.admin_resolution}
                  </p>
                )}

                {["OPEN", "UNDER_REVIEW"].includes(rep.status) && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button
                      size="sm"
                      onClick={() => {
                        setActionTarget({ id: rep.id, nextStatus: "RESOLVED" });
                        setResolutionText("");
                      }}
                    >
                      {t("admin.resolveReport")}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setActionTarget({ id: rep.id, nextStatus: "REJECTED" });
                        setResolutionText("");
                      }}
                    >
                      {t("admin.rejectReport")}
                    </Button>
                  </div>
                )}
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

      <Dialog open={Boolean(actionTarget)} onOpenChange={(o) => !o && setActionTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionTarget?.nextStatus === "RESOLVED"
                ? t("admin.resolveReport")
                : t("admin.rejectReport")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!actionTarget) return;
              resolveMutation.mutate({
                reportId: actionTarget.id,
                nextStatus: actionTarget.nextStatus,
                adminResolution: resolutionText,
              });
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="report-resolution">Resolution notes</Label>
              <Textarea
                id="report-resolution"
                rows={3}
                value={resolutionText}
                onChange={(e) => setResolutionText(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setActionTarget(null)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={resolveMutation.isPending}>
                {t("common.confirm")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
