from django.conf import settings
from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Public liveness/dependency status without infrastructure details."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        db_status = cache_status = "ok"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone()[0] != 1:
                    db_status = "unavailable"
        except Exception:
            db_status = "unavailable"
        try:
            cache.set("health_ping", "pong", timeout=10)
            if cache.get("health_ping") != "pong":
                cache_status = "unavailable"
        except Exception:
            cache_status = "unavailable"
        healthy = db_status == cache_status == "ok"
        return Response({"success": healthy, "service": "ishchi-backend",
            "database": {"status": db_status}, "redis": {"status": cache_status},
            "payments_enabled": False}, status=200 if healthy else 503)


class LivenessView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({"success": True, "service": "ishchi-backend"})


class PaymentStatusView(APIView):
    """Informational only. There is no payment submission endpoint."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        return Response({"success": True, "data": {"enabled": False, "status": "DISABLED",
            "message": "Online payments are not available. ISHCHI does not collect card details or transfer money."}})


class PublicPlatformStatsView(APIView):
    """Non-PII public platform statistics for landing & marketplace overview."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Public Platform Statistics",
        description="Returns aggregated non-PII marketplace counters from PostgreSQL.",
        responses={200: OpenApiResponse(description="Platform statistics")},
        tags=["System"],
    )
    def get(self, request, *args, **kwargs):
        from apps.categories.models import Category
        from apps.orders.models import OrderStatus, ServiceOrder
        from apps.profiles.models import EmployerProfile, WorkerProfile
        from apps.reviews.models import Review

        workers_qs = WorkerProfile.objects.filter(user__is_active=True, user__account_status="ACTIVE", user__is_anonymized=False)
        employers_qs = EmployerProfile.objects.filter(user__is_active=True, user__account_status="ACTIVE", user__is_anonymized=False)
        orders_qs = ServiceOrder.objects.filter(employer__user__is_anonymized=False)

        return Response(
            {
                "success": True,
                "data": {
                    "total_workers": workers_qs.count(),
                    "verified_workers": workers_qs.filter(is_verified=True).count(),
                    "total_employers": employers_qs.count(),
                    "published_orders": orders_qs.filter(status=OrderStatus.PUBLISHED).count(),
                    "in_progress_orders": orders_qs.filter(status=OrderStatus.IN_PROGRESS).count(),
                    "completed_orders": orders_qs.filter(status=OrderStatus.COMPLETED).count(),
                    "total_categories": Category.objects.filter(is_active=True).count(),
                    "total_reviews": Review.objects.count(),
                },
            },
            status=status.HTTP_200_OK,
        )
