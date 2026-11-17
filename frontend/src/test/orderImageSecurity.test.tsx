import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OrderImagePreview } from "@/components/shared/OrderImagePreview";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/stores/authStore";

afterEach(() => vi.unstubAllGlobals());

describe("Protected order images", () => {
  it("fetches through the API and revokes the displayed blob on unmount", async () => {
    const create = vi.fn(() => "blob:private-order-image");
    const revoke = vi.fn();
    vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: revoke });
    const get = vi.spyOn(apiClient, "get").mockResolvedValue({ data: new Blob(["image"]) });
    const view = render(<OrderImagePreview orderId="order-1" imageId="image-1" alt="Order image" />);
    await waitFor(() => expect(screen.getByAltText("Order image")).toHaveAttribute("src", "blob:private-order-image"));
    expect(get).toHaveBeenCalledWith("/orders/order-1/images/image-1/content/", expect.objectContaining({ responseType: "blob" }));
    view.unmount();
    expect(revoke).toHaveBeenCalledWith("blob:private-order-image");
  });

  it("clears private image data when the session changes and access is refused", async () => {
    const revoke = vi.fn();
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:private"), revokeObjectURL: revoke });
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({ data: new Blob(["private"]) })
      .mockRejectedValueOnce(new Error("Unauthorized"));
    render(<OrderImagePreview orderId="order-1" imageId="image-1" alt="Order image" />);
    await waitFor(() => expect(screen.getByAltText("Order image")).toHaveAttribute("src", "blob:private"));
    act(() => useAuthStore.getState().clearSession());
    await waitFor(() => expect(screen.getByAltText("Order image")).not.toHaveAttribute("src"));
    expect(revoke).toHaveBeenCalledWith("blob:private");
  });
});
