from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts.models import AccountStatus, User, UserRole
from apps.accounts.permissions import IsAdminUserRole, IsEmployer, IsWorker
from apps.accounts.serializers import UserSummarySerializer
from apps.accounts.services.auth_service import _blacklist_all_user_tokens
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.categories.models import Category
from apps.common.exceptions import BusinessRuleViolation
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.notifications.models import Notification, NotificationEventType
from apps.notifications.services import NotificationService
from apps.orders.models import OrderStatus, ServiceOrder
from apps.orders.serializers import ServiceOrderSerializer
from apps.profiles.models import EmployerProfile, VerificationStatus, WorkerProfile
from apps.profiles.serializers import WorkerProfileSerializer
from apps.reports.models import Report, ReportStatus
from apps.reports.serializers import ReportResolveSerializer, ReportSerializer
from apps.reviews.models import Review
from apps.dashboard.serializers import (
    AdminOrderModerateSerializer,
    AdminUserSuspendSerializer,
    AdminWorkerVerifySerializer,
)


class EmployerDashboardView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(summary="Employer Dashboard Statistics", tags=["Dashboards"])
    def get(self, request):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        orders_qs = ServiceOrder.objects.filter(employer=employer)
        status_counts = {
            row["status"]: row["total"]
            for row in orders_qs.values("status").annotate(total=Count("id"))
        }
        pending_applications = OrderApplication.objects.filter(
            order__employer=employer, status=ApplicationStatus.PENDING
        ).count()
        pending_invitations = OrderInvitation.objects.filter(
            employer=employer, status=InvitationStatus.PENDING
        ).count()
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()

        recent_orders = ServiceOrderSerializer(
            orders_qs.select_related("employer", "category", "assigned_worker").order_by("-created_at")[:5],
            many=True,
            context={"request": request},
        ).data

        return success_response(
            data={
                "employer_id": str(employer.id),
                "total_orders": orders_qs.count(),
                "orders_by_status": status_counts,
                "pending_applications_received": pending_applications,
                "pending_invitations_sent": pending_invitations,
                "rating_avg": str(employer.rating_avg),
                "review_count": employer.review_count,
                "unread_notifications": unread_notifications,
                "recent_orders": recent_orders,
            }
        )


class WorkerDashboardView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Worker Dashboard Statistics", tags=["Dashboards"])
    def get(self, request):
        worker = get_object_or_404(WorkerProfile, user=request.user)
        apps_qs = OrderApplication.objects.filter(worker=worker)
        invs_qs = OrderInvitation.objects.filter(worker=worker)
        assigned_qs = ServiceOrder.objects.filter(Q(assigned_worker=worker) | Q(assigned_workers=worker)).distinct()
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()

        return success_response(
            data={
                "worker_id": str(worker.id),
                "verification_status": worker.verification_status,
                "is_verified": worker.is_verified,
                "is_available": worker.is_available,
                "rating_avg": str(worker.rating_avg),
                "review_count": worker.review_count,
                "completed_orders_count": worker.completed_orders_count,
                "applications_summary": {
                    row["status"]: row["total"]
                    for row in apps_qs.values("status").annotate(total=Count("id"))
                },
                "pending_invitations_count": invs_qs.filter(status=InvitationStatus.PENDING).count(),
                "active_assigned_orders_count": assigned_qs.filter(status=OrderStatus.IN_PROGRESS).count(),
                "unread_notifications": unread_notifications,
            }
        )


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(summary="Admin Platform Statistics", tags=["Admin"])
    def get(self, request):
        users_qs = User.objects.all()
        workers_qs = WorkerProfile.objects.filter(user__is_anonymized=False)
        orders_qs = ServiceOrder.objects.all()
        reports_qs = Report.objects.all()

        return success_response(
            data={
                "users": {
                    "total": users_qs.count(),
                    "active": users_qs.filter(account_status=AccountStatus.ACTIVE).count(),
                    "suspended": users_qs.filter(account_status=AccountStatus.SUSPENDED).count(),
                    "anonymized": users_qs.filter(is_anonymized=True).count(),
                    "by_role": {r["role"]: r["total"] for r in users_qs.values("role").annotate(total=Count("id"))},
                },
                "workers": {
                    "total": workers_qs.count(),
                    "verified": workers_qs.filter(is_verified=True).count(),
                    "pending_verification": workers_qs.filter(verification_status=VerificationStatus.PENDING).count(),
                    "unverified": workers_qs.filter(is_verified=False).count(),
                },
                "employers": {
                    "total": EmployerProfile.objects.filter(user__is_anonymized=False).count(),
                },
                "categories": {
                    "total": Category.objects.count(),
                    "active": Category.objects.filter(is_active=True).count(),
                },
                "orders": {
                    "total": orders_qs.count(),
                    "by_status": {r["status"]: r["total"] for r in orders_qs.values("status").annotate(total=Count("id"))},
                },
                "applications_total": OrderApplication.objects.count(),
                "invitations_total": OrderInvitation.objects.count(),
                "reviews_total": Review.objects.count(),
                "reports": {
                    "total": reports_qs.count(),
                    "by_status": {r["status"]: r["total"] for r in reports_qs.values("status").annotate(total=Count("id"))},
                },
            }
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: List Users",
        parameters=[
            OpenApiParameter(name="role", type=str, required=False),
            OpenApiParameter(name="account_status", type=str, required=False),
            OpenApiParameter(name="search", type=str, required=False),
        ],
        responses={200: UserSummarySerializer(many=True)},
        tags=["Admin"],
    )
    def get(self, request):
        qs = User.objects.all().order_by("-created_at")
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        acc_status = request.query_params.get("account_status")
        if acc_status:
            qs = qs.filter(account_status=acc_status)
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(full_name__icontains=search) | Q(phone_number__icontains=search) | Q(email__icontains=search))

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UserSummarySerializer(page, many=True).data)


class AdminUserSuspendView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(summary="Admin: Suspend User", request=AdminUserSuspendSerializer, tags=["Admin"])
    def post(self, request, user_id):
        with transaction.atomic():
            target = get_object_or_404(User.objects.select_for_update(), id=user_id)
            if str(target.id) == str(request.user.id):
                raise BusinessRuleViolation("Administrators cannot suspend themselves.", code="cannot_suspend_self")
            if target.is_anonymized:
                raise BusinessRuleViolation("Cannot suspend an anonymized user.", code="user_anonymized")

            target.account_status = AccountStatus.SUSPENDED
            target.is_active = False
            target.token_version += 1
            target.save(update_fields=["account_status", "is_active", "token_version", "updated_at"])
            _blacklist_all_user_tokens(target)

        return success_response(data=UserSummarySerializer(target).data, message="User account suspended.")


class AdminUserActivateView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(summary="Admin: Activate Suspended User", tags=["Admin"])
    def post(self, request, user_id):
        with transaction.atomic():
            target = get_object_or_404(User.objects.select_for_update(), id=user_id)
            if target.is_anonymized or target.account_status == AccountStatus.DELETED:
                raise BusinessRuleViolation("Deleted/anonymized accounts cannot be reactivated.", code="user_deleted")
            target.account_status = AccountStatus.ACTIVE
            target.is_active = True
            target.save(update_fields=["account_status", "is_active", "updated_at"])

        return success_response(data=UserSummarySerializer(target).data, message="User account activated.")


class AdminWorkerListView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: List Workers",
        parameters=[OpenApiParameter(name="verification_status", type=str, required=False)],
        responses={200: WorkerProfileSerializer(many=True)},
        tags=["Admin"],
    )
    def get(self, request):
        qs = WorkerProfile.objects.filter(user__is_anonymized=False).select_related("user").order_by("-created_at")
        v_status = request.query_params.get("verification_status")
        if v_status:
            qs = qs.filter(verification_status=v_status)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(WorkerProfileSerializer(page, many=True, context={"request": request}).data)


class AdminWorkerVerifyView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: Verify or Reject Worker",
        request=AdminWorkerVerifySerializer,
        responses={200: WorkerProfileSerializer},
        tags=["Admin"],
    )
    def post(self, request, worker_id):
        serializer = AdminWorkerVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        with transaction.atomic():
            worker = get_object_or_404(
                WorkerProfile.objects.select_for_update(of=("self",)).select_related("user"),
                id=worker_id,
            )
            if worker.user.is_anonymized:
                raise BusinessRuleViolation("Cannot verify an anonymized worker.", code="user_anonymized")

            now = timezone.now()
            if action == "APPROVE":
                worker.verification_status = VerificationStatus.VERIFIED
                worker.is_verified = True
                worker.verified_by = request.user
                worker.verified_at = now
                worker.verification_notes = notes or "Approved by administrator."
                msg = "Your worker profile has been verified! You can now apply for service orders."
            else:
                worker.verification_status = VerificationStatus.REJECTED
                worker.is_verified = False
                worker.verified_by = request.user
                worker.verified_at = None
                worker.verification_notes = notes or "Verification rejected by administrator."
                msg = f"Your worker verification was rejected. Notes: {worker.verification_notes}"

            worker.save()
            NotificationService.notify(
                recipient=worker.user,
                event_type=NotificationEventType.VERIFICATION_UPDATED,
                title=f"Worker Verification {worker.verification_status}",
                message=msg,
                data={"verification_status": worker.verification_status, "is_verified": worker.is_verified},
            )

        return success_response(
            data=WorkerProfileSerializer(worker, context={"request": request}).data,
            message=f"Worker verification status set to {worker.verification_status}.",
        )


class AdminOrderListView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: List All Orders",
        parameters=[OpenApiParameter(name="status", type=str, required=False)],
        responses={200: ServiceOrderSerializer(many=True)},
        tags=["Admin"],
    )
    def get(self, request):
        qs = ServiceOrder.objects.select_related("employer", "category", "assigned_worker").order_by("-created_at")
        ord_status = request.query_params.get("status")
        if ord_status:
            qs = qs.filter(status=ord_status)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ServiceOrderSerializer(page, many=True, context={"request": request}).data)


class AdminOrderModerateView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: Moderate (Cancel/Close) Order",
        request=AdminOrderModerateSerializer,
        responses={200: ServiceOrderSerializer},
        tags=["Admin"],
    )
    def post(self, request, order_id):
        serializer = AdminOrderModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        with transaction.atomic():
            order = get_object_or_404(
                ServiceOrder.objects.select_for_update(of=("self",)).select_related("employer__user"),
                id=order_id,
            )
            if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.CLOSED):
                raise BusinessRuleViolation(f"Order is already in terminal status '{order.status}'.", code="invalid_status")
            new_status = OrderStatus.CANCELLED if action == "CANCEL" else OrderStatus.CLOSED
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
            NotificationService.notify(
                recipient=order.employer.user,
                event_type=NotificationEventType.ORDER_STATUS_CHANGED,
                title=f"Order {new_status} by Admin",
                message=f"Order '{order.title}' was {new_status.lower()} by moderation.",
                data={"order_id": str(order.id), "status": new_status},
            )
        return success_response(data=ServiceOrderSerializer(order, context={"request": request}).data, message=f"Order {new_status.lower()}.")


class AdminReportListView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: List Moderation Reports",
        parameters=[OpenApiParameter(name="status", type=str, required=False)],
        responses={200: ReportSerializer(many=True)},
        tags=["Admin"],
    )
    def get(self, request):
        qs = Report.objects.select_related("reporter", "resolved_by").order_by("-created_at")
        rep_status = request.query_params.get("status")
        if rep_status:
            qs = qs.filter(status=rep_status)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ReportSerializer(page, many=True).data)


class AdminReportResolveView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Admin: Resolve / Update Moderation Report",
        request=ReportResolveSerializer,
        responses={200: ReportSerializer},
        tags=["Admin"],
    )
    def post(self, request, report_id):
        serializer = ReportResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            report = get_object_or_404(Report.objects.select_for_update(), id=report_id)
            report.status = serializer.validated_data["status"]
            report.admin_resolution = serializer.validated_data.get("admin_resolution", "")
            report.resolved_by = request.user
            if report.status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
                report.resolved_at = timezone.now()
            report.save()
        return success_response(data=ReportSerializer(report).data, message="Report updated.")
