import { useEffect, useMemo, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { Toaster } from "sonner";
import i18n from "@/i18n";
import { AppErrorBoundary } from "@/components/shared/AppErrorBoundary";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

function AuthSessionSync() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const darkMode = useUIStore((s) => s.darkMode);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    authApi
      .me()
      .then((freshUser) => {
        if (active) setUser(freshUser);
      })
      .catch(() => {
        // Interceptor clears invalid sessions if refresh fails
      });
    return () => {
      active = false;
    };
  }, [accessToken, setUser]);

  return null;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const sessionRevision = useAuthStore((s) => s.sessionRevision);
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }), [sessionRevision]
  );
  useEffect(() => () => { void queryClient.cancelQueries(); queryClient.clear(); }, [queryClient]);

  return (
    <AppErrorBoundary>
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          <AuthSessionSync />
          {children}
          <Toaster richColors position="top-right" closeButton />
        </QueryClientProvider>
      </I18nextProvider>
    </AppErrorBoundary>
  );
}
