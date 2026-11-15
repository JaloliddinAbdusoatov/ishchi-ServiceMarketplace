from django.urls import path
from apps.profiles.views import (
    MyEmployerProfileView,
    MyWorkerCategoriesView,
    MyWorkerProfileView,
    WorkerPortfolioDetailView,
    WorkerPortfolioListCreateView,
    WorkerVerificationRequestView,
)

urlpatterns = [
    path("worker/", MyWorkerProfileView.as_view(), name="my-worker-profile"),
    path("worker/verification-request/", WorkerVerificationRequestView.as_view(), name="worker-verification-request"),
    path("worker/portfolio/", WorkerPortfolioListCreateView.as_view(), name="worker-portfolio-list-create"),
    path("worker/portfolio/<uuid:item_id>/", WorkerPortfolioDetailView.as_view(), name="worker-portfolio-detail"),
    path("worker/categories/", MyWorkerCategoriesView.as_view(), name="worker-categories"),
    path("employer/", MyEmployerProfileView.as_view(), name="my-employer-profile"),
]
