import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Briefcase,
  ExternalLink,
  Flag,
  Heart,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  Star,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { UserAvatar } from "@/components/ui/avatar";
import { ErrorState } from "@/components/shared/ErrorState";
import { ReportModal } from "@/components/shared/ReportModal";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  favoritesApi,
  invitationsApi,
  ordersApi,
  reviewsApi,
  workersApi,
} from "@/services/api";
import {
  extractApiErrorMessage,
  formatCurrencyUZS,
  formatDate,
  getLocalizedCategoryName,
  resolveMediaUrl,
} from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function WorkerPublicProfilePage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  const [inviteOpen, setInviteOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [selectedOrderId, setSelectedOrderId] = useState("");
  const [invMessage, setInvMessage] = useState("");
  const [invBudget, setInvBudget] = useState("");
  const [invDays, setInvDays] = useState("7");

  const workerQuery = useQuery({
    queryKey: ["worker", id],
    queryFn: () => workersApi.detail(id),
    enabled: Boolean(id),
  });

  const worker = workerQuery.data;

  const reviewsQuery = useQuery({
    queryKey: ["reviews", "worker", worker?.user_id],
    queryFn: () => reviewsApi.list({ reviewee: worker?.user_id, direction: "EMPLOYER_TO_WORKER" }),
    enabled: Boolean(worker?.user_id),
  });

  const myPublishedOrdersQuery = useQuery({
    queryKey: ["orders", "mine-published"],
    queryFn: () => ordersApi.list({ mine: true, status: "PUBLISHED", page_size: 50 }),
    enabled: Boolean(user?.is_employer && inviteOpen),
  });

  const favWorkersQuery = useQuery({
    queryKey: ["favorites", "workers"],
    queryFn: favoritesApi.listWorkers,
    enabled: Boolean(user),
  });

  const isFavorite = (favWorkersQuery.data?.results || []).some((f) => f.worker === id);

  const toggleFav = useMutation({
    mutationFn: async () => {
      if (isFavorite) return favoritesApi.removeWorker(id);
      return favoritesApi.addWorker(id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["favorites", "workers"] });
      toast.success(t("common.save"));
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      invitationsApi.send({
        order: selectedOrderId,
        worker: id,
        message: invMessage,
        proposed_budget: invBudget ? Number(invBudget) : null,
        expires_in_days: Number(invDays) || 7,
      }),
    onSuccess: () => {
      toast.success(t("marketplace.inviteWorker"));
      setInviteOpen(false);
      setInvMessage("");
      setInvBudget("");
      void queryClient.invalidateQueries({ queryKey: ["invitations"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (workerQuery.isLoading) {
    return (
      <div className="container py-8 space-y-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (workerQuery.isError || !worker) {
    return (
      <div className="container py-8">
        <ErrorState onRetry={() => void workerQuery.refetch()} />
      </div>
    );
  }

  const canInvite = Boolean(user?.is_employer && user.id !== worker.user_id);

  return (
    <div className="container py-8 space-y-6">
      {/* Top Profile Banner */}
      <Card className="p-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <UserAvatar src={worker.photo} name={worker.full_name} className="h-20 w-20 text-xl" />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold">{worker.full_name}</h1>
                <StatusBadge status={worker.verification_status} showIcon />
                {worker.is_available && (
                  <Badge variant="success">{t("worker.availabilityLabel")}</Badge>
                )}
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                  <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                  {Number(worker.rating_avg || 0).toFixed(1)} (
                  {t("marketplace.reviewsCount", { count: worker.review_count })})
                </span>
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {worker.location || "—"}
                  {worker.district ? `, ${worker.district}` : ""}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Briefcase className="h-4 w-4" />
                  {t("marketplace.yearsExp", { years: worker.experience_years })}
                </span>
                {worker.phone_number && (
                  <span className="inline-flex items-center gap-1">
                    <Phone className="h-4 w-4" />
                    {worker.phone_number}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {canInvite && (
              <Button onClick={() => setInviteOpen(true)} className="gap-2">
                <Mail className="h-4 w-4" />
                {t("marketplace.inviteWorker")}
              </Button>
            )}
            {user && (
              <>
                <Button variant="outline" onClick={() => toggleFav.mutate()} className="gap-2">
                  <Heart className={`h-4 w-4 ${isFavorite ? "fill-red-500 text-red-500" : ""}`} />
                  {isFavorite ? t("marketplace.removeFavorite") : t("marketplace.addFavorite")}
                </Button>
                {user.id !== worker.user_id && (
                  <Button variant="ghost" size="icon" onClick={() => setReportOpen(true)}>
                    <Flag className="h-4 w-4 text-muted-foreground" />
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("worker.bioLabel")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground whitespace-pre-line">
                {worker.bio || "—"}
              </p>
              {worker.experience_description && (
                <div>
                  <h4 className="text-sm font-semibold">{t("worker.experienceDescLabel")}</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {worker.experience_description}
                  </p>
                </div>
              )}
              {worker.skills?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">{t("worker.skillsLabel")}</h4>
                  <div className="flex flex-wrap gap-2">
                    {worker.skills.map((s) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Portfolio */}
          <Card>
            <CardHeader>
              <CardTitle>{t("worker.portfolioTitle")}</CardTitle>
            </CardHeader>
            <CardContent>
              {worker.portfolio_items.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {worker.portfolio_items.map((item) => (
                    <div key={item.id} className="rounded-xl border p-4 space-y-2">
                      {item.image && (
                        <img
                          src={resolveMediaUrl(item.image)}
                          alt={item.title}
                          className="h-36 w-full rounded-lg object-cover"
                        />
                      )}
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-sm">{item.title}</h4>
                        {item.completed_year && (
                          <Badge variant="outline">{item.completed_year}</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                      {item.project_url && (
                        <a
                          href={item.project_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Link
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Reviews */}
          <Card>
            <CardHeader>
              <CardTitle>{t("reviews.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              {(reviewsQuery.data?.results.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">{t("reviews.noReviews")}</p>
              ) : (
                <div className="space-y-4">
                  {reviewsQuery.data?.results.map((rev) => (
                    <div key={rev.id} className="rounded-xl border p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold">{rev.reviewer_name}</p>
                          <p className="text-xs text-muted-foreground">{rev.order_title}</p>
                        </div>
                        <div className="flex items-center gap-1 text-amber-500 font-semibold text-sm">
                          <Star className="h-4 w-4 fill-amber-400" />
                          {rev.rating}/5
                        </div>
                      </div>
                      {rev.comment && <p className="mt-2 text-sm text-muted-foreground">{rev.comment}</p>}
                      <p className="mt-2 text-[11px] text-muted-foreground">
                        {formatDate(rev.created_at, i18n.language)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Sidebar: Pricing & Categories */}
        <div className="space-y-6">
          <Card className="p-5 space-y-3">
            <h3 className="font-semibold">{t("marketplace.budgetType")}</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("worker.hourlyRateLabel")}</span>
                <span className="font-semibold">{formatCurrencyUZS(worker.hourly_rate)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("worker.fixedRateLabel")}</span>
                <span className="font-semibold">{formatCurrencyUZS(worker.fixed_rate_from)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("landing.statsCompleted")}</span>
                <span className="font-semibold">{worker.completed_orders_count}</span>
              </div>
            </div>
          </Card>

          <Card className="p-5 space-y-3">
            <h3 className="font-semibold flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              {t("nav.categories")}
            </h3>
            {worker.categories.length === 0 ? (
              <p className="text-xs text-muted-foreground">{t("common.noData")}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {worker.categories.map((cat) => (
                  <Badge key={cat.id} variant={cat.is_primary ? "default" : "secondary"}>
                    {getLocalizedCategoryName(cat, i18n.language)}
                    {cat.is_primary ? ` (${t("worker.primaryCategory")})` : ""}
                  </Badge>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Direct Invitation Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("marketplace.inviteWorker")}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!selectedOrderId) {
                toast.error(t("validation.requiredField"));
                return;
              }
              inviteMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label htmlFor="inv-order">{t("employer.selectOrderLabel")}</Label>
              <NativeSelect
                id="inv-order"
                value={selectedOrderId}
                onChange={(e) => setSelectedOrderId(e.target.value)}
                required
              >
                <option value="">-- {t("employer.selectOrderLabel")} --</option>
                {(myPublishedOrdersQuery.data?.results || []).map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.title} ({formatCurrencyUZS(o.budget)})
                  </option>
                ))}
              </NativeSelect>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="inv-budget">{t("employer.proposedBudgetLabel")}</Label>
                <Input
                  id="inv-budget"
                  type="number"
                  value={invBudget}
                  onChange={(e) => setInvBudget(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="inv-days">{t("employer.expiresDaysLabel")}</Label>
                <Input
                  id="inv-days"
                  type="number"
                  min={1}
                  max={60}
                  value={invDays}
                  onChange={(e) => setInvDays(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="inv-msg">{t("employer.invitationMsgLabel")}</Label>
              <Textarea
                id="inv-msg"
                value={invMessage}
                onChange={(e) => setInvMessage(e.target.value)}
                rows={3}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setInviteOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={inviteMutation.isPending}>
                {inviteMutation.isPending ? t("common.loading") : t("common.submit")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <ReportModal
        open={reportOpen}
        onOpenChange={setReportOpen}
        targetType="USER"
        targetId={worker.user_id}
      />
    </div>
  );
}
