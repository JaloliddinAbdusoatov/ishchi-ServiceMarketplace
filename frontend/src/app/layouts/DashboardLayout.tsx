import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Bell,
  Briefcase,
  FileText,
  Flag,
  FolderKanban,
  Heart,
  LayoutDashboard,
  Mail,
  MessageSquare,
  PlusCircle,
  Search,
  Settings,
  ShieldCheck,
  Star,
  Tag,
  UserCheck,
  UserCog,
  Users,
} from "lucide-react";
import { Navbar } from "@/components/navigation/Navbar";
import { useAuthStore, type WorkspaceMode } from "@/stores/authStore";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
}

export function DashboardLayout({ mode }: { mode?: WorkspaceMode }) {
  const { t } = useTranslation();
  const { user, activeWorkspace } = useAuthStore();
  const effectiveMode: WorkspaceMode =
    mode ?? (user?.role === "ADMIN" ? "ADMIN" : activeWorkspace);

  const workerNav: NavItem[] = [
    { to: "/worker", label: t("nav.dashboard"), icon: LayoutDashboard, end: true },
    { to: "/worker/profile", label: t("nav.profile"), icon: UserCog },
    { to: "/worker/categories", label: t("nav.categories"), icon: Tag },
    { to: "/marketplace?tab=orders", label: t("nav.browseOrders"), icon: Search },
    { to: "/worker/applications", label: t("nav.applications"), icon: FileText },
    { to: "/worker/invitations", label: t("nav.invitations"), icon: Mail },
    { to: "/dashboard/messages", label: t("nav.messages"), icon: MessageSquare },
    { to: "/worker/favorites", label: t("nav.favorites"), icon: Heart },
    { to: "/worker/reviews", label: t("nav.reviews"), icon: Star },
    { to: "/notifications", label: t("nav.notifications"), icon: Bell },
    { to: "/settings", label: t("nav.settings"), icon: Settings },
  ];

  const employerNav: NavItem[] = [
    { to: "/employer", label: t("nav.dashboard"), icon: LayoutDashboard, end: true },
    { to: "/employer/orders", label: t("nav.myOrders"), icon: FolderKanban },
    { to: "/employer/orders/new", label: t("nav.createOrder"), icon: PlusCircle },
    { to: "/employer/applications", label: t("nav.applications"), icon: FileText },
    { to: "/employer/find-workers", label: t("nav.findWorkers"), icon: Users },
    { to: "/employer/invitations", label: t("nav.invitations"), icon: Mail },
    { to: "/dashboard/messages", label: t("nav.messages"), icon: MessageSquare },
    { to: "/employer/favorites", label: t("nav.favorites"), icon: Heart },
    { to: "/employer/reviews", label: t("nav.reviews"), icon: Star },
    { to: "/employer/profile", label: t("nav.profile"), icon: UserCog },
    { to: "/notifications", label: t("nav.notifications"), icon: Bell },
    { to: "/settings", label: t("nav.settings"), icon: Settings },
  ];

  const adminNav: NavItem[] = [
    { to: "/admin", label: t("nav.adminOverview"), icon: LayoutDashboard, end: true },
    { to: "/admin/users", label: t("nav.adminUsers"), icon: Users },
    { to: "/admin/verification", label: t("nav.adminVerification"), icon: UserCheck },
    { to: "/admin/categories", label: t("nav.adminCategories"), icon: Tag },
    { to: "/admin/orders", label: t("nav.adminOrders"), icon: Briefcase },
    { to: "/admin/reports", label: t("nav.adminReports"), icon: Flag },
    { to: "/settings", label: t("nav.settings"), icon: Settings },
  ];

  const navItems =
    effectiveMode === "ADMIN" ? adminNav : effectiveMode === "EMPLOYER" ? employerNav : workerNav;

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="container flex-1 py-6">
        <div className="flex flex-col gap-6 lg:flex-row">
          <aside className="w-full shrink-0 lg:w-64">
            <div className="rounded-xl border bg-card p-3 shadow-sm sticky top-20">
              <div className="mb-3 flex items-center gap-2 border-b px-3 pb-3">
                <ShieldCheck className="h-4 w-4 text-primary" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{user?.full_name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {effectiveMode === "ADMIN"
                      ? "ADMIN"
                      : effectiveMode === "EMPLOYER"
                        ? t("auth.roleEmployer")
                        : t("auth.roleWorker")}
                  </p>
                </div>
              </div>

              <nav className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) =>
                        `flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                          isActive
                            ? "bg-primary text-primary-foreground shadow-xs"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          </aside>

          <main className="min-w-0 flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
