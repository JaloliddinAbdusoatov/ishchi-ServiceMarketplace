import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <Card className="flex flex-col items-center justify-center border-red-200 bg-red-50/40 p-8 text-center dark:border-red-900 dark:bg-red-950/20">
      <AlertTriangle className="mb-2 h-8 w-8 text-destructive" />
      <p className="text-sm font-medium text-destructive">{message || t("common.errorOccurred")}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      )}
    </Card>
  );
}
