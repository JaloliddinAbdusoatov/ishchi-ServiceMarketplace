import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/stores/authStore";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _sessionRevision?: number;
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.request.use(
  (config) => {
    const request = config as RetryableConfig;
    if (request._sessionRevision === undefined) request._sessionRevision = useAuthStore.getState().sessionRevision;
    if (request._sessionRevision !== useAuthStore.getState().sessionRevision) return Promise.reject(new Error("Session changed; request cancelled."));
    const token = useAuthStore.getState().accessToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => (response.config as RetryableConfig)._sessionRevision === useAuthStore.getState().sessionRevision
    ? response : Promise.reject(new Error("Session changed; response discarded.")),
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableConfig | undefined;
    if (!originalRequest) {
      return Promise.reject(error);
    }
    if (originalRequest._sessionRevision !== useAuthStore.getState().sessionRevision) return Promise.reject(error);

    const requestUrl = originalRequest.url || "";
    const isAuthEndpoint =
      requestUrl.includes("/auth/login/") ||
      requestUrl.includes("/auth/register/") ||
      requestUrl.includes("/auth/otp/") ||
      requestUrl.includes("/auth/token/refresh/") ||
      requestUrl.includes("/auth/password/reset/");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      const { refreshToken, setTokens, clearSession } = useAuthStore.getState();

      if (!refreshToken) {
        clearSession();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        originalRequest._retry = true;
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((newAccessToken) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          }
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshRes = await axios.post<{
          success: boolean;
          data: { access: string; refresh?: string };
        }>(`${BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        }, { timeout: 15000 });

        const { access, refresh } = refreshRes.data.data;
        if (useAuthStore.getState().refreshToken !== refreshToken || useAuthStore.getState().sessionRevision !== originalRequest._sessionRevision) {
          throw new Error("Session changed during refresh.");
        }
        setTokens(access, refresh);
        processQueue(null, access);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        if (useAuthStore.getState().refreshToken === refreshToken) clearSession();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
