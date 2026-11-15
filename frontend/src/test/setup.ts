import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import i18n from "@/i18n";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverMock;
Element.prototype.scrollIntoView = vi.fn();

beforeEach(async () => {
  useAuthStore.getState().clearSession();
  useUIStore.getState().setLanguage("uz");
  await i18n.changeLanguage("uz");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
