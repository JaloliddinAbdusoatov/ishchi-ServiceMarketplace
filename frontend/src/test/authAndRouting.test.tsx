import { Route, Routes } from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "@/app/router/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { OtpVerifyPage } from "@/features/auth/OtpVerifyPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { UserSummary } from "@/types/api";

const baseUser: UserSummary = {
  id: "u-1",
  phone_number: "+998901234567",
  email: "worker@example.com",
  full_name: "Test Worker",
  role: "WORKER",
  has_worker_role: true,
  has_employer_role: false,
  is_worker: true,
  is_employer: false,
  is_verified_worker: true,
  worker_profile_id: "wp-1",
  employer_profile_id: null,
  worker_verification_status: "VERIFIED",
  is_phone_verified: true,
  account_status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
};

describe("Authentication Forms & Role-Based Routing", () => {
  it("validates phone format and required password on LoginPage", async () => {
    const user = userEvent.setup();
    const loginSpy = vi.spyOn(authApi, "login");

    renderWithProviders(<LoginPage />);

    const phoneInput = screen.getByLabelText("Telefon raqami");
    await user.clear(phoneInput);
    await user.type(phoneInput, "+99812");
    await user.click(screen.getByRole("button", { name: "Kirish" }));

    expect(
      await screen.findByText("Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak")
    ).toBeInTheDocument();
    expect(screen.getByText("Ushbu maydon to'ldirilishi shart")).toBeInTheDocument();
    expect(loginSpy).not.toHaveBeenCalled();
  });

  it("logs in via authApi and stores session + tokens", async () => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "login").mockResolvedValue({
      success: true,
      message: "Signed in",
      data: {
        user: baseUser,
        tokens: { access: "acc-1", refresh: "ref-1", token_type: "Bearer" },
      },
    });

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/worker" element={<div>Worker Workspace</div>} />
      </Routes>,
      { initialEntries: ["/login"] }
    );

    const phoneInput = screen.getByLabelText("Telefon raqami");
    await user.clear(phoneInput);
    await user.type(phoneInput, "+998901234567");
    await user.type(screen.getByLabelText("Parol"), "DemoPass123!");
    await user.click(screen.getByRole("button", { name: "Kirish" }));

    await waitFor(() => {
      expect(screen.getByText("Worker Workspace")).toBeInTheDocument();
    });
    expect(useAuthStore.getState().accessToken).toBe("acc-1");
    expect(useAuthStore.getState().user?.id).toBe("u-1");
  });

  it("validates matching passwords and dual-role company toggle on RegisterPage", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />);

    await user.type(screen.getByLabelText("To'liq ism-familiya"), "Ali Valiyev");
    const phoneInput = screen.getByLabelText("Telefon raqami");
    await user.clear(phoneInput);
    await user.type(phoneInput, "+998901112233");
    await user.type(screen.getByLabelText("Parol"), "Password123!");
    await user.type(screen.getByLabelText("Parolni tasdiqlang"), "Different123!");

    await user.selectOptions(screen.getByLabelText("Asosiy rolingiz"), "EMPLOYER");
    await user.selectOptions(screen.getByLabelText("Buyurtmachi turi"), "COMPANY");
    expect(screen.getByLabelText("Kompaniya nomi")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ro'yxatdan o'tish" }));
    expect(await screen.findByText("Parollar mos kelmadi")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login and blocks unauthorized roles in ProtectedRoute", async () => {
    // 1. Unauthenticated redirect
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<div>Login Screen</div>} />
        <Route element={<ProtectedRoute requiredRole="WORKER" />}>
          <Route path="/worker" element={<div>Worker Panel</div>} />
        </Route>
      </Routes>,
      { initialEntries: ["/worker"] }
    );
    expect(screen.getByText("Login Screen")).toBeInTheDocument();

    // 2. Worker blocked from Admin route
    useAuthStore
      .getState()
      .setSession(baseUser, { access: "acc-1", refresh: "ref-1", token_type: "Bearer" });

    renderWithProviders(
      <Routes>
        <Route path="/worker" element={<div>Worker Redirected</div>} />
        <Route element={<ProtectedRoute requiredRole="ADMIN" />}>
          <Route path="/admin" element={<div>Admin Secret</div>} />
        </Route>
      </Routes>,
      { initialEntries: ["/admin"] }
    );
    expect(screen.getByText("Worker Redirected")).toBeInTheDocument();
    expect(screen.queryByText("Admin Secret")).not.toBeInTheDocument();
  });
  it.each(["WORKER", "EMPLOYER"] as const)("registers %s and opens its dashboard without SMS verification", async (role) => {
    const user = userEvent.setup();
    vi.spyOn(authApi, "register").mockResolvedValue({ success: true, data: {
      user: { ...baseUser, role, is_phone_verified: false, is_worker: role === "WORKER", is_employer: role === "EMPLOYER" },
      tokens: { access: "registered-access", refresh: "registered-refresh", token_type: "Bearer" },
    }});
    const otpSpy = vi.spyOn(authApi, "sendOtp");
    renderWithProviders(<Routes>
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-otp" element={<div>Phone verification required</div>} />
      <Route element={<ProtectedRoute requiredRole={role} />}>
        <Route path={role === "WORKER" ? "/worker" : "/employer"} element={<div>Registered dashboard</div>} />
      </Route>
    </Routes>, { initialEntries: ["/register"] });
    await user.type(screen.getByLabelText("To'liq ism-familiya"), "Ali Valiyev");
    await user.clear(screen.getByLabelText("Telefon raqami"));
    await user.type(screen.getByLabelText("Telefon raqami"), "+998901234567");
    await user.selectOptions(screen.getByLabelText("Asosiy rolingiz"), role);
    await user.type(screen.getByLabelText("Parol"), "Password123!");
    await user.type(screen.getByLabelText("Parolni tasdiqlang"), "Password123!");
    await user.click(screen.getByRole("button", { name: "Ro'yxatdan o'tish" }));
    expect(await screen.findByText("Registered dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Phone verification required")).not.toBeInTheDocument();
    expect(useAuthStore.getState().accessToken).toBe("registered-access");
    expect(useAuthStore.getState().user?.is_phone_verified).toBe(false);
    expect(otpSpy).not.toHaveBeenCalled();
  });

  it("verifies the signed-in phone while preserving the existing session", async () => {
    const user = userEvent.setup();
    useAuthStore.getState().setSession(baseUser, {
      access: "existing-access", refresh: "existing-refresh", token_type: "Bearer",
    });
    vi.spyOn(authApi, "verifyOtp").mockResolvedValue({ success: true, data: {
      user: { ...baseUser, is_phone_verified: true },
    }});
    renderWithProviders(<Routes>
      <Route path="/verify-otp" element={<OtpVerifyPage />} />
      <Route path="/worker" element={<div>Activated worker</div>} />
    </Routes>, { initialEntries: ["/verify-otp"] });
    const inputs = screen.getAllByRole("textbox");
    expect(inputs[0]).toHaveAttribute("readonly");
    await user.type(inputs[1], "654321");
    await user.click(screen.getAllByRole("button")[0]);
    expect(await screen.findByText("Activated worker")).toBeInTheDocument();
    expect(useAuthStore.getState().refreshToken).toBe("existing-refresh");
    expect(useAuthStore.getState().accessToken).toBe("existing-access");
    expect(useAuthStore.getState().user?.is_phone_verified).toBe(true);
  });

});
