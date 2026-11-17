import { apiClient } from "@/services/apiClient";
import type {
  AdminDashboardStats,
  ApiPaginatedResponse,
  ApiSuccessResponse,
  AuthTokens,
  Category,
  ChatMessage,
  Conversation,
  EmployerDashboardStats,
  EmployerProfile,
  FavoriteOrder,
  FavoriteWorker,
  NotificationItem,
  OrderApplication,
  OrderImage,
  OrderInvitation,
  PublicPlatformStats,
  ReportItem,
  ReportReason,
  ReportStatus,
  ReportTargetType,
  Review,
  ReviewEligibility,
  ServiceOrder,
  UserSummary,
  WorkerDashboardStats,
  WorkerPortfolioItem,
  WorkerProfile,
} from "@/types/api";

export const systemApi = {
  health: async () => {
    const res = await apiClient.get<{
      success: boolean;
      service: string;
      version: string;
      database: { status: string; name: string; version: string };
      redis: { status: string };
      payments_enabled: boolean;
    }>("/health/");
    return res.data;
  },
  stats: async () => {
    const res = await apiClient.get<ApiSuccessResponse<PublicPlatformStats>>("/stats/");
    return res.data.data;
  },
  paymentStatus: async () => {
    const res = await apiClient.get<
      ApiSuccessResponse<{ enabled: boolean; status: string; message: string }>
    >("/payments/status/");
    return res.data.data;
  },
};

export const authApi = {
  register: async (payload: {
    phone_number: string;
    password: string;
    full_name: string;
    role: "WORKER" | "EMPLOYER";
    email?: string | null;
    enable_worker?: boolean;
    enable_employer?: boolean;
    employer_type?: "INDIVIDUAL" | "COMPANY";
    company_name?: string;
    location?: string;
    district?: string;
  }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ user: UserSummary; tokens: AuthTokens }>
    >("/auth/register/", payload);
    return res.data;
  },
  login: async (payload: { phone_number: string; password: string }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ user: UserSummary; tokens: AuthTokens }>
    >("/auth/login/", payload);
    return res.data;
  },
  logout: async (refresh?: string | null) => {
    const res = await apiClient.post<ApiSuccessResponse<null>>(
      "/auth/logout/",
      refresh ? { refresh } : {}
    );
    return res.data;
  },
  logoutAll: async () => {
    const res = await apiClient.post<ApiSuccessResponse<null>>("/auth/logout-all/", {});
    return res.data;
  },
  me: async () => {
    const res = await apiClient.get<ApiSuccessResponse<UserSummary>>("/auth/me/");
    return res.data.data;
  },
  updateMe: async (payload: { full_name?: string; email?: string | null }) => {
    const res = await apiClient.patch<ApiSuccessResponse<UserSummary>>("/auth/me/", payload);
    return res.data.data;
  },
  sendOtp: async (payload: { phone_number: string; purpose: "VERIFY_PHONE" | "PASSWORD_RESET" }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ cooldown_seconds: number; expires_in_seconds: number }>
    >("/auth/otp/send/", payload);
    return res.data;
  },
  resendOtp: async (payload: { phone_number: string; purpose: "VERIFY_PHONE" | "PASSWORD_RESET" }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ cooldown_seconds: number; expires_in_seconds: number }>
    >("/auth/otp/resend/", payload);
    return res.data;
  },
  verifyOtp: async (payload: { phone_number: string; otp: string }) => {
    const res = await apiClient.post<ApiSuccessResponse<{ user: UserSummary }>>(
      "/auth/otp/verify/",
      payload
    );
    return res.data;
  },
  changePassword: async (payload: { old_password: string; new_password: string }) => {
    const res = await apiClient.post<ApiSuccessResponse<null>>("/auth/password/change/", payload);
    return res.data;
  },
  requestPasswordReset: async (payload: { phone_number: string }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ cooldown_seconds: number; expires_in_seconds: number }>
    >("/auth/password/reset/request/", payload);
    return res.data;
  },
  confirmPasswordReset: async (payload: {
    phone_number: string;
    otp: string;
    new_password: string;
  }) => {
    const res = await apiClient.post<ApiSuccessResponse<null>>(
      "/auth/password/reset/confirm/",
      payload
    );
    return res.data;
  },
  enableRole: async (payload: {
    role: "WORKER" | "EMPLOYER";
    employer_type?: "INDIVIDUAL" | "COMPANY";
    company_name?: string;
  }) => {
    const res = await apiClient.post<ApiSuccessResponse<UserSummary>>(
      "/auth/enable-role/",
      payload
    );
    return res.data.data;
  },
  deleteAccount: async (payload: { password: string; confirm: boolean; reason?: string }) => {
    const res = await apiClient.post<
      ApiSuccessResponse<{ audit_id: string; anonymized_at: string }>
    >("/auth/delete-account/", payload);
    return res.data;
  },
};

export const categoriesApi = {
  list: async (params?: Record<string, string | number | boolean | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<Category>>("/categories/", { params });
    return res.data;
  },
  detail: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<Category>>(`/categories/${id}/`);
    return res.data.data;
  },
  create: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post<ApiSuccessResponse<Category>>("/categories/", payload);
    return res.data.data;
  },
  update: async (id: string, payload: Record<string, unknown>) => {
    const res = await apiClient.patch<ApiSuccessResponse<Category>>(`/categories/${id}/`, payload);
    return res.data.data;
  },
  deactivate: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<Category>>(`/categories/${id}/deactivate/`);
    return res.data.data;
  },
  remove: async (id: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(`/categories/${id}/`);
    return res.data;
  },
};

export const profilesApi = {
  getMyWorkerProfile: async () => {
    const res = await apiClient.get<ApiSuccessResponse<WorkerProfile>>("/profiles/worker/");
    return res.data.data;
  },
  updateMyWorkerProfile: async (payload: FormData | Record<string, unknown>) => {
    const isForm = payload instanceof FormData;
    const res = await apiClient.patch<ApiSuccessResponse<WorkerProfile>>(
      "/profiles/worker/",
      payload,
      isForm ? { headers: { "Content-Type": "multipart/form-data" } } : undefined
    );
    return res.data.data;
  },
  requestWorkerVerification: async (notes: string) => {
    const res = await apiClient.post<ApiSuccessResponse<WorkerProfile>>(
      "/profiles/worker/verification-request/",
      { notes }
    );
    return res.data.data;
  },
  getMyWorkerCategories: async () => {
    const res = await apiClient.get<ApiSuccessResponse<WorkerProfile["categories"]>>(
      "/profiles/worker/categories/"
    );
    return res.data.data;
  },
  updateMyWorkerCategories: async (
    categories: Array<{ category_id: string; is_primary: boolean; experience_years?: number | null }>
  ) => {
    const res = await apiClient.put<ApiSuccessResponse<WorkerProfile["categories"]>>(
      "/profiles/worker/categories/",
      { categories }
    );
    return res.data.data;
  },
  listMyPortfolio: async () => {
    const res = await apiClient.get<ApiSuccessResponse<WorkerPortfolioItem[]>>(
      "/profiles/worker/portfolio/"
    );
    return res.data.data;
  },
  createPortfolioItem: async (payload: FormData | Record<string, unknown>) => {
    const isForm = payload instanceof FormData;
    const res = await apiClient.post<ApiSuccessResponse<WorkerPortfolioItem>>(
      "/profiles/worker/portfolio/",
      payload,
      isForm ? { headers: { "Content-Type": "multipart/form-data" } } : undefined
    );
    return res.data.data;
  },
  deletePortfolioItem: async (itemId: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(
      `/profiles/worker/portfolio/${itemId}/`
    );
    return res.data;
  },
  getMyEmployerProfile: async () => {
    const res = await apiClient.get<ApiSuccessResponse<EmployerProfile>>("/profiles/employer/");
    return res.data.data;
  },
  updateMyEmployerProfile: async (payload: FormData | Record<string, unknown>) => {
    const isForm = payload instanceof FormData;
    const res = await apiClient.patch<ApiSuccessResponse<EmployerProfile>>(
      "/profiles/employer/",
      payload,
      isForm ? { headers: { "Content-Type": "multipart/form-data" } } : undefined
    );
    return res.data.data;
  },
};

export const workersApi = {
  list: async (params?: Record<string, string | number | boolean | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<WorkerProfile>>("/workers/", { params });
    return res.data;
  },
  detail: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<WorkerProfile>>(`/workers/${id}/`);
    return res.data.data;
  },
  employerDetail: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<EmployerProfile>>(`/employers/${id}/`);
    return res.data.data;
  },
};

export const ordersApi = {
  list: async (params?: Record<string, string | number | boolean | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<ServiceOrder>>("/orders/", { params });
    return res.data;
  },
  detail: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/`);
    return res.data.data;
  },
  create: async (payload: Record<string, unknown>) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>("/orders/", payload);
    return res.data.data;
  },
  update: async (id: string, payload: Record<string, unknown>) => {
    const res = await apiClient.patch<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/`, payload);
    return res.data.data;
  },
  remove: async (id: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(`/orders/${id}/`);
    return res.data;
  },
  publish: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/publish/`);
    return res.data.data;
  },
  pause: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/pause/`);
    return res.data.data;
  },
  cancel: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/cancel/`);
    return res.data.data;
  },
  close: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/close/`);
    return res.data.data;
  },
  complete: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(`/orders/${id}/complete/`);
    return res.data.data;
  },
  uploadImage: async (orderId: string, file: File, caption = "") => {
    const formData = new FormData();
    formData.append("image", file);
    if (caption) formData.append("caption", caption);
    const res = await apiClient.post<ApiSuccessResponse<OrderImage>>(
      `/orders/${orderId}/images/`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return res.data.data;
  },
  deleteImage: async (orderId: string, imageId: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(
      `/orders/${orderId}/images/${imageId}/`
    );
    return res.data;
  },
};

export const applicationsApi = {
  list: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<OrderApplication>>("/applications/", {
      params,
    });
    return res.data;
  },
  detail: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<OrderApplication>>(`/applications/${id}/`);
    return res.data.data;
  },
  create: async (payload: { order: string; cover_message: string; proposed_price: number | string }) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderApplication>>(
      "/applications/",
      payload
    );
    return res.data.data;
  },
  withdraw: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderApplication>>(
      `/applications/${id}/withdraw/`
    );
    return res.data.data;
  },
  accept: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderApplication>>(
      `/applications/${id}/accept/`
    );
    return res.data.data;
  },
  reject: async (id: string, reason = "") => {
    const res = await apiClient.post<ApiSuccessResponse<OrderApplication>>(
      `/applications/${id}/reject/`,
      { reason }
    );
    return res.data.data;
  },
};

export const invitationsApi = {
  list: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<OrderInvitation>>("/invitations/", {
      params,
    });
    return res.data;
  },
  send: async (payload: {
    order: string;
    worker: string;
    message?: string;
    proposed_budget?: number | string | null;
    expires_in_days?: number;
  }) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderInvitation>>(
      "/invitations/",
      payload
    );
    return res.data.data;
  },
  accept: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderInvitation>>(
      `/invitations/${id}/accept/`
    );
    return res.data.data;
  },
  reject: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderInvitation>>(
      `/invitations/${id}/reject/`
    );
    return res.data.data;
  },
  cancel: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<OrderInvitation>>(
      `/invitations/${id}/cancel/`
    );
    return res.data.data;
  },
};

export const chatApi = {
  listConversations: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<Conversation>>("/chat/conversations/", {
      params,
    });
    return res.data;
  },
  openConversation: async (payload: { order: string; worker?: string }) => {
    const res = await apiClient.post<ApiSuccessResponse<Conversation>>(
      "/chat/conversations/",
      payload
    );
    return res.data.data;
  },
  getConversation: async (id: string) => {
    const res = await apiClient.get<ApiSuccessResponse<Conversation>>(
      `/chat/conversations/${id}/`
    );
    return res.data.data;
  },
  listMessages: async (id: string, params?: Record<string, string | number | boolean | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<ChatMessage>>(
      `/chat/conversations/${id}/messages/`,
      { params }
    );
    return res.data;
  },
  sendMessage: async (conversationId: string, payload: { content?: string; attachment?: File | null }) => {
    if (payload.attachment) {
      const formData = new FormData();
      if (payload.content) formData.append("content", payload.content);
      formData.append("attachment", payload.attachment);
      const res = await apiClient.post<ApiSuccessResponse<ChatMessage>>(
        `/chat/conversations/${conversationId}/messages/`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return res.data.data;
    }
    const res = await apiClient.post<ApiSuccessResponse<ChatMessage>>(
      `/chat/conversations/${conversationId}/messages/`,
      { content: payload.content || "" }
    );
    return res.data.data;
  },
  markRead: async (conversationId: string) => {
    const res = await apiClient.post<ApiSuccessResponse<{ marked_read_count: number }>>(
      `/chat/conversations/${conversationId}/read/`
    );
    return res.data.data;
  },
};

export const reviewsApi = {
  list: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<Review>>("/reviews/", { params });
    return res.data;
  },
  eligibility: async (orderId: string) => {
    const res = await apiClient.get<ApiSuccessResponse<ReviewEligibility>>(
      "/reviews/eligibility/",
      { params: { order: orderId } }
    );
    return res.data.data;
  },
  create: async (payload: { order: string; rating: number; comment?: string; reviewee?: string }) => {
    const res = await apiClient.post<ApiSuccessResponse<Review>>("/reviews/", payload);
    return res.data.data;
  },
};

export const notificationsApi = {
  list: async (params?: Record<string, string | number | boolean | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<NotificationItem>>("/notifications/", {
      params,
    });
    return res.data;
  },
  markRead: async (id: string) => {
    const res = await apiClient.post<ApiSuccessResponse<NotificationItem>>(
      `/notifications/${id}/read/`
    );
    return res.data.data;
  },
  markAllRead: async () => {
    const res = await apiClient.post<ApiSuccessResponse<{ marked_read_count: number }>>(
      "/notifications/read-all/"
    );
    return res.data.data;
  },
  remove: async (id: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(`/notifications/${id}/`);
    return res.data;
  },
};

export const favoritesApi = {
  listWorkers: async () => {
    const res = await apiClient.get<ApiPaginatedResponse<FavoriteWorker>>("/favorites/workers/");
    return res.data;
  },
  addWorker: async (workerId: string) => {
    const res = await apiClient.post<ApiSuccessResponse<FavoriteWorker>>("/favorites/workers/", {
      worker: workerId,
    });
    return res.data.data;
  },
  removeWorker: async (workerId: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(
      `/favorites/workers/${workerId}/`
    );
    return res.data;
  },
  listOrders: async () => {
    const res = await apiClient.get<ApiPaginatedResponse<FavoriteOrder>>("/favorites/orders/");
    return res.data;
  },
  addOrder: async (orderId: string) => {
    const res = await apiClient.post<ApiSuccessResponse<FavoriteOrder>>("/favorites/orders/", {
      order: orderId,
    });
    return res.data.data;
  },
  removeOrder: async (orderId: string) => {
    const res = await apiClient.delete<ApiSuccessResponse<null>>(`/favorites/orders/${orderId}/`);
    return res.data;
  },
};

export const reportsApi = {
  list: async () => {
    const res = await apiClient.get<ApiPaginatedResponse<ReportItem>>("/reports/");
    return res.data;
  },
  create: async (payload: {
    target_type: ReportTargetType;
    target_id: string;
    reason: ReportReason;
    description: string;
  }) => {
    const res = await apiClient.post<ApiSuccessResponse<ReportItem>>("/reports/", payload);
    return res.data.data;
  },
};

export const dashboardApi = {
  employer: async () => {
    const res = await apiClient.get<ApiSuccessResponse<EmployerDashboardStats>>(
      "/dashboard/employer/"
    );
    return res.data.data;
  },
  worker: async () => {
    const res = await apiClient.get<ApiSuccessResponse<WorkerDashboardStats>>(
      "/dashboard/worker/"
    );
    return res.data.data;
  },
};

export const adminApi = {
  stats: async () => {
    const res = await apiClient.get<ApiSuccessResponse<AdminDashboardStats>>("/admin/dashboard/");
    return res.data.data;
  },
  listUsers: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<UserSummary>>("/admin/users/", {
      params,
    });
    return res.data;
  },
  suspendUser: async (userId: string, reason = "") => {
    const res = await apiClient.post<ApiSuccessResponse<UserSummary>>(
      `/admin/users/${userId}/suspend/`,
      { reason }
    );
    return res.data.data;
  },
  activateUser: async (userId: string) => {
    const res = await apiClient.post<ApiSuccessResponse<UserSummary>>(
      `/admin/users/${userId}/activate/`
    );
    return res.data.data;
  },
  listWorkers: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<WorkerProfile>>("/admin/workers/", {
      params,
    });
    return res.data;
  },
  verifyWorker: async (workerId: string, action: "APPROVE" | "REJECT", notes = "") => {
    const res = await apiClient.post<ApiSuccessResponse<WorkerProfile>>(
      `/admin/workers/${workerId}/verify/`,
      { action, notes }
    );
    return res.data.data;
  },
  listOrders: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<ServiceOrder>>("/admin/orders/", {
      params,
    });
    return res.data;
  },
  moderateOrder: async (orderId: string, action: "CANCEL" | "CLOSE", reason = "") => {
    const res = await apiClient.post<ApiSuccessResponse<ServiceOrder>>(
      `/admin/orders/${orderId}/moderate/`,
      { action, reason }
    );
    return res.data.data;
  },
  listReports: async (params?: Record<string, string | number | undefined>) => {
    const res = await apiClient.get<ApiPaginatedResponse<ReportItem>>("/admin/reports/", {
      params,
    });
    return res.data;
  },
  resolveReport: async (reportId: string, status: ReportStatus, admin_resolution = "") => {
    const res = await apiClient.post<ApiSuccessResponse<ReportItem>>(
      `/admin/reports/${reportId}/resolve/`,
      { status, admin_resolution }
    );
    return res.data.data;
  },
};
