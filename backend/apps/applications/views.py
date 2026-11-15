from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from apps.accounts.permissions import IsEmployer, IsWorker
from apps.applications.models import OrderApplication
from apps.applications.serializers import (
    ApplicationRejectSerializer,
    OrderApplicationCreateSerializer,
    OrderApplicationSerializer,
)
from apps.applications.services import ApplicationService
from apps.common.exceptions import ForbiddenActionError
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.profiles.models import EmployerProfile, WorkerProfile


class ApplicationListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsWorker()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        summary="List Applications",
        description="Workers see their own applications; employers see applications to their orders (filterable by ?order=<uuid>&status=...).",
        parameters=[
            OpenApiParameter(name="order", type=str, required=False),
            OpenApiParameter(name="status", type=str, required=False),
        ],
        responses={200: OrderApplicationSerializer(many=True)},
        tags=["Applications"],
    )
    def get(self, request):
        qs = OrderApplication.objects.select_related("order__employer", "worker__user")
        user = request.user
        if not getattr(user, "is_admin_user", False):
            filters_q = Q()
            if hasattr(user, "worker_profile"):
                filters_q |= Q(worker=user.worker_profile)
            if hasattr(user, "employer_profile"):
                filters_q |= Q(order__employer=user.employer_profile)
            if not filters_q:
                qs = qs.none()
            else:
                qs = qs.filter(filters_q)

        order_id = request.query_params.get("order")
        if order_id:
            qs = qs.filter(order_id=order_id)

        app_status = request.query_params.get("status")
        if app_status:
            qs = qs.filter(status=app_status)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(OrderApplicationSerializer(page, many=True).data)

    @extend_schema(
        summary="Submit Application (Verified Worker Only)",
        request=OrderApplicationCreateSerializer,
        responses={201: OrderApplicationSerializer},
        tags=["Applications"],
    )
    def post(self, request):
        worker = get_object_or_404(WorkerProfile, user=request.user)
        serializer = OrderApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = ApplicationService.submit_application(
            worker=worker,
            order_id=serializer.validated_data["order"],
            cover_message=serializer.validated_data["cover_message"],
            proposed_price=serializer.validated_data["proposed_price"],
        )
        return success_response(
            data=OrderApplicationSerializer(app).data,
            message="Application submitted successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ApplicationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get Application Detail", responses={200: OrderApplicationSerializer}, tags=["Applications"])
    def get(self, request, application_id):
        app = get_object_or_404(
            OrderApplication.objects.select_related("order__employer__user", "worker__user"),
            id=application_id,
        )
        user = request.user
        if not (
            getattr(user, "is_admin_user", False)
            or str(app.worker.user_id) == str(user.id)
            or str(app.order.employer.user_id) == str(user.id)
        ):
            raise ForbiddenActionError("You do not have permission to view this application.")
        return success_response(data=OrderApplicationSerializer(app).data)


class ApplicationWithdrawView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Withdraw Application (Worker)", responses={200: OrderApplicationSerializer}, tags=["Applications"])
    def post(self, request, application_id):
        worker = get_object_or_404(WorkerProfile, user=request.user)
        app = ApplicationService.withdraw_application(application_id, worker)
        return success_response(data=OrderApplicationSerializer(app).data, message="Application withdrawn.")


class ApplicationAcceptView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(summary="Accept Application (Employer)", responses={200: OrderApplicationSerializer}, tags=["Applications"])
    def post(self, request, application_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        app = ApplicationService.accept_application(application_id, employer)
        return success_response(data=OrderApplicationSerializer(app).data, message="Application accepted. Order is now IN_PROGRESS.")


class ApplicationRejectView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(
        summary="Reject Application (Employer)",
        request=ApplicationRejectSerializer,
        responses={200: OrderApplicationSerializer},
        tags=["Applications"],
    )
    def post(self, request, application_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        serializer = ApplicationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = ApplicationService.reject_application(
            application_id,
            employer,
            reason=serializer.validated_data.get("reason", ""),
        )
        return success_response(data=OrderApplicationSerializer(app).data, message="Application rejected.")
