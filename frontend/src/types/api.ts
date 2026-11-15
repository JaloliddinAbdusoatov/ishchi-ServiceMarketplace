export type UserRole = "WORKER" | "EMPLOYER" | "ADMIN";
export type AccountStatus = "ACTIVE" | "SUSPENDED" | "DELETED";
export type VerificationStatus = "UNSUBMITTED" | "PENDING" | "VERIFIED" | "REJECTED";
export type PricingType = "HOURLY" | "FIXED" | "NEGOTIABLE";
export type EmployerType = "INDIVIDUAL" | "COMPANY";
export type OrderStatus =
  | "DRAFT"
  | "PUBLISHED"
  | "PAUSED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "CLOSED";
export type BudgetType = "FIXED" | "HOURLY" | "NEGOTIABLE";
export type WorkType = "ONSITE" | "REMOTE" | "HYBRID";
export type ApplicationStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "WITHDRAWN";
export type InvitationStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "CANCELLED" | "EXPIRED";
export type ReviewDirection = "EMPLOYER_TO_WORKER" | "WORKER_TO_EMPLOYER";
export type ReportTargetType = "USER" | "ORDER" | "MESSAGE";
export type ReportReason = "SPAM" | "FRAUD" | "HARASSMENT" | "INAPPROPRIATE" | "OTHER";
export type ReportStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED";

export interface ApiSuccessResponse<T> {
  success: boolean;
  message?: string;
  data: T;
}

export interface ApiPaginatedResponse<T> {
  success: boolean;
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  results: T[];
  unread_count?: number;
}

export interface ApiErrorPayload {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | string[] | null;
  };
}

export interface AuthTokens {
  access: string;
  refresh: string;
  token_type: string;
}

export interface UserSummary {
  id: string;
  phone_number: string | null;
  email: string | null;
  full_name: string;
  role: UserRole;
  has_worker_role: boolean;
  has_employer_role: boolean;
  is_worker: boolean;
  is_employer: boolean;
  is_verified_worker: boolean;
  worker_profile_id: string | null;
  employer_profile_id: string | null;
  worker_verification_status: VerificationStatus | null;
  is_phone_verified: boolean;
  account_status: AccountStatus;
  created_at: string;
}

export interface CategoryChild {
  id: string;
  slug: string;
  name: string;
  name_uz: string;
  name_ru: string;
  name_en: string;
  description: string;
  image: string | null;
  is_active: boolean;
  display_order: number;
}

export interface Category {
  id: string;
  parent: string | null;
  parent_name: string | null;
  slug: string;
  name: string;
  name_uz: string;
  name_ru: string;
  name_en: string;
  description: string;
  image: string | null;
  is_active: boolean;
  display_order: number;
  children: CategoryChild[];
  created_at: string;
  updated_at: string;
}

export interface WorkerCategoryItem {
  id: string;
  category_id: string;
  slug: string;
  name: string;
  name_uz: string;
  name_ru: string;
  name_en: string;
  is_primary: boolean;
  experience_years: number | null;
}

export interface WorkerPortfolioItem {
  id: string;
  title: string;
  description: string;
  image: string | null;
  project_url: string;
  completed_year: number | null;
  created_at: string;
}

export interface WorkerProfile {
  id: string;
  user_id: string;
  full_name: string;
  bio: string;
  phone_number: string | null;
  photo: string | null;
  location: string;
  district: string;
  skills: string[];
  experience_years: number;
  experience_description: string;
  pricing_type: PricingType;
  hourly_rate: string | null;
  fixed_rate_from: string | null;
  is_available: boolean;
  verification_status: VerificationStatus;
  is_verified: boolean;
  verification_notes: string;
  verified_at: string | null;
  rating_avg: string;
  review_count: number;
  completed_orders_count: number;
  categories: WorkerCategoryItem[];
  portfolio_items: WorkerPortfolioItem[];
  created_at: string;
  updated_at: string;
}

export interface EmployerProfile {
  id: string;
  user_id: string;
  employer_type: EmployerType;
  full_name: string;
  company_name: string;
  bio: string;
  phone_number: string | null;
  email: string | null;
  photo: string | null;
  location: string;
  district: string;
  address: string;
  rating_avg: string;
  review_count: number;
  posted_orders_count: number;
  completed_orders_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrderImage {
  id: string;
  image: string;
  caption: string;
  display_order: number;
  created_at: string;
}

export interface ServiceOrder {
  id: string;
  employer: string;
  employer_user_id: string;
  employer_name: string;
  category: string;
  category_name: string;
  assigned_worker: string | null;
  assigned_worker_user_id: string | null;
  assigned_worker_name: string | null;
  capacity?: number;
  hired_worker_count?: number;
  team?: Array<{ id: string; user_id: string; name: string }>;
  title: string;
  description: string;
  budget: string;
  budget_type: BudgetType;
  location: string;
  district: string;
  address: string;
  work_type: WorkType;
  deadline: string | null;
  start_date: string | null;
  status: OrderStatus;
  payment_status: "DISABLED";
  images: OrderImage[];
  applications_count: number;
  published_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderApplication {
  id: string;
  order: string;
  order_title: string;
  order_status: OrderStatus;
  worker: string;
  worker_name: string;
  worker_rating: string;
  worker_is_verified: boolean;
  cover_message: string;
  proposed_price: string;
  status: ApplicationStatus;
  rejection_reason: string;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderInvitation {
  id: string;
  order: string;
  order_title: string;
  employer: string;
  employer_name: string;
  worker: string;
  worker_name: string;
  message: string;
  proposed_budget: string | null;
  status: InvitationStatus;
  expires_at: string;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationLastMessage {
  id: string;
  sender_id: string;
  content: string;
  has_attachment: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  order: string;
  order_title: string;
  employer: string;
  employer_name: string;
  worker: string;
  worker_name: string;
  last_message_at: string | null;
  unread_count: number;
  last_message: ConversationLastMessage | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  conversation: string;
  sender_id: string;
  sender_name: string;
  content: string;
  attachment: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface Review {
  id: string;
  order: string;
  order_title: string;
  reviewer: string;
  reviewer_name: string;
  reviewee: string;
  reviewee_name: string;
  direction: ReviewDirection;
  rating: number;
  comment: string;
  created_at: string;
}

export interface ReviewEligibility {
  reviewee_id?: string;
  reviewee_name?: string;
  eligible: boolean;
  reason: string;
  direction: ReviewDirection | null;
  existing_review: Review | null;
}

export interface NotificationItem {
  id: string;
  event_type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface FavoriteWorker {
  id: string;
  worker: string;
  worker_detail: WorkerProfile;
  created_at: string;
}

export interface FavoriteOrder {
  id: string;
  order: string;
  order_detail: ServiceOrder;
  created_at: string;
}

export interface ReportItem {
  id: string;
  reporter: string;
  reporter_name: string;
  target_type: ReportTargetType;
  target_user: string | null;
  target_order: string | null;
  target_message: string | null;
  reason: ReportReason;
  description: string;
  status: ReportStatus;
  admin_resolution: string;
  resolved_by: string | null;
  resolved_by_name: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublicPlatformStats {
  total_workers: number;
  verified_workers: number;
  total_employers: number;
  published_orders: number;
  in_progress_orders: number;
  completed_orders: number;
  total_categories: number;
  total_reviews: number;
}

export interface EmployerDashboardStats {
  employer_id: string;
  total_orders: number;
  orders_by_status: Record<string, number>;
  pending_applications_received: number;
  pending_invitations_sent: number;
  rating_avg: string;
  review_count: number;
  unread_notifications: number;
  recent_orders: ServiceOrder[];
}

export interface WorkerDashboardStats {
  worker_id: string;
  verification_status: VerificationStatus;
  is_verified: boolean;
  is_available: boolean;
  rating_avg: string;
  review_count: number;
  completed_orders_count: number;
  applications_summary: Record<string, number>;
  pending_invitations_count: number;
  active_assigned_orders_count: number;
  unread_notifications: number;
}

export interface AdminDashboardStats {
  users: {
    total: number;
    active: number;
    suspended: number;
    anonymized: number;
    by_role: Record<string, number>;
  };
  workers: {
    total: number;
    verified: number;
    pending_verification: number;
    unverified: number;
  };
  employers: {
    total: number;
  };
  categories: {
    total: number;
    active: number;
  };
  orders: {
    total: number;
    by_status: Record<string, number>;
  };
  applications_total: number;
  invitations_total: number;
  reviews_total: number;
  reports: {
    total: number;
    by_status: Record<string, number>;
  };
}
