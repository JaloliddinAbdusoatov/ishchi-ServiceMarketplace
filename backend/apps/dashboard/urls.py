from django.urls import path
from apps.dashboard.views import EmployerDashboardView, WorkerDashboardView

urlpatterns = [
    path("employer/", EmployerDashboardView.as_view(), name="dashboard-employer"),
    path("worker/", WorkerDashboardView.as_view(), name="dashboard-worker"),
]
