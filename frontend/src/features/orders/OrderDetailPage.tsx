import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Briefcase,
  Calendar,
  CheckCircle2,
  CreditCard,
  Flag,
  MapPin,
  MessageSquare,
  ShieldCheck,
  Star,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/shared/ErrorState";
import { ReportModal } from "@/components/shared/ReportModal";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { applicationsApi, chatApi, ordersApi, reviewsApi } from "@/services/api";
import { extractApiErrorMessage, formatCurrencyUZS, formatDate } from "@/lib/utils";
import { OrderImagePreview } from "@/components/shared/OrderImagePreview";
import { useAuthStore } from "@/stores/authStore";

export function OrderDetailPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  const [coverMessage, setCoverMessage] = useState("");
  const [proposedPrice, setProposedPrice] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [reportOpen, setReportOpen] = useState(false);

  const orderQuery = useQuery({
    queryKey: ["order", id],
    queryFn: () => ordersApi.detail(id),
    enabled: Boolean(id),
  });

  const order = orderQuery.data;
  const isOwner = Boolean(user && order && user.id === order.employer_user_id);

  // Fetch relevant applications if authenticated (employer sees order applicants; worker sees own application)
  const appsQuery = useQuery({
    queryKey: ["applications", "order", id],
    queryFn: () => applicationsApi.list({ order: id, page_size: 50 }),
    enabled: Boolean(user && id),
  });

  // Backend-confirmed review eligibility (never guess review form visibility purely on client!)
  const reviewEligibilityQuery = useQuery({
    queryKey: ["review-eligibility", id],
    queryFn: () => reviewsApi.eligibility(id),
    enabled: Boolean(user && order && order.status === "COMPLETED"),
  });

  const orderReviewsQuery = useQuery({
    queryKey: ["reviews", "order", id],
    queryFn: () => reviewsApi.list({ order: id }),
    enabled: Boolean(order && order.status === "COMPLETED"),
  });

  const myApplication = (appsQuery.data?.results || []).find(
    (a) => a.worker === user?.worker_profile_id
  );

  const invalidateOrderGraph = () => {
    void queryClient.invalidateQueries({ queryKey: ["order", id] });
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
    void queryClient.invalidateQueries({ queryKey: ["orders"] });
    void queryClient.invalidateQueries({ queryKey: ["review-eligibility", id] });
  };

  const applyMutation = useMutation({
    mutationFn: () =>
      applicationsApi.create({
        order: id,
        cover_message: coverMessage,
        proposed_price: proposedPrice,
      }),
    onSuccess: () => {
      toast.success(t("marketplace.applyNow"));
      setCoverMessage("");
      setProposedPrice("");
      invalidateOrderGraph();
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const withdrawMutation = useMutation({
    mutationFn: (appId: string) => applicationsApi.withdraw(appId),
    onSuccess: () => {
      toast.success(t("worker.withdrawBtn"));
      invalidateOrderGraph();
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const acceptAppMutation = useMutation({
    mutationFn: (appId: string) => applicationsApi.accept(appId),
    onSuccess: () => {
      toast.success(t("employer.acceptApplicantBtn"));
      invalidateOrderGraph();
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const rejectAppMutation = useMutation({
    mutationFn: (appId: string) => applicationsApi.reject(appId, ""),
    onSuccess: () => {
      toast.success(t("employer.rejectApplicantBtn"));
      invalidateOrderGraph();
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const statusActionMutation = useMutation({
    mutationFn: async (action: "publish" | "pause" | "cancel" | "close" | "complete") => {
      if (action === "publish") return ordersApi.publish(id);
      if (action === "pause") return ordersApi.pause(id);
      if (action === "cancel") return ordersApi.cancel(id);
      if (action === "close") return ordersApi.close(id);
      return ordersApi.complete(id);
    },
    onSuccess: () => {
      toast.success(t("common.save"));
      invalidateOrderGraph();
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const openChatMutation = useMutation({
    mutationFn: (workerId?: string) => chatApi.openConversation({ order: id, worker: workerId }),
    onSuccess: (conv) => {
      navigate(`/dashboard/messages?conversation=${conv.id}`);
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  const submitReviewMutation = useMutation({
    mutationFn: () =>
      reviewsApi.create({
        order: id,
        rating: reviewRating,
        comment: reviewComment,
        reviewee: reviewEligibilityQuery.data?.reviewee_id,
      }),
    onSuccess: () => {
      toast.success(t("reviews.submitReviewBtn"));
      setReviewComment("");
      void queryClient.invalidateQueries({ queryKey: ["review-eligibility", id] });
      void queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
    onError: (err) => toast.error(extractApiErrorMessage(err)),
  });

  if (orderQuery.isLoading) {
    return (
      <div className="container py-8 space-y-4">
        <Skeleton className="h-44" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (orderQuery.isError || !order) {
    return (
      <div className="container py-8">
        <ErrorState
          message={extractApiErrorMessage(orderQuery.error)}
          onRetry={() => void orderQuery.refetch()}
        />
      </div>
    );
  }

  const canWorkerChat =
    Boolean(myApplication && ["PENDING", "ACCEPTED"].includes(myApplication.status));

  return (
    <div className="container py-8 space-y-6">
      <Card className="p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{order.category_name}</Badge>
              <StatusBadge status={order.status} showIcon />
              <Badge variant="outline" className="gap-1">
                <CreditCard className="h-3 w-3" />
                Payment: {order.payment_status}
              </Badge>
            </div>
            <h1 className="text-2xl font-bold">{order.title}</h1>
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-4 w-4 text-primary" />
                {order.location}
                {order.district ? `, ${order.district}` : ""}
              </span>
              <span className="inline-flex items-center gap-1">
                <Briefcase className="h-4 w-4 text-primary" />
                {t(`statuses.${order.work_type}`, order.work_type)}
              </span>
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-4 w-4 text-primary" />
                {formatDate(order.published_at || order.created_at, i18n.language)}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-start lg:items-end gap-2">
            <div className="text-2xl font-extrabold text-primary">
              {formatCurrencyUZS(order.budget)}
            </div>
            <span className="text-xs text-muted-foreground">
              {t(`statuses.${order.budget_type}`, order.budget_type)} • {order.employer_name}
            </span>
            <div className="flex flex-wrap gap-2 pt-1">
              {!isOwner && user?.is_worker && canWorkerChat && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => openChatMutation.mutate(undefined)}
                  className="gap-1.5"
                >
                  <MessageSquare className="h-4 w-4" />
                  {t("employer.openChatBtn")}
                </Button>
              )}
              {user && !isOwner && (
                <Button size="sm" variant="ghost" onClick={() => setReportOpen(true)}>
                  <Flag className="h-4 w-4 mr-1" />
                  {t("reports.reportBtn")}
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("employer.orderDescLabel")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-foreground/90 whitespace-pre-line">{order.description}</p>
              {order.address && (
                <p className="text-xs text-muted-foreground">
                  <strong>{t("employer.addressLabel")}:</strong> {order.address}
                </p>
              )}
              {order.images?.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-3 pt-2">
                  {order.images.map((img) => (
                    <OrderImagePreview
                      key={img.id}
                      orderId={order.id}
                      imageId={img.id}
                      alt={img.caption || order.title}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Employer Management Controls + Applicants List */}
          {isOwner && (
            <Card>
              <CardHeader>
                <CardTitle>{t("employer.dashboardTitle")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex flex-wrap gap-2">
                  {(order.status === "DRAFT" || order.status === "PAUSED") && (
                    <Button
                      size="sm"
                      onClick={() => statusActionMutation.mutate("publish")}
                      disabled={statusActionMutation.isPending}
                    >
                      {t("employer.publishBtn")}
                    </Button>
                  )}
                  {order.status === "PUBLISHED" && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => statusActionMutation.mutate("pause")}
                      disabled={statusActionMutation.isPending}
                    >
                      {t("employer.pauseBtn")}
                    </Button>
                  )}
                  {(order.status === "IN_PROGRESS" || (order.status === "PUBLISHED" && (order.hired_worker_count ?? 0) > 0)) && (
                    <Button
                      size="sm"
                      variant="success"
                      onClick={() => statusActionMutation.mutate("complete")}
                      disabled={statusActionMutation.isPending}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {t("employer.completeOrderBtn")}
                    </Button>
                  )}
                  {!["COMPLETED", "CANCELLED", "CLOSED"].includes(order.status) && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => statusActionMutation.mutate("close")}
                        disabled={statusActionMutation.isPending}
                      >
                        {t("employer.closeBtn")}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => statusActionMutation.mutate("cancel")}
                        disabled={statusActionMutation.isPending}
                      >
                        {t("employer.cancelOrderBtn")}
                      </Button>
                    </>
                  )}
                  {(order.status === "DRAFT" || order.status === "PUBLISHED" || order.status === "PAUSED") && (
                    <Link to={`/employer/orders/${order.id}/edit`}>
                      <Button size="sm" variant="secondary">
                        {t("common.edit")}
                      </Button>
                    </Link>
                  )}
                </div>

                {/* Applicants to this order */}
                <div className="border-t pt-4 space-y-3">
                  <h4 className="font-semibold text-sm">
                    {t("nav.applications")} ({appsQuery.data?.count ?? 0})
                  </h4>
                  {(appsQuery.data?.results.length ?? 0) === 0 ? (
                    <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
                  ) : (
                    <div className="space-y-3">
                      {appsQuery.data?.results.map((app) => (
                        <div
                          key={app.id}
                          className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Link
                                to={`/workers/${app.worker}`}
                                className="font-semibold text-sm hover:text-primary hover:underline"
                              >
                                {app.worker_name}
                              </Link>
                              {app.worker_is_verified && (
                                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                              )}
                              <StatusBadge status={app.status} />
                            </div>
                            <p className="text-xs font-medium text-primary">
                              {formatCurrencyUZS(app.proposed_price)}
                            </p>
                            <p className="text-xs text-muted-foreground">{app.cover_message}</p>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {["PENDING", "ACCEPTED"].includes(app.status) && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openChatMutation.mutate(app.worker)}
                              >
                                <MessageSquare className="h-3.5 w-3.5" />
                                {t("employer.openChatBtn")}
                              </Button>
                            )}
                            {app.status === "PENDING" && order.status === "PUBLISHED" && (
                              <>
                                <Button
                                  size="sm"
                                  variant="success"
                                  disabled={acceptAppMutation.isPending}
                                  onClick={() => acceptAppMutation.mutate(app.id)}
                                >
                                  <CheckCircle2 className="h-3.5 w-3.5" />
                                  {t("employer.acceptApplicantBtn")}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  disabled={rejectAppMutation.isPending}
                                  onClick={() => rejectAppMutation.mutate(app.id)}
                                >
                                  <XCircle className="h-3.5 w-3.5" />
                                  {t("employer.rejectApplicantBtn")}
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Reviews & Backend-confirmed Review Form */}
          {order.status === "COMPLETED" && (
            <Card>
              <CardHeader>
                <CardTitle>{t("reviews.title")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {user && reviewEligibilityQuery.data?.eligible && (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      submitReviewMutation.mutate();
                    }}
                    className="rounded-xl border bg-accent/40 p-4 space-y-3"
                  >
                    <h4 className="font-semibold text-sm">{t("reviews.leaveReviewTitle")}</h4>
                    {reviewEligibilityQuery.data?.reviewee_name && <p>{reviewEligibilityQuery.data.reviewee_name}</p>}
                    <div className="space-y-1.5">
                      <Label htmlFor="rev-rating">{t("reviews.ratingLabel")} (1–5)</Label>
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            onClick={() => setReviewRating(star)}
                            className="p-1"
                            aria-label={t("reviews.rateStars", { count: star })}
                          >
                            <Star
                              className={`h-6 w-6 ${
                                star <= reviewRating
                                  ? "fill-amber-400 text-amber-400"
                                  : "text-muted-foreground"
                              }`}
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="rev-comment">{t("reviews.commentLabel")}</Label>
                      <Textarea
                        id="rev-comment"
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        rows={3}
                      />
                    </div>
                    <Button type="submit" disabled={submitReviewMutation.isPending}>
                      {submitReviewMutation.isPending
                        ? t("common.loading")
                        : t("reviews.submitReviewBtn")}
                    </Button>
                  </form>
                )}

                {(orderReviewsQuery.data?.results.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground">{t("reviews.noReviews")}</p>
                ) : (
                  <div className="space-y-3">
                    {orderReviewsQuery.data?.results.map((r) => (
                      <div key={r.id} className="rounded-xl border p-4">
                        <div className="flex justify-between">
                          <span className="font-semibold text-sm">
                            {r.reviewer_name} → {r.reviewee_name}
                          </span>
                          <span className="inline-flex items-center gap-1 text-sm font-semibold text-amber-500">
                            <Star className="h-4 w-4 fill-amber-400" />
                            {r.rating}/5
                          </span>
                        </div>
                        {r.comment && <p className="mt-1.5 text-sm text-muted-foreground">{r.comment}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Worker Application Panel */}
        <div className="space-y-6">
          {!user ? (
            <Card className="p-5 space-y-3">
              <h3 className="font-semibold">{t("marketplace.applyNow")}</h3>
              <p className="text-sm text-muted-foreground">{t("auth.loginSubtitle")}</p>
              <Link to="/login">
                <Button className="w-full">{t("nav.login")}</Button>
              </Link>
            </Card>
          ) : (
            user.is_worker &&
            !isOwner && (
              <Card className="p-5 space-y-4">
                <h3 className="font-semibold">{t("marketplace.applyNow")}</h3>

                {myApplication ? (
                  <div className="space-y-3 rounded-xl border bg-muted/40 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">
                        {t("common.status")}
                      </span>
                      <StatusBadge status={myApplication.status} showIcon />
                    </div>
                    <p className="text-sm font-semibold">
                      {formatCurrencyUZS(myApplication.proposed_price)}
                    </p>
                    <p className="text-xs text-muted-foreground">{myApplication.cover_message}</p>
                    {myApplication.status === "PENDING" && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        disabled={withdrawMutation.isPending}
                        onClick={() => withdrawMutation.mutate(myApplication.id)}
                      >
                        {t("worker.withdrawBtn")}
                      </Button>
                    )}
                  </div>
                ) : order.status !== "PUBLISHED" ? (
                  <p className="text-sm text-muted-foreground">
                    {t(`statuses.${order.status}`, order.status)}
                  </p>
                ) : (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (coverMessage.trim().length < 5) {
                        toast.error(t("validation.minChars", { min: 5 }));
                        return;
                      }
                      if (!proposedPrice || Number(proposedPrice) <= 0) {
                        toast.error(t("validation.positiveNumber"));
                        return;
                      }
                      applyMutation.mutate();
                    }}
                    className="space-y-3"
                  >
                    <div className="space-y-1.5">
                      <Label htmlFor="app-price">{t("worker.proposedPriceLabel")}</Label>
                      <Input
                        id="app-price"
                        type="number"
                        value={proposedPrice}
                        onChange={(e) => setProposedPrice(e.target.value)}
                        placeholder={order.budget}
                        required
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="app-cover">{t("worker.coverMessageLabel")}</Label>
                      <Textarea
                        id="app-cover"
                        value={coverMessage}
                        onChange={(e) => setCoverMessage(e.target.value)}
                        rows={4}
                        required
                      />
                    </div>
                    <Button type="submit" className="w-full" disabled={applyMutation.isPending}>
                      {applyMutation.isPending ? t("common.loading") : t("common.submit")}
                    </Button>
                  </form>
                )}
              </Card>
            )
          )}

          {(order.team?.length ?? 0) > 0 && (
            <Card className="p-5 space-y-2">
              <p>{t("employer.capacityLabel", { defaultValue: "Hired workers" })}: {order.hired_worker_count}/{order.capacity}</p>
              {order.team?.map((worker) => <Link key={worker.id} className="block text-primary" to={`/workers/${worker.id}`}>{worker.name}</Link>)}
            </Card>
          )}
          {!order.team?.length && order.assigned_worker_name && (
            <Card className="p-5 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                {t("auth.roleWorker")}
              </p>
              <Link
                to={`/workers/${order.assigned_worker}`}
                className="font-semibold text-primary hover:underline"
              >
                {order.assigned_worker_name}
              </Link>
            </Card>
          )}
        </div>
      </div>

      <ReportModal
        open={reportOpen}
        onOpenChange={setReportOpen}
        targetType="ORDER"
        targetId={order.id}
      />
    </div>
  );
}
