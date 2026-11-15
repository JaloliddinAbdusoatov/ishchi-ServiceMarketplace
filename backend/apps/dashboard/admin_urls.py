from django.urls import path
from apps.dashboard.views import (
    AdminDashboardStatsView,
    AdminOrderListView,
    AdminOrderModerateView,
    AdminReportListView,
    AdminReportResolveView,
    AdminUserActivateView,
    AdminUserListView,
    AdminUserSuspendView,
    AdminWorkerListView,
    AdminWorkerVerifyView,
)

urlpatterns = [
    path("dashboard/", AdminDashboardStatsView.as_view(), name="admin-dashboard"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<uuid:user_id>/suspend/", AdminUserSuspendView.as_view(), name="admin-user-suspend"),
    path("users/<uuid:user_id>/activate/", AdminUserActivateView.as_view(), name="admin-user-activate"),
    path("workers/", AdminWorkerListView.as_view(), name="admin-workers"),
    path("workers/<uuid:worker_id>/verify/", AdminWorkerVerifyView.as_view(), name="admin-worker-verify"),
    path("orders/", AdminOrderListView.as_view(), name="admin-orders"),
    path("orders/<uuid:order_id>/moderate/", AdminOrderModerateView.as_view(), name="admin-order-moderate"),
    path("reports/", AdminReportListView.as_view(), name="admin-reports"),
    path("reports/<uuid:report_id>/resolve/", AdminReportResolveView.as_view(), name="admin-report-resolve"),
]
