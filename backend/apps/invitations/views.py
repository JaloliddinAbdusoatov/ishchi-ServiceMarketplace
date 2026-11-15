from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from apps.accounts.permissions import IsEmployer, IsWorker
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.invitations.models import OrderInvitation
from apps.invitations.serializers import OrderInvitationCreateSerializer, OrderInvitationSerializer
from apps.invitations.services import InvitationService
from apps.profiles.models import EmployerProfile, WorkerProfile


class InvitationListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsEmployer()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        summary="List Invitations",
        description="Workers see received invitations; employers see sent invitations.",
        parameters=[
            OpenApiParameter(name="status", type=str, required=False),
            OpenApiParameter(name="order", type=str, required=False),
        ],
        responses={200: OrderInvitationSerializer(many=True)},
        tags=["Invitations"],
    )
    def get(self, request):
        qs = OrderInvitation.objects.select_related("order", "employer", "worker")
        user = request.user
        if not getattr(user, "is_admin_user", False):
            q = Q()
            if hasattr(user, "worker_profile"):
                q |= Q(worker=user.worker_profile)
            if hasattr(user, "employer_profile"):
                q |= Q(employer=user.employer_profile)
            qs = qs.filter(q) if q else qs.none()

        inv_status = request.query_params.get("status")
        if inv_status:
            qs = qs.filter(status=inv_status)
        order_id = request.query_params.get("order")
        if order_id:
            qs = qs.filter(order_id=order_id)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(OrderInvitationSerializer(page, many=True).data)

    @extend_schema(
        summary="Send Direct Invitation (Employer)",
        request=OrderInvitationCreateSerializer,
        responses={201: OrderInvitationSerializer},
        tags=["Invitations"],
    )
    def post(self, request):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        serializer = OrderInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inv = InvitationService.send_invitation(
            employer=employer,
            order_id=serializer.validated_data["order"],
            worker_id=serializer.validated_data["worker"],
            message=serializer.validated_data.get("message", ""),
            proposed_budget=serializer.validated_data.get("proposed_budget"),
            expires_in_days=serializer.validated_data.get("expires_in_days", 7),
        )
        return success_response(
            data=OrderInvitationSerializer(inv).data,
            message="Direct invitation sent.",
            status_code=status.HTTP_201_CREATED,
        )


class InvitationAcceptView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Accept Invitation (Worker)", responses={200: OrderInvitationSerializer}, tags=["Invitations"])
    def post(self, request, invitation_id):
        worker = get_object_or_404(WorkerProfile, user=request.user)
        inv = InvitationService.accept_invitation(invitation_id, worker)
        return success_response(data=OrderInvitationSerializer(inv).data, message="Invitation accepted. Order is now IN_PROGRESS.")


class InvitationRejectView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Reject Invitation (Worker)", responses={200: OrderInvitationSerializer}, tags=["Invitations"])
    def post(self, request, invitation_id):
        worker = get_object_or_404(WorkerProfile, user=request.user)
        inv = InvitationService.reject_invitation(invitation_id, worker)
        return success_response(data=OrderInvitationSerializer(inv).data, message="Invitation rejected.")


class InvitationCancelView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(summary="Cancel Invitation (Employer)", responses={200: OrderInvitationSerializer}, tags=["Invitations"])
    def post(self, request, invitation_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        inv = InvitationService.cancel_invitation(invitation_id, employer)
        return success_response(data=OrderInvitationSerializer(inv).data, message="Invitation cancelled.")
