from django.urls import path
from apps.notifications.views import (
    NotificationDeleteView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="notifications-read-all"),
    path("<uuid:notification_id>/read/", NotificationMarkReadView.as_view(), name="notifications-read"),
    path("<uuid:notification_id>/", NotificationDeleteView.as_view(), name="notifications-delete"),
]
