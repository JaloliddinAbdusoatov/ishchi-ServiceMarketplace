import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CreditCard } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/shared/ErrorState";
import { systemApi } from "@/services/api";

export function PaymentsPage() {
  const { t } = useTranslation();
  const statusQuery = useQuery({ queryKey: ["payment-status"], queryFn: systemApi.paymentStatus });
  return (
    <div className="container max-w-2xl py-12">
      <Card>
        <CardHeader>
          <CreditCard className="h-8 w-8 text-muted-foreground" />
          <CardTitle>{t("payments.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="font-semibold">{t("payments.disabledBanner")}</p>
          <p className="text-muted-foreground">{t("payments.description")}</p>
          {statusQuery.isLoading ? <Skeleton className="h-6 w-32" /> : statusQuery.isError ? (
            <ErrorState onRetry={() => void statusQuery.refetch()} />
          ) : <p className="text-sm">{t("payments.backendStatusLabel")}: {statusQuery.data?.status}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
