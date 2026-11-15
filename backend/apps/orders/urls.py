from django.urls import path
from apps.orders.views import (
    OrderCancelView,
    OrderCloseView,
    OrderCompleteView,
    OrderImageDeleteView,
    OrderImageUploadView,
    OrderPauseView,
    OrderPublishView,
    ServiceOrderDetailView,
    ServiceOrderListCreateView,
)

urlpatterns = [
    path("", ServiceOrderListCreateView.as_view(), name="orders-list-create"),
    path("<uuid:order_id>/", ServiceOrderDetailView.as_view(), name="orders-detail"),
    path("<uuid:order_id>/publish/", OrderPublishView.as_view(), name="orders-publish"),
    path("<uuid:order_id>/pause/", OrderPauseView.as_view(), name="orders-pause"),
    path("<uuid:order_id>/cancel/", OrderCancelView.as_view(), name="orders-cancel"),
    path("<uuid:order_id>/close/", OrderCloseView.as_view(), name="orders-close"),
    path("<uuid:order_id>/complete/", OrderCompleteView.as_view(), name="orders-complete"),
    path("<uuid:order_id>/images/", OrderImageUploadView.as_view(), name="orders-image-upload"),
    path("<uuid:order_id>/images/<uuid:image_id>/", OrderImageDeleteView.as_view(), name="orders-image-delete"),
]
