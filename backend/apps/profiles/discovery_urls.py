from django.urls import path
from apps.profiles.views import (
    EmployerDiscoveryDetailView,
    WorkerDiscoveryDetailView,
    WorkerDiscoveryListView,
)

urlpatterns = [
    path("workers/", WorkerDiscoveryListView.as_view(), name="workers-list"),
    path("workers/<uuid:worker_id>/", WorkerDiscoveryDetailView.as_view(), name="workers-detail"),
    path("employers/<uuid:employer_id>/", EmployerDiscoveryDetailView.as_view(), name="employers-detail"),
]
