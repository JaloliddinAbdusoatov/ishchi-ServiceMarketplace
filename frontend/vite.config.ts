import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (mode === "production") {
    // Same-origin is the safe default; cross-origin deployment requires an explicit
    // process environment, never the local .env.
    const configured = process.env.VITE_API_BASE_URL || "/api/v1";
    if (!configured.startsWith("/api/") && !configured.startsWith("https://")) {
      throw new Error("Production API URL must use HTTPS or /api/.");
    }
    env.VITE_API_BASE_URL = configured;
    env.VITE_MEDIA_BASE_URL = process.env.VITE_MEDIA_BASE_URL || "";
  }
  return {
    define: mode === "production" ? {
      "import.meta.env.VITE_API_BASE_URL": JSON.stringify(env.VITE_API_BASE_URL),
      "import.meta.env.VITE_MEDIA_BASE_URL": JSON.stringify(env.VITE_MEDIA_BASE_URL),
    } : {},
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      host: "127.0.0.1",
      proxy: {
        "/api": "http://127.0.0.1:8001",
        "/media": "http://127.0.0.1:8001",
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom", "react-router-dom", "zustand"],
            query: ["@tanstack/react-query", "axios"],
            charts: ["recharts"],
            i18n: ["i18next", "react-i18next"],
          },
        },
      },
    },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      css: true,
    },
  };
});
