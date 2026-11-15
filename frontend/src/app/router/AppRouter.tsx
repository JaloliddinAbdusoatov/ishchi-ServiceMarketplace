import { Suspense, lazy } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { DashboardLayout } from "@/app/layouts/DashboardLayout";
import { PublicLayout } from "@/app/layouts/PublicLayout";
import { ProtectedRoute } from "@/app/router/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const LandingPage = lazy(() =>
  import("@/features/marketplace/LandingPage").then((m) => ({ default: m.LandingPage }))
);
const MarketplacePage = lazy(() =>
  import("@/features/marketplace/MarketplacePage").then((m) => ({ default: m.MarketplacePage }))
);
const PaymentsPage = lazy(() =>
  import("@/features/marketplace/PaymentsPage").then((m) => ({ default: m.PaymentsPage }))
);
const OrderDetailPage = lazy(() =>
  import("@/features/orders/OrderDetailPage").then((m) => ({ default: m.OrderDetailPage }))
);
const WorkerPublicProfilePage = lazy(() =>
  import("@/features/workers/WorkerPublicProfilePage").then((m) => ({
    default: m.WorkerPublicProfilePage,
  }))
);

const LoginPage = lazy(() =>
  import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage }))
);
const RegisterPage = lazy(() =>
  import("@/features/auth/RegisterPage").then((m) => ({ default: m.RegisterPage }))
);
const OtpVerifyPage = lazy(() =>
  import("@/features/auth/OtpVerifyPage").then((m) => ({ default: m.OtpVerifyPage }))
);
const PasswordResetPage = lazy(() =>
  import("@/features/auth/PasswordResetPage").then((m) => ({ default: m.PasswordResetPage }))
);

const WorkerOverviewPage = lazy(() =>
  import("@/features/worker/WorkerOverviewPage").then((m) => ({ default: m.WorkerOverviewPage }))
);
const WorkerProfilePage = lazy(() =>
  import("@/features/worker/WorkerProfilePage").then((m) => ({ default: m.WorkerProfilePage }))
);
const WorkerCategoriesPage = lazy(() =>
  import("@/features/worker/WorkerCategoriesPage").then((m) => ({
    default: m.WorkerCategoriesPage,
  }))
);
const WorkerApplicationsPage = lazy(() =>
  import("@/features/worker/WorkerApplicationsPage").then((m) => ({
    default: m.WorkerApplicationsPage,
  }))
);
const WorkerInvitationsPage = lazy(() =>
  import("@/features/worker/WorkerInvitationsPage").then((m) => ({
    default: m.WorkerInvitationsPage,
  }))
);

const EmployerOverviewPage = lazy(() =>
  import("@/features/employer/EmployerOverviewPage").then((m) => ({
    default: m.EmployerOverviewPage,
  }))
);
const EmployerOrdersPage = lazy(() =>
  import("@/features/employer/EmployerOrdersPage").then((m) => ({
    default: m.EmployerOrdersPage,
  }))
);
const EmployerOrderFormPage = lazy(() =>
  import("@/features/employer/EmployerOrderFormPage").then((m) => ({
    default: m.EmployerOrderFormPage,
  }))
);
const EmployerApplicationsPage = lazy(() =>
  import("@/features/employer/EmployerApplicationsPage").then((m) => ({
    default: m.EmployerApplicationsPage,
  }))
);
const EmployerInvitationsPage = lazy(() =>
  import("@/features/employer/EmployerInvitationsPage").then((m) => ({
    default: m.EmployerInvitationsPage,
  }))
);
const EmployerProfilePage = lazy(() =>
  import("@/features/employer/EmployerProfilePage").then((m) => ({
    default: m.EmployerProfilePage,
  }))
);

const MessagesPage = lazy(() =>
  import("@/features/chat/MessagesPage").then((m) => ({ default: m.MessagesPage }))
);
const FavoritesPage = lazy(() =>
  import("@/features/favorites/FavoritesPage").then((m) => ({ default: m.FavoritesPage }))
);
const NotificationsPage = lazy(() =>
  import("@/features/notifications/NotificationsPage").then((m) => ({
    default: m.NotificationsPage,
  }))
);
const ReviewsPage = lazy(() =>
  import("@/features/reviews/ReviewsPage").then((m) => ({ default: m.ReviewsPage }))
);
const SettingsPage = lazy(() =>
  import("@/features/profile/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

const AdminOverviewPage = lazy(() =>
  import("@/features/admin/AdminOverviewPage").then((m) => ({ default: m.AdminOverviewPage }))
);
const AdminUsersPage = lazy(() =>
  import("@/features/admin/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage }))
);
const AdminVerificationPage = lazy(() =>
  import("@/features/admin/AdminVerificationPage").then((m) => ({
    default: m.AdminVerificationPage,
  }))
);
const AdminCategoriesPage = lazy(() =>
  import("@/features/admin/AdminCategoriesPage").then((m) => ({
    default: m.AdminCategoriesPage,
  }))
);
const AdminOrdersPage = lazy(() =>
  import("@/features/admin/AdminOrdersPage").then((m) => ({ default: m.AdminOrdersPage }))
);
const AdminReportsPage = lazy(() =>
  import("@/features/admin/AdminReportsPage").then((m) => ({ default: m.AdminReportsPage }))
);

function RouteLoadingFallback() {
  return (
    <div className="container py-10 space-y-4">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="container py-20 text-center space-y-4">
      <p className="text-6xl font-extrabold text-primary">404</p>
      <h1 className="text-2xl font-bold">{t("common.noData")}</h1>
      <Link to="/">
        <Button>{t("nav.home")}</Button>
      </Link>
    </div>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteLoadingFallback />}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route index element={<LandingPage />} />
            <Route path="/marketplace" element={<MarketplacePage />} />
            <Route path="/orders/:id" element={<OrderDetailPage />} />
            <Route path="/workers/:id" element={<WorkerPublicProfilePage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/verify-otp" element={<OtpVerifyPage />} />
            <Route path="/reset-password" element={<PasswordResetPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>

          <Route element={<ProtectedRoute requiredRole="WORKER" />}>
            <Route path="/worker" element={<DashboardLayout mode="WORKER" />}>
              <Route index element={<WorkerOverviewPage />} />
              <Route path="profile" element={<WorkerProfilePage />} />
              <Route path="categories" element={<WorkerCategoriesPage />} />
              <Route path="applications" element={<WorkerApplicationsPage />} />
              <Route path="invitations" element={<WorkerInvitationsPage />} />
              <Route path="favorites" element={<FavoritesPage />} />
              <Route path="reviews" element={<ReviewsPage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute requiredRole="EMPLOYER" />}>
            <Route path="/employer" element={<DashboardLayout mode="EMPLOYER" />}>
              <Route index element={<EmployerOverviewPage />} />
              <Route path="orders" element={<EmployerOrdersPage />} />
              <Route path="orders/new" element={<EmployerOrderFormPage />} />
              <Route path="orders/:id/edit" element={<EmployerOrderFormPage />} />
              <Route path="applications" element={<EmployerApplicationsPage />} />
              <Route path="find-workers" element={<MarketplacePage defaultTab="workers" />} />
              <Route path="invitations" element={<EmployerInvitationsPage />} />
              <Route path="favorites" element={<FavoritesPage />} />
              <Route path="reviews" element={<ReviewsPage />} />
              <Route path="profile" element={<EmployerProfilePage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute requiredRole="ADMIN" />}>
            <Route path="/admin" element={<DashboardLayout mode="ADMIN" />}>
              <Route index element={<AdminOverviewPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="verification" element={<AdminVerificationPage />} />
              <Route path="categories" element={<AdminCategoriesPage />} />
              <Route path="orders" element={<AdminOrdersPage />} />
              <Route path="reports" element={<AdminReportsPage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route path="/dashboard/messages" element={<MessagesPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
