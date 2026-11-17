from django.http import HttpResponseNotFound
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.common.views import HealthCheckView, LivenessView, PaymentStatusView, PublicPlatformStatsView

api_v1_patterns = [
    path("health/live/", LivenessView.as_view(), name="liveness"),
    path("health/ready/", HealthCheckView.as_view(), name="readiness"),
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("stats/", PublicPlatformStatsView.as_view(), name="public-stats"),
    path("payments/status/", PaymentStatusView.as_view(), name="payment-status"),
    path("auth/", include("apps.accounts.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("", include("apps.profiles.discovery_urls")),
    path("categories/", include("apps.categories.urls")),
    path("orders/", include("apps.orders.urls")),
    path("applications/", include("apps.applications.urls")),
    path("invitations/", include("apps.invitations.urls")),
    path("chat/", include("apps.chat.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("favorites/", include("apps.favorites.urls")),
    path("reports/", include("apps.reports.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("admin/", include("apps.dashboard.admin_urls")),
]

admin.site.site_header = "ISHCHI Administration"
admin.site.site_title = "ISHCHI"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api-v1"))),
]

if settings.DEBUG:
    urlpatterns += [path("media/chat/attachments/<path:name>", lambda request, name: HttpResponseNotFound())]
    urlpatterns += [path("media/orders/images/<path:name>", lambda request, name: HttpResponseNotFound())]
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
