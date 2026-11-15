
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore, type WorkspaceMode } from "@/stores/authStore";

interface ProtectedRouteProps {
  requiredRole?: WorkspaceMode;
}

export function ProtectedRoute({ requiredRole }: ProtectedRouteProps) {
  const location = useLocation();
  const { user, accessToken } = useAuthStore();

  if (!user || !accessToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.account_status !== "ACTIVE") {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole === "ADMIN" && user.role !== "ADMIN") {
    return <Navigate to={user.is_employer ? "/employer" : "/worker"} replace />;
  }

  if (requiredRole === "WORKER" && !user.is_worker) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/employer"} replace />;
  }

  if (requiredRole === "EMPLOYER" && !user.is_employer) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/worker"} replace />;
  }

  return <Outlet />;
}
