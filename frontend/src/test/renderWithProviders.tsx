import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render } from "@testing-library/react";
import i18n from "@/i18n";

export function renderWithProviders(
  ui: ReactNode,
  { initialEntries = ["/"], routePath }: { initialEntries?: string[]; routePath?: string } = {}
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });

  const wrapped = routePath ? (
    <Routes>
      <Route path={routePath} element={ui} />
    </Routes>
  ) : (
    ui
  );

  return render(
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{wrapped}</MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );
}
