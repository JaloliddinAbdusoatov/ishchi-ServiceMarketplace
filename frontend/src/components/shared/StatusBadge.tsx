import { useTranslation } from "react-i18next";
import { ShieldCheck, Clock, CheckCircle2, XCircle, Ban } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface StatusBadgeProps {
  status: string;
  showIcon?: boolean;
}

const VARIANT_MAP: Record<string, "default" | "secondary" | "success" | "warning" | "destructive" | "outline"> = {
  PUBLISHED: "default",
  IN_PROGRESS: "warning",
  COMPLETED: "success",
  DRAFT: "secondary",
  PAUSED: "warning",
  CANCELLED: "destructive",
  CLOSED: "outline",
  PENDING: "warning",
  ACCEPTED: "success",
  REJECTED: "destructive",
  WITHDRAWN: "outline",
  EXPIRED: "outline",
  VERIFIED: "success",
  UNSUBMITTED: "secondary",
  ACTIVE: "success",
  SUSPENDED: "destructive",
  DELETED: "outline",
  OPEN: "warning",
  UNDER_REVIEW: "default",
  RESOLVED: "success",
};

export function StatusBadge({ status, showIcon = false }: StatusBadgeProps) {
  const { t } = useTranslation();
  const variant = VARIANT_MAP[status] || "secondary";
  const label = t(`statuses.${status}`, status);

  return (
    <Badge variant={variant}>
      {showIcon && status === "VERIFIED" && <ShieldCheck className="h-3.5 w-3.5" />}
      {showIcon && (status === "PENDING" || status === "UNDER_REVIEW") && <Clock className="h-3.5 w-3.5" />}
      {showIcon && (status === "ACCEPTED" || status === "COMPLETED" || status === "RESOLVED") && (
        <CheckCircle2 className="h-3.5 w-3.5" />
      )}
      {showIcon && (status === "REJECTED" || status === "CANCELLED") && <XCircle className="h-3.5 w-3.5" />}
      {showIcon && status === "SUSPENDED" && <Ban className="h-3.5 w-3.5" />}
      <span>{label}</span>
    </Badge>
  );
}
