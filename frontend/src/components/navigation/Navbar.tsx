import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Briefcase,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Shield,
  Sun,
  Users,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { UserAvatar } from "@/components/ui/avatar";
import { LanguageSwitcher } from "@/components/navigation/LanguageSwitcher";
import { NotificationBell } from "@/components/navigation/NotificationBell";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

export function Navbar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, refreshToken, activeWorkspace, setActiveWorkspace, clearSession } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();

  const handleLogout = async () => {
    try {
      await authApi.logout(refreshToken);
    } catch {
      // Clear local session regardless of server response
    } finally {
      setMobileOpen(false);
      clearSession();
      navigate("/login");
    }
  };

  const dashboardHref =
    user?.role === "ADMIN"
      ? "/admin"
      : activeWorkspace === "EMPLOYER"
        ? "/employer"
        : "/worker";

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-card/90 backdrop-blur-md">
      <div className="container flex min-h-16 flex-wrap items-center justify-between gap-2 py-2 sm:gap-4">
        <div className="flex items-center gap-6">
          <Link to="/" aria-label={t("brand.name")} className="flex shrink-0 items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-lg shadow-sm">
              I
            </div>
            <div className="hidden min-[360px]:block">
              <span className="text-lg font-extrabold tracking-tight text-foreground">
                {t("brand.name")}
              </span>
            </div>
          </Link>

          <nav className="hidden xl:flex items-center gap-1 text-sm font-medium">
            <NavLink
              to="/marketplace?tab=orders"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
            >
              <Briefcase className="h-4 w-4" />
              {t("nav.marketplace")}
            </NavLink>
            <NavLink
              to="/marketplace?tab=workers"
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Users className="h-4 w-4" />
              {t("nav.workers")}
            </NavLink>
            <NavLink
              to="/payments"
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
            >
              <CreditCard className="h-4 w-4" />
              {t("nav.payments")}
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          <LanguageSwitcher />

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleDarkMode}
            aria-label={darkMode ? t("common.lightMode") : t("common.darkMode")}
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          {user ? (
            <div className="hidden lg:flex items-center gap-2">
              {user.role !== "ADMIN" && user.is_worker && user.is_employer && (
                <div className="flex items-center rounded-lg border bg-muted p-0.5 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveWorkspace("WORKER");
                      navigate("/worker");
                    }}
                    className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                      activeWorkspace === "WORKER"
                        ? "bg-card text-foreground shadow-xs"
                        : "text-muted-foreground"
                    }`}
                  >
                    {t("nav.switchToWorker")}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveWorkspace("EMPLOYER");
                      navigate("/employer");
                    }}
                    className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                      activeWorkspace === "EMPLOYER"
                        ? "bg-card text-foreground shadow-xs"
                        : "text-muted-foreground"
                    }`}
                  >
                    {t("nav.switchToEmployer")}
                  </button>
                </div>
              )}

              <NotificationBell />

              <Link to={dashboardHref}>
                <Button variant="outline" size="sm" className="gap-2">
                  {user.role === "ADMIN" ? (
                    <Shield className="h-4 w-4 text-primary" />
                  ) : (
                    <LayoutDashboard className="h-4 w-4 text-primary" />
                  )}
                  <span className="max-w-[120px] truncate">{user.full_name || user.phone_number}</span>
                  <Badge variant="default" className="px-1.5 py-0 text-[10px]">
                    {user.role === "ADMIN" ? "ADMIN" : activeWorkspace}
                  </Badge>
                </Button>
              </Link>

              <Link to={dashboardHref} className="hidden lg:block">
                <UserAvatar name={user.full_name} className="h-8 w-8" />
              </Link>

              <Button variant="ghost" size="icon" onClick={handleLogout} title={t("nav.logout")}>
                <LogOut className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ) : (
            <div className="hidden lg:flex items-center gap-2">
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  {t("nav.login")}
                </Button>
              </Link>
              <Link to="/register">
                <Button size="sm">{t("nav.register")}</Button>
              </Link>
            </div>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="xl:hidden shrink-0"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={mobileOpen ? t("nav.closeMenu") : t("nav.openMenu")}
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <nav id="mobile-navigation" aria-label={t("nav.mainNavigation")} className="border-t bg-card px-4 py-4 xl:hidden space-y-2">
          <Link
            to="/marketplace?tab=orders"
            onClick={() => setMobileOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
          >
            {t("nav.marketplace")}
          </Link>
          <Link
            to="/marketplace?tab=workers"
            onClick={() => setMobileOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
          >
            {t("nav.workers")}
          </Link>
          <Link
            to="/payments"
            onClick={() => setMobileOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
          >
            {t("nav.payments")}
          </Link>
          <div className="border-t pt-2 space-y-2">
            {user ? (
              <>
                {user.role !== "ADMIN" && user.is_worker && user.is_employer && (
                  <div className="grid grid-cols-2 gap-2">
                    {(["WORKER", "EMPLOYER"] as const).map((workspace) => (
                      <Button key={workspace} type="button" variant={activeWorkspace === workspace ? "default" : "outline"}
                        aria-pressed={activeWorkspace === workspace}
                        onClick={() => {
                          setActiveWorkspace(workspace);
                          setMobileOpen(false);
                          navigate(workspace === "WORKER" ? "/worker" : "/employer");
                        }}>
                        {t(workspace === "WORKER" ? "nav.switchToWorker" : "nav.switchToEmployer")}
                      </Button>
                    ))}
                  </div>
                )}
                <Link
                  to={dashboardHref}
                  onClick={() => setMobileOpen(false)}
                  className="block rounded-lg bg-primary px-3 py-2 text-center text-sm font-medium text-primary-foreground"
                >
                  {t("nav.dashboard")}
                </Link>
                <Link
                  to="/notifications"
                  onClick={() => setMobileOpen(false)}
                  className="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted"
                >
                  {t("notifications.title")}
                </Link>
                <Button variant="outline" className="w-full" onClick={handleLogout}>
                  {t("nav.logout")}
                </Button>
              </>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Link to="/login" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full">
                    {t("nav.login")}
                  </Button>
                </Link>
                <Link to="/register" onClick={() => setMobileOpen(false)}>
                  <Button className="w-full">{t("nav.register")}</Button>
                </Link>
              </div>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
