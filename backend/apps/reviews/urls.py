from django.urls import path
from apps.reviews.views import ReviewEligibilityView, ReviewListCreateView

urlpatterns = [
    path("", ReviewListCreateView.as_view(), name="reviews-list-create"),
    path("eligibility/", ReviewEligibilityView.as_view(), name="reviews-eligibility"),
]
