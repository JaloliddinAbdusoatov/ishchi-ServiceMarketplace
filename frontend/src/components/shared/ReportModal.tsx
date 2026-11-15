import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { reportsApi } from "@/services/api";
import { extractApiErrorMessage } from "@/lib/utils";
import type { ReportReason, ReportTargetType } from "@/types/api";

interface ReportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  targetType: ReportTargetType;
  targetId: string;
}

export function ReportModal({ open, onOpenChange, targetType, targetId }: ReportModalProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState<ReportReason>("SPAM");
  const [description, setDescription] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      reportsApi.create({
        target_type: targetType,
        target_id: targetId,
        reason,
        description,
      }),
    onSuccess: () => {
      toast.success(t("common.submit"));
      setDescription("");
      onOpenChange(false);
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim().length < 5) {
      toast.error(t("validation.minChars", { min: 5 }));
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("reports.modalTitle")}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="report-reason">{t("reports.reasonLabel")}</Label>
            <NativeSelect
              id="report-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as ReportReason)}
            >
              {(["SPAM", "FRAUD", "HARASSMENT", "INAPPROPRIATE", "OTHER"] as ReportReason[]).map(
                (r) => (
                  <option key={r} value={r}>
                    {t(`reports.reasons.${r}`)}
                  </option>
                )
              )}
            </NativeSelect>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="report-desc">{t("reports.descriptionLabel")}</Label>
            <Textarea
              id="report-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" variant="destructive" disabled={mutation.isPending}>
              {mutation.isPending ? t("common.loading") : t("common.submit")}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
