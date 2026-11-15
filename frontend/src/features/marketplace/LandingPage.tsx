import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  CheckCircle2,
  FolderKanban,
  Layers,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  UserCheck,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { OrderCard } from "@/components/shared/OrderCard";
import { WorkerCard } from "@/components/shared/WorkerCard";
import { categoriesApi, ordersApi, systemApi, workersApi } from "@/services/api";
import { getLocalizedCategoryName } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

export function LandingPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"orders" | "workers">("orders");

  const statsQuery = useQuery({
    queryKey: ["public-stats"],
    queryFn: systemApi.stats,
  });

  const categoriesQuery = useQuery({
    queryKey: ["categories", "root"],
    queryFn: () => categoriesApi.list({ root_only: true, page_size: 8 }),
  });

  const workersQuery = useQuery({
    queryKey: ["workers", "featured"],
    queryFn: () => workersApi.list({ is_verified: true, ordering: "-rating_avg", page_size: 4 }),
  });

  const ordersQuery = useQuery({
    queryKey: ["orders", "recent"],
    queryFn: () => ordersApi.list({ status: "PUBLISHED", ordering: "-published_at", page_size: 4 }),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams({ tab: searchMode });
    if (searchQuery.trim()) params.set("search", searchQuery.trim());
    navigate(`/marketplace?${params.toString()}`);
  };

  const stats = statsQuery.data;

  return (
    <div>
      {/* 1 & 2. Hero + Working Search */}
      <section className="border-b bg-gradient-to-b from-primary/5 via-background to-background py-14 sm:py-20">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3.5 py-1 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              {t("landing.heroBadge")}
            </span>

            <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-foreground sm:text-5xl leading-tight">
              {t("landing.heroTitle")}
            </h1>

            <p className="mt-4 text-base text-muted-foreground sm:text-lg">
              {t("landing.heroSubtitle")}
            </p>

            {/* Primary CTAs */}
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              <Link to="/marketplace?tab=orders">
                <Button size="lg" className="gap-2 shadow-sm">
                  {t("landing.ctaFindWork")}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/marketplace?tab=workers">
                <Button size="lg" variant="outline" className="gap-2 bg-card">
                  {t("landing.ctaFindWorkers")}
                  <Users className="h-4 w-4" />
                </Button>
              </Link>
            </div>

            {/* 3. Functional Search Bar */}
            <form
              onSubmit={handleSearch}
              className="mx-auto mt-8 flex max-w-2xl flex-col gap-2 rounded-2xl border bg-card p-2 shadow-md sm:flex-row sm:items-center"
            >
              <div className="flex rounded-xl bg-muted p-1 text-xs font-medium shrink-0">
                <button
                  type="button"
                  onClick={() => setSearchMode("orders")}
                  className={`rounded-lg px-3 py-1.5 transition-colors ${
                    searchMode === "orders"
                      ? "bg-card text-foreground shadow-xs"
                      : "text-muted-foreground"
                  }`}
                >
                  {t("landing.searchModeOrders")}
                </button>
                <button
                  type="button"
                  onClick={() => setSearchMode("workers")}
                  className={`rounded-lg px-3 py-1.5 transition-colors ${
                    searchMode === "workers"
                      ? "bg-card text-foreground shadow-xs"
                      : "text-muted-foreground"
                  }`}
                >
                  {t("landing.searchModeWorkers")}
                </button>
              </div>

              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t("landing.searchPlaceholder")}
                  className="border-0 pl-9 shadow-none focus-visible:ring-0"
                />
              </div>

              <Button type="submit" className="shrink-0">
                {t("common.search")}
              </Button>
            </form>
          </div>
        </div>
      </section>

      {/* 8. Live Platform Statistics */}
      <section className="container -mt-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[
            {
              label: t("landing.statsWorkers"),
              value: stats?.total_workers,
              icon: Users,
              color: "text-primary",
            },
            {
              label: t("landing.statsVerified"),
              value: stats?.verified_workers,
              icon: UserCheck,
              color: "text-emerald-600",
            },
            {
              label: t("landing.statsOrders"),
              value: stats?.published_orders,
              icon: FolderKanban,
              color: "text-indigo-600",
            },
            {
              label: t("landing.statsCompleted"),
              value: stats?.completed_orders,
              icon: CheckCircle2,
              color: "text-amber-600",
            },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.label} className="flex items-center gap-3 p-4 shadow-sm">
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-muted ${stat.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {statsQuery.isLoading ? "—" : stat.value ?? 0}
                  </p>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* 4. Popular Categories */}
      <section className="container py-14">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              {t("landing.popularCategoriesTitle")}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("landing.popularCategoriesSubtitle")}
            </p>
          </div>
          <Link to="/marketplace?tab=orders" className="text-sm font-medium text-primary hover:underline">
            {t("common.viewAll")} →
          </Link>
        </div>

        {categoriesQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
        ) : categoriesQuery.isError ? (
          <ErrorState onRetry={() => void categoriesQuery.refetch()} />
        ) : categoriesQuery.data?.results.length === 0 ? (
          <EmptyState title={t("common.noData")} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(categoriesQuery.data?.results || []).map((cat) => (
              <Link key={cat.id} to={`/marketplace?tab=orders&category=${cat.id}`}>
                <Card className="h-full p-5 transition-all hover:border-primary/40 hover:shadow-md">
                  <div className="flex items-center justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Layers className="h-5 w-5" />
                    </div>
                    {cat.children?.length > 0 && (
                      <span className="text-xs font-medium text-muted-foreground">
                        {cat.children.length} sub
                      </span>
                    )}
                  </div>
                  <h3 className="mt-3 font-semibold text-foreground">
                    {getLocalizedCategoryName(cat, i18n.language)}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {cat.description}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* 5. How ISHCHI Works */}
      <section className="border-y bg-muted/40 py-14">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-bold tracking-tight">{t("landing.howItWorksTitle")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t("landing.howItWorksSubtitle")}</p>
          </div>

          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {[
              { title: t("landing.step1Title"), desc: t("landing.step1Desc") },
              { title: t("landing.step2Title"), desc: t("landing.step2Desc") },
              { title: t("landing.step3Title"), desc: t("landing.step3Desc") },
            ].map((step) => (
              <Card key={step.title} className="p-6">
                <h3 className="text-base font-semibold text-primary">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{step.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 6. Featured Verified Workers */}
      <section className="container py-14">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              {t("landing.featuredWorkersTitle")}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("landing.featuredWorkersSubtitle")}
            </p>
          </div>
          <Link to="/marketplace?tab=workers" className="text-sm font-medium text-primary hover:underline">
            {t("common.viewAll")} →
          </Link>
        </div>

        {workersQuery.isLoading ? (
          <div className="grid gap-5 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-52" />
            ))}
          </div>
        ) : workersQuery.isError ? (
          <ErrorState onRetry={() => void workersQuery.refetch()} />
        ) : workersQuery.data?.results.length === 0 ? (
          <EmptyState title={t("common.noData")} />
        ) : (
          <div className="grid gap-5 md:grid-cols-2">
            {(workersQuery.data?.results || []).map((worker) => (
              <WorkerCard key={worker.id} worker={worker} />
            ))}
          </div>
        )}
      </section>

      {/* 7. Recently Published Orders */}
      <section className="container pb-14">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{t("landing.recentOrdersTitle")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("landing.recentOrdersSubtitle")}
            </p>
          </div>
          <Link to="/marketplace?tab=orders" className="text-sm font-medium text-primary hover:underline">
            {t("common.viewAll")} →
          </Link>
        </div>

        {ordersQuery.isLoading ? (
          <div className="grid gap-5 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-52" />
            ))}
          </div>
        ) : ordersQuery.isError ? (
          <ErrorState onRetry={() => void ordersQuery.refetch()} />
        ) : ordersQuery.data?.results.length === 0 ? (
          <EmptyState title={t("common.noData")} />
        ) : (
          <div className="grid gap-5 md:grid-cols-2">
            {(ordersQuery.data?.results || []).map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        )}
      </section>

      {/* 9. Advantages of Using ISHCHI */}
      <section className="border-t bg-muted/30 py-14">
        <div className="container">
          <h2 className="text-center text-2xl font-bold tracking-tight">
            {t("landing.advantagesTitle")}
          </h2>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { icon: ShieldCheck, title: t("landing.adv1Title"), desc: t("landing.adv1Desc") },
              { icon: Lock, title: t("landing.adv2Title"), desc: t("landing.adv2Desc") },
              { icon: Users, title: t("landing.adv3Title"), desc: t("landing.adv3Desc") },
              { icon: Star, title: t("landing.adv4Title"), desc: t("landing.adv4Desc") },
            ].map((adv) => {
              const Icon = adv.icon;
              return (
                <Card key={adv.title} className="p-5">
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-semibold">{adv.title}</h3>
                  <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">{adv.desc}</p>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* 10. CTA Banner */}
      <section className="container pt-12">
        <div className="rounded-2xl bg-primary px-6 py-10 text-center text-primary-foreground shadow-lg sm:px-12">
          <h2 className="text-2xl font-bold sm:text-3xl">{t("landing.ctaBannerTitle")}</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-primary-foreground/85">
            {t("landing.ctaBannerSubtitle")}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {!user ? (
              <>
                <Link to="/register">
                  <Button size="lg" variant="secondary">
                    {t("nav.register")}
                  </Button>
                </Link>
                <Link to="/login">
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10"
                  >
                    {t("nav.login")}
                  </Button>
                </Link>
              </>
            ) : (
              <Link to="/marketplace">
                <Button size="lg" variant="secondary">
                  {t("nav.marketplace")}
                </Button>
              </Link>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
