import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MarketplacePage } from "@/features/marketplace/MarketplacePage";
import { OrderDetailPage } from "@/features/orders/OrderDetailPage";
import {
  applicationsApi,
  categoriesApi,
  ordersApi,
  workersApi,
} from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { ServiceOrder, UserSummary } from "@/types/api";

const sampleOrder: ServiceOrder = {
  id: "ord-1",
  employer: "emp-1",
  employer_user_id: "emp-u1",
  employer_name: "Tashkent Build LLC",
  category: "cat-1",
  category_name: "Elektr montaj",
  assigned_worker: null,
  assigned_worker_user_id: null,
  assigned_worker_name: null,
  title: "Ofis elektr tarmog'ini montaj qilish",
  description: "200 kv.m ofis uchun elektr simlarini o'tkazish va shit yig'ish.",
  budget: "4500000.00",
  budget_type: "FIXED",
  location: "Toshkent",
  district: "Chilonzor",
  address: "Bunyodkor shoh ko'chasi",
  work_type: "ONSITE",
  deadline: null,
  start_date: null,
  status: "PUBLISHED",
  payment_status: "DISABLED",
  images: [],
  applications_count: 1,
  published_at: "2026-01-10T10:00:00Z",
  completed_at: null,
  created_at: "2026-01-10T10:00:00Z",
  updated_at: "2026-01-10T10:00:00Z",
};

const unverifiedWorker: UserSummary = {
  id: "w-u1",
  phone_number: "+998902223344",
  email: null,
  full_name: "Unverified Usta",
  role: "WORKER",
  has_worker_role: true,
  has_employer_role: false,
  is_worker: true,
  is_employer: false,
  is_verified_worker: false,
  worker_profile_id: "wp-unv",
  employer_profile_id: null,
  worker_verification_status: "PENDING",
  is_phone_verified: true,
  account_status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
};

const verifiedWorker: UserSummary = {
  ...unverifiedWorker,
  id: "w-u2",
  full_name: "Verified Usta",
  is_verified_worker: true,
  worker_profile_id: "wp-ver",
  worker_verification_status: "VERIFIED",
};

describe("Marketplace Filtering & Worker Application Workflow", () => {
  it("loads orders and workers tabs with API filter parameters", async () => {
    const user = userEvent.setup();
    vi.spyOn(categoriesApi, "list").mockResolvedValue({
      success: true,
      count: 1,
      total_pages: 1,
      current_page: 1,
      next: null,
      previous: null,
      results: [
        {
          id: "cat-1",
          parent: null,
          parent_name: null,
          slug: "elektr",
          name: "Elektr montaj",
          name_uz: "Elektr montaj",
          name_ru: "Электромонтаж",
          name_en: "Electrical",
          description: "",
          image: null,
          is_active: true,
          display_order: 1,
          children: [],
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
    });
    const ordersSpy = vi.spyOn(ordersApi, "list").mockResolvedValue({
      success: true,
      count: 1,
      total_pages: 1,
      current_page: 1,
      next: null,
      previous: null,
      results: [sampleOrder],
    });
    const workersSpy = vi.spyOn(workersApi, "list").mockResolvedValue({
      success: true,
      count: 0,
      total_pages: 1,
      current_page: 1,
      next: null,
      previous: null,
      results: [],
    });

    renderWithProviders(<MarketplacePage />, { initialEntries: ["/marketplace?tab=orders"] });

    expect(
      await screen.findByText("Ofis elektr tarmog'ini montaj qilish")
    ).toBeInTheDocument();
    expect(ordersSpy).toHaveBeenCalledWith(
      expect.objectContaining({ status: "PUBLISHED", page: 1 })
    );

    const searchInput = screen.getByPlaceholderText(
      "Xizmat, kasb yoki shahar bo'yicha qidiring..."
    );
    await user.type(searchInput, "Toshkent");

    await waitFor(() => {
      expect(ordersSpy).toHaveBeenCalledWith(
        expect.objectContaining({ search: "Toshkent" })
      );
    });

    await user.click(screen.getByRole("tab", { name: "Mutaxassislar" }));
    await waitFor(() => {
      expect(workersSpy).toHaveBeenCalled();
    });
  });

  it("allows both unverified and verified workers to submit applications (Optional KYC)", async () => {
    const user = userEvent.setup();
    vi.spyOn(ordersApi, "detail").mockResolvedValue(sampleOrder);
    vi.spyOn(applicationsApi, "list").mockResolvedValue({
      success: true,
      count: 0,
      total_pages: 1,
      current_page: 1,
      next: null,
      previous: null,
      results: [],
    });
    const createAppSpy = vi.spyOn(applicationsApi, "create").mockResolvedValue({
      id: "app-1",
      order: "ord-1",
      order_title: sampleOrder.title,
      order_status: "PUBLISHED",
      worker: "wp-unver",
      worker_name: "Unverified Usta",
      worker_rating: "0.00",
      worker_is_verified: false,
      cover_message: "Tajribam 7 yil, ertaga boshlay olaman.",
      proposed_price: "4200000.00",
      status: "PENDING",
      rejection_reason: "",
      responded_at: null,
      created_at: "2026-01-11T00:00:00Z",
      updated_at: "2026-01-11T00:00:00Z",
    });

    // 1. Unverified worker can fill and submit application directly (PDR-PRODUCT-14 / Option A)
    useAuthStore
      .getState()
      .setSession(unverifiedWorker, { access: "a1", refresh: "r1", token_type: "Bearer" });

    const { unmount } = renderWithProviders(<OrderDetailPage />, {
      initialEntries: ["/orders/ord-1"],
      routePath: "/orders/:id",
    });

    const priceInput = await screen.findByLabelText(/Taklif etilgan narx/i);
    const coverInput = screen.getByLabelText(/Murojaat xati/i);
    await user.type(priceInput, "4200000");
    await user.type(coverInput, "Tajribam 7 yil, ertaga boshlay olaman.");
    await user.click(screen.getByRole("button", { name: "Yuborish" }));

    await waitFor(() => {
      expect(createAppSpy).toHaveBeenCalledWith({
        order: "ord-1",
        proposed_price: "4200000",
        cover_message: "Tajribam 7 yil, ertaga boshlay olaman.",
      });
    });
    unmount();

    // 2. Verified worker can also fill and submit application
    createAppSpy.mockClear();
    useAuthStore
      .getState()
      .setSession(verifiedWorker, { access: "a2", refresh: "r2", token_type: "Bearer" });

    renderWithProviders(<OrderDetailPage />, {
      initialEntries: ["/orders/ord-1"],
      routePath: "/orders/:id",
    });

    const priceInput2 = await screen.findByLabelText(/Taklif etilgan narx/i);
    const coverInput2 = screen.getByLabelText(/Murojaat xati/i);
    await user.type(priceInput2, "4500000");
    await user.type(coverInput2, "Tajribam 10 yil, kafolat beraman.");
    await user.click(screen.getByRole("button", { name: "Yuborish" }));

    await waitFor(() => {
      expect(createAppSpy).toHaveBeenCalledWith({
        order: "ord-1",
        proposed_price: "4500000",
        cover_message: "Tajribam 10 yil, kafolat beraman.",
      });
    });
  });
});
