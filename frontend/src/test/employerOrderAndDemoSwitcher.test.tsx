import { Route, Routes } from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "@/features/auth/LoginPage";
import { EmployerOrderFormPage } from "@/features/employer/EmployerOrderFormPage";
import { authApi, categoriesApi, ordersApi } from "@/services/api";
import { renderWithProviders } from "@/test/renderWithProviders";

describe("Employer orders and real login", () => {
  it("validates required order fields and submits valid order payload", async () => {
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
          id: "cat-elec",
          parent: null,
          parent_name: null,
          slug: "elektr-ishlari",
          name: "Elektr montaj ishlari",
          name_uz: "Elektr montaj ishlari",
          name_ru: "Электромонтаж",
          name_en: "Electrical Works",
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

    const createOrderSpy = vi.spyOn(ordersApi, "create").mockResolvedValue({
      id: "ord-new-1",
      employer: "ep-1",
      employer_user_id: "emp-u1",
      employer_name: "Azizbek Karimov",
      category: "cat-elec",
      category_name: "Elektr montaj ishlari",
      assigned_worker: null,
      assigned_worker_user_id: null,
      assigned_worker_name: null,
      title: "Yangi ofis elektr montaji",
      description: "To'liq elektr simlarini almashtirish va rozetkalar o'rnatish.",
      budget: "1500000.00",
      budget_type: "FIXED",
      location: "Toshkent",
      district: "Chilonzor",
      address: "",
      work_type: "ONSITE",
      deadline: null,
      start_date: null,
      status: "PUBLISHED",
      payment_status: "DISABLED",
      images: [],
      applications_count: 0,
      published_at: "2026-01-12T00:00:00Z",
      completed_at: null,
      created_at: "2026-01-12T00:00:00Z",
      updated_at: "2026-01-12T00:00:00Z",
    });

    renderWithProviders(
      <Routes>
        <Route path="/employer/orders/new" element={<EmployerOrderFormPage />} />
        <Route path="/orders/:id" element={<div>Created Order Detail</div>} />
      </Routes>,
      { initialEntries: ["/employer/orders/new"] }
    );

    expect(await screen.findByText("Elektr montaj ishlari")).toBeInTheDocument();

    // Empty submit triggers validation without hitting API
    await user.click(screen.getByRole("button", { name: "Saqlash" }));
    expect(createOrderSpy).not.toHaveBeenCalled();

    await user.selectOptions(screen.getByLabelText("Kategoriya"), "cat-elec");
    await user.type(screen.getByLabelText("Buyurtma sarlavhasi"), "Yangi ofis elektr montaji");
    await user.type(
      screen.getByLabelText("Batafsil tavsif"),
      "To'liq elektr simlarini almashtirish va rozetkalar o'rnatish."
    );
    await user.type(screen.getByLabelText("Byudjet (UZS)"), "1500000");

    await user.click(screen.getByRole("button", { name: "Saqlash" }));

    await waitFor(() => {
      expect(createOrderSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          category: "cat-elec",
          title: "Yangi ofis elektr montaji",
          budget: "1500000.00",
        })
      );
    });
    expect(await screen.findByText("Created Order Detail")).toBeInTheDocument();
  });

  it("never offers synthetic account shortcuts, even when a legacy flag is enabled", () => {
    vi.stubEnv("VITE_ENABLE_DEMO_SWITCHER", "true");
    const loginSpy = vi.spyOn(authApi, "login");
    renderWithProviders(<LoginPage />);
    expect(screen.getByLabelText("Parol")).toHaveValue("");
    expect(screen.getByLabelText("Telefon raqami")).toHaveValue("+998");
    expect(screen.queryByText(/Demo|Quick Login|Azizbek|Admin/i)).not.toBeInTheDocument();
    expect(loginSpy).not.toHaveBeenCalled();
    vi.unstubAllEnvs();
  });
});
