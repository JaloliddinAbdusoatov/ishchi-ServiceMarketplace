import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthTokens, UserSummary } from "@/types/api";

export type WorkspaceMode = "WORKER" | "EMPLOYER" | "ADMIN";

interface AuthState {
  sessionRevision: number;
  user: UserSummary | null;
  accessToken: string | null;
  refreshToken: string | null;
  activeWorkspace: WorkspaceMode;
  setSession: (user: UserSummary, tokens: AuthTokens) => void;
  setTokens: (access: string, refresh?: string) => void;
  setUser: (user: UserSummary) => void;
  setActiveWorkspace: (mode: WorkspaceMode) => void;
  clearSession: () => void;
}

function defaultWorkspaceForUser(user: UserSummary): WorkspaceMode {
  if (user.role === "ADMIN") return "ADMIN";
  if (user.role === "EMPLOYER" && user.is_employer) return "EMPLOYER";
  if (user.is_worker) return "WORKER";
  if (user.is_employer) return "EMPLOYER";
  return "WORKER";
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      sessionRevision: 0,
      accessToken: null,
      refreshToken: null,
      activeWorkspace: "WORKER",

      setSession: (user, tokens) =>
        set({
          user,
          sessionRevision: get().sessionRevision + 1,
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
          activeWorkspace: defaultWorkspaceForUser(user),
        }),

      setTokens: (access, refresh) =>
        set({
          accessToken: access,
          refreshToken: refresh ?? get().refreshToken,
        }),

      setUser: (user) => {
        const current = get().activeWorkspace;
        let next = current;
        if (user.role === "ADMIN") next = "ADMIN";
        else if (current === "WORKER" && !user.is_worker && user.is_employer) next = "EMPLOYER";
        else if (current === "EMPLOYER" && !user.is_employer && user.is_worker) next = "WORKER";
        set({ user, activeWorkspace: next });
      },

      setActiveWorkspace: (mode) => set({ activeWorkspace: mode }),

      clearSession: () =>
        set({
          sessionRevision: get().sessionRevision + 1,
          user: null,
          accessToken: null,
          refreshToken: null,
          activeWorkspace: "WORKER",
        }),
    }),
    {
      name: "ishchi_auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        activeWorkspace: state.activeWorkspace,
      }),
    }
  )
);
