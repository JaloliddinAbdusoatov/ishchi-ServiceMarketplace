import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axios, { AxiosError } from "axios";
import { PaymentsPage } from "@/features/marketplace/PaymentsPage";
import { MessagesPage } from "@/features/chat/MessagesPage";
import { chatApi } from "@/services/api";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/stores/authStore";
import { renderWithProviders } from "@/test/renderWithProviders";
import type { ApiPaginatedResponse, UserSummary } from "@/types/api";

afterEach(() => { vi.restoreAllMocks(); useAuthStore.getState().clearSession(); });

describe("teacher-demo finish sprint", () => {
  it("marks incoming messages read once without a request loop when the page rerenders", async () => {
    useAuthStore.setState({ user: { id: "worker-user", worker_profile_id: "worker" } as UserSummary });
    const page = <T,>(results: T[]): ApiPaginatedResponse<T> => ({ success: true, count: results.length, total_pages: 1, current_page: 1, next: null, previous: null, results });
    const conversations = vi.spyOn(chatApi, "listConversations").mockResolvedValue(page([{
      id: "conv", order: "order", order_title: "Synthetic order", employer: "employer", employer_name: "Synthetic employer",
      worker: "worker", worker_name: "Synthetic worker", last_message_at: null, unread_count: 1, last_message: null, created_at: "2026-11-14T10:00:00Z",
    }]));
    vi.spyOn(chatApi, "listMessages").mockResolvedValue(page([{
      id: "message", conversation: "conv", sender_id: "employer-user", sender_name: "Synthetic employer", content: "Synthetic work update",
      attachment: null, is_read: false, read_at: null, created_at: "2026-11-14T10:00:00Z",
    }]));
    const markRead = vi.spyOn(chatApi, "markRead").mockImplementation(() => new Promise(() => {}))
      .mockResolvedValueOnce({ marked_read_count: 1 });
    renderWithProviders(<MessagesPage />, { initialEntries: ["/dashboard/messages?conversation=conv"] });
    await screen.findByText("Synthetic work update");
    await waitFor(() => expect(conversations).toHaveBeenCalledTimes(2));
    await userEvent.type(screen.getByRole("textbox"), "A synthetic reply");
    expect(markRead).toHaveBeenCalledTimes(1);
  });

  it("shows payments unavailable without submission controls or card details", async () => {
    const adapter = apiClient.defaults.adapter;
    apiClient.defaults.adapter = async (config) => ({ config, status: 200, statusText: "OK", headers: {}, data: { success: true, data: { enabled: false, status: "DISABLED" } } });
    try {
      renderWithProviders(<PaymentsPage />);
      expect(await screen.findByText(/DISABLED/)).toBeInTheDocument();
      expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Preview|Pay|Submit/i })).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/card number|CVV/i)).not.toBeInTheDocument();
    } finally { apiClient.defaults.adapter = adapter; }
  });

  it("does not restore tokens when an old refresh finishes after logout", async () => {
    const adapter = apiClient.defaults.adapter;
    useAuthStore.setState({ accessToken: "expired-access", refreshToken: "old-refresh" });
    let finish!: (value: unknown) => void;
    const refresh = vi.spyOn(axios, "post").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    apiClient.defaults.adapter = async (config) => {
      throw new AxiosError("Expired", "ERR_BAD_REQUEST", config, {}, { config, status: 401, statusText: "Unauthorized", headers: {}, data: {} });
    };
    try {
      const pending = apiClient.get("/profiles/worker/").catch((error: unknown) => error);
      await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
      useAuthStore.getState().clearSession();
      finish({ data: { success: true, data: { access: "stale-access", refresh: "stale-refresh" } } });
      await pending;
      expect(useAuthStore.getState().accessToken).toBeNull();
      expect(useAuthStore.getState().refreshToken).toBeNull();
    } finally { apiClient.defaults.adapter = adapter; }
  });
});
