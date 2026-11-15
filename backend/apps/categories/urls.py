from django.urls import path
from apps.categories.views import CategoryDeactivateView, CategoryDetailView, CategoryListCreateView

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="category-list-create"),
    path("<uuid:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
    path("<uuid:category_id>/deactivate/", CategoryDeactivateView.as_view(), name="category-deactivate"),
]
