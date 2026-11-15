import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { CheckCircle2, MapPin, UserCheck, XCircle } from "lucide-react";
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
import { extractApiErrorMessage, getLocalizedCategoryName } from "@/lib/utils";

export function AdminVerificationPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [page, setPage] = useState(1);

  const [rejectWorkerId, setRejectWorkerId] = useState<string | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");

  const query = useQuery({
    queryKey: ["admin", "workers", { statusFilter, page }],
    queryFn: () =>
      adminApi.listWorkers({
        verification_status: statusFilter || undefined,
        page,
        page_size: 15,
      }),
  });

  const verifyMutation = useMutation({
    mutationFn: ({
      workerId,
      action,
      notes,
    }: {
      workerId: string;
      action: "APPROVE" | "REJECT";
      notes?: string;
    }) => adminApi.verifyWorker(workerId, action, notes || ""),
    onSuccess: (_, vars) => {
      toast.success(
        vars.action === "APPROVE" ? t("admin.approveWorker") : t("admin.rejectWorker")
      );
      setRejectWorkerId(null);
      setRejectNotes("");
      void queryClient.invalidateQueries({ queryKey: ["admin", "workers"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "dashboard"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const items = query.data?.results || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.adminVerification")}</h1>
        <NativeSelect
          className="w-52"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="PENDING">{t("statuses.PENDING")}</option>
          <option value="UNSUBMITTED">{t("statuses.UNSUBMITTED")}</option>
          <option value="VERIFIED">{t("statuses.VERIFIED")}</option>
          <option value="REJECTED">{t("statuses.REJECTED")}</option>
          <option value="">{t("common.all")}</option>
        </NativeSelect>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-64" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon={<UserCheck className="h-6 w-6" />} title={t("common.noData")} />
      ) : (
        <>
          <div className="space-y-3">
            {items.map((w) => (
              <Card key={w.id} className="p-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-semibold">{w.full_name}</span>
                    <StatusBadge status={w.verification_status} showIcon />
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3.5 w-3.5" />
                      {w.location || "—"} {w.district ? `, ${w.district}` : ""}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{w.bio || "—"}</p>
                  {w.verification_notes && (
                    <p className="rounded-md bg-muted px-3 py-1.5 text-xs">
                      <strong>Notes:</strong> {w.verification_notes}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1.5">
                    {w.categories?.map((cat) => (
                      <Badge key={cat.id} variant="secondary">
                        {getLocalizedCategoryName(cat, i18n.language)}
                      </Badge>
                    ))}
                    {w.skills?.map((s) => (
                      <Badge key={s} variant="outline">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 shrink-0">
                  {w.verification_status !== "VERIFIED" && (
                    <Button
                      size="sm"
                      className="gap-1.5"
                      disabled={verifyMutation.isPending}
                      onClick={() =>
                        verifyMutation.mutate({
                          workerId: w.id,
                          action: "APPROVE",
                          notes: "Approved by admin",
                        })
                      }
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {t("admin.approveWorker")}
                    </Button>
                  )}
                  {w.verification_status !== "REJECTED" && (
                    <Button
                      size="sm"
                      variant="destructive"
                      className="gap-1.5"
                      disabled={verifyMutation.isPending}
                      onClick={() => {
                        setRejectWorkerId(w.id);
                        setRejectNotes("");
                      }}
                    >
                      <XCircle className="h-4 w-4" />
                      {t("admin.rejectWorker")}
                    </Button>
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

      <Dialog open={Boolean(rejectWorkerId)} onOpenChange={(o) => !o && setRejectWorkerId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("admin.rejectWorker")}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!rejectWorkerId) return;
              verifyMutation.mutate({
                workerId: rejectWorkerId,
                action: "REJECT",
                notes: rejectNotes,
              });
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="reject-notes">{t("worker.verificationNotesLabel")}</Label>
              <Textarea
                id="reject-notes"
                rows={3}
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setRejectWorkerId(null)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" variant="destructive" disabled={verifyMutation.isPending}>
                {t("admin.rejectWorker")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
