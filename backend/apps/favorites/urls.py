from django.urls import path
from apps.favorites.views import (
    FavoriteOrderDeleteView,
    FavoriteOrderListCreateView,
    FavoriteWorkerDeleteView,
    FavoriteWorkerListCreateView,
)

urlpatterns = [
    path("workers/", FavoriteWorkerListCreateView.as_view(), name="favorites-workers"),
    path("workers/<uuid:worker_id>/", FavoriteWorkerDeleteView.as_view(), name="favorites-worker-delete"),
    path("orders/", FavoriteOrderListCreateView.as_view(), name="favorites-orders"),
    path("orders/<uuid:order_id>/", FavoriteOrderDeleteView.as_view(), name="favorites-order-delete"),
]
