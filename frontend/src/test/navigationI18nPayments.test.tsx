import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Navbar } from "@/components/navigation/Navbar";
import { PaymentsPage } from "@/features/marketplace/PaymentsPage";
import { notificationsApi, systemApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { UserSummary } from "@/types/api";

const adminUser: UserSummary = {
  id: "adm-1",
  phone_number: "+998909999999",
  email: "admin@ishchi.uz",
  full_name: "System Admin",
  role: "ADMIN",
  has_worker_role: false,
  has_employer_role: false,
  is_worker: false,
  is_employer: false,
  is_verified_worker: false,
  worker_profile_id: null,
  employer_profile_id: null,
  worker_verification_status: null,
  is_phone_verified: true,
  account_status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
};

describe("Navigation, Trilingual i18n Switcher, and Disabled Payments Notice", () => {
  it("switches UI text dynamically between Uzbek, Russian, and English and renders Admin navbar items", async () => {
    const user = userEvent.setup();
    vi.spyOn(notificationsApi, "list").mockResolvedValue({
      success: true,
      count: 0,
      total_pages: 1,
      current_page: 1,
      next: null,
      previous: null,
      unread_count: 0,
      results: [],
    });

    useAuthStore
      .getState()
      .setSession(adminUser, { access: "a1", refresh: "r1", token_type: "Bearer" });

    renderWithProviders(<Navbar />);

    expect(screen.getByText("Buyurtmalar bozori")).toBeInTheDocument();
    expect(screen.getByText("System Admin")).toBeInTheDocument();
    expect(screen.getByText("ADMIN")).toBeInTheDocument();

    const langSelect = screen.getByLabelText("Til");
    await user.selectOptions(langSelect, "en");
    await waitFor(() => {
      expect(screen.getByText("Marketplace")).toBeInTheDocument();
      expect(screen.getByText("Specialists")).toBeInTheDocument();
      expect(screen.getByText("Payments")).toBeInTheDocument();
    });
    expect(useUIStore.getState().language).toBe("en");

    await user.selectOptions(screen.getByLabelText("Language"), "ru");
    await waitFor(() => {
      expect(screen.getByText("Биржа заказов")).toBeInTheDocument();
      expect(screen.getByText("Платежи")).toBeInTheDocument();
    });
    expect(useUIStore.getState().language).toBe("ru");
  });

  it("displays explicit Uzbek disabled payments notice with no card inputs", async () => {
    vi.spyOn(systemApi, "paymentStatus").mockResolvedValue({
      enabled: false,
      status: "DISABLED",
      message: "To'lov tizimi hozircha mavjud emas.",
    });

    renderWithProviders(<PaymentsPage />);

    expect(
      await screen.findByText("To'lov tizimi hozircha mavjud emas.")
    ).toBeInTheDocument();
    expect(await screen.findByText(/DISABLED/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
