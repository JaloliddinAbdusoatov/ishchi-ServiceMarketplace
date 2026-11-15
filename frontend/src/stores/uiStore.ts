import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SupportedLang = "uz" | "ru" | "en";

interface UIState {
  language: SupportedLang;
  darkMode: boolean;
  setLanguage: (lang: SupportedLang) => void;
  toggleDarkMode: () => void;
  setDarkMode: (dark: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      language: "uz",
      darkMode: false,
      setLanguage: (language) => set({ language }),
      toggleDarkMode: () =>
        set((state) => {
          const next = !state.darkMode;
          document.documentElement.classList.toggle("dark", next);
          return { darkMode: next };
        }),
      setDarkMode: (darkMode) => {
        document.documentElement.classList.toggle("dark", darkMode);
        set({ darkMode });
      },
    }),
    {
      name: "ishchi_ui",
      onRehydrateStorage: () => (state) => {
        if (state?.darkMode) {
          document.documentElement.classList.add("dark");
        }
      },
    }
  )
);
