import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

interface PaginationBarProps {
  currentPage: number;
  totalPages: number;
  count: number;
  onPageChange: (page: number) => void;
}

export function PaginationBar({ currentPage, totalPages, count, onPageChange }: PaginationBarProps) {
  const { t } = useTranslation();
  if (totalPages <= 1 && count === 0) return null;

  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
      <p className="text-sm text-muted-foreground">
        {t("common.pageInfo", { current: currentPage, total: Math.max(totalPages, 1), count })}
      </p>
      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
            {t("common.previous")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
          >
            {t("common.next")}
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
