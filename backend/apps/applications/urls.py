from django.urls import path
from apps.applications.views import (
    ApplicationAcceptView,
    ApplicationDetailView,
    ApplicationListCreateView,
    ApplicationRejectView,
    ApplicationWithdrawView,
)

urlpatterns = [
    path("", ApplicationListCreateView.as_view(), name="applications-list-create"),
    path("<uuid:application_id>/", ApplicationDetailView.as_view(), name="applications-detail"),
    path("<uuid:application_id>/withdraw/", ApplicationWithdrawView.as_view(), name="applications-withdraw"),
    path("<uuid:application_id>/accept/", ApplicationAcceptView.as_view(), name="applications-accept"),
    path("<uuid:application_id>/reject/", ApplicationRejectView.as_view(), name="applications-reject"),
]
