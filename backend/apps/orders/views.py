from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import filters, generics, permissions, status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import APIView

from apps.accounts.permissions import IsEmployer
from apps.common.exceptions import BusinessRuleViolation, ForbiddenActionError
from apps.common.responses import success_response
from apps.orders.filters import ServiceOrderFilter
from apps.orders.models import OrderImage, OrderStatus, ServiceOrder
from apps.orders.serializers import (
    OrderImageSerializer,
    ServiceOrderCreateSerializer,
    ServiceOrderSerializer,
    ServiceOrderUpdateSerializer,
)
from apps.orders.services import OrderService
from apps.profiles.models import EmployerProfile


class ServiceOrderListCreateView(generics.ListCreateAPIView):
    """
    GET: Browse/search/filter published orders (or employer's own orders with ?mine=true).
    POST: Create a new service order (Employer only).
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ServiceOrderFilter
    search_fields = ["title", "description", "location", "district", "category__name"]
    ordering_fields = ["budget", "created_at", "published_at", "deadline"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsEmployer()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ServiceOrderCreateSerializer
        return ServiceOrderSerializer

    def get_queryset(self):
        qs = ServiceOrder.objects.select_related("employer__user", "category", "assigned_worker__user").prefetch_related("images")
        user = self.request.user
        mine = self.request.query_params.get("mine", "").lower() in ("true", "1")
        assigned = self.request.query_params.get("assigned_to_me", "").lower() in ("true", "1")

        if (mine or assigned) and not user.is_authenticated:
            raise NotAuthenticated("Authentication required for private order filters.")

        if mine and user.is_employer and hasattr(user, "employer_profile"):
            return qs.filter(employer=user.employer_profile)

        if assigned and user.is_worker and hasattr(user, "worker_profile"):
            return qs.filter(Q(assigned_worker=user.worker_profile) | Q(assigned_workers=user.worker_profile)).distinct()

        if user.is_authenticated and getattr(user, "is_admin_user", False):
            return qs

        return qs.filter(status=OrderStatus.PUBLISHED, employer__user__is_active=True, employer__user__account_status="ACTIVE", employer__user__is_anonymized=False)

    @extend_schema(
        summary="List & Filter Service Orders",
        parameters=[
            OpenApiParameter(name="mine", type=bool, required=False, description="Employer: list my own orders"),
            OpenApiParameter(name="assigned_to_me", type=bool, required=False, description="Worker: list orders assigned to me"),
        ],
        tags=["Orders"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create Service Order (Employer Only)",
        request=ServiceOrderCreateSerializer,
        responses={201: ServiceOrderSerializer},
        tags=["Orders"],
    )
    def post(self, request, *args, **kwargs):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        serializer = ServiceOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.create_order(employer, serializer.validated_data)
        return success_response(
            data=ServiceOrderSerializer(order, context={"request": request}).data,
            message="Service order created.",
            status_code=status.HTTP_201_CREATED,
        )


class ServiceOrderDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def _get_accessible_order(self, request, order_id) -> ServiceOrder:
        order = get_object_or_404(
            ServiceOrder.objects.select_related("employer__user", "category", "assigned_worker__user").prefetch_related("images"),
            id=order_id,
        )
        user = request.user
        if order.status == OrderStatus.PUBLISHED and order.employer.user.is_active and order.employer.user.account_status == "ACTIVE" and not order.employer.user.is_anonymized:
            return order
        if not user.is_authenticated:
            raise NotAuthenticated("Authentication required to view non-published orders.")
        is_owner = str(order.employer.user_id) == str(user.id)
        is_assigned = any(str(worker.user_id) == str(user.id) for worker in order.get_hired_workers())
        is_admin = getattr(user, "is_admin_user", False)
        if order.status in (OrderStatus.DRAFT, OrderStatus.PAUSED) and not (is_owner or is_admin):
            raise ForbiddenActionError("You do not have access to this draft/paused order.")
        if order.status not in (OrderStatus.PUBLISHED,) and not (is_owner or is_assigned or is_admin):
            # Allow applicants who applied to this order to view its detail
            has_applied = hasattr(user, "worker_profile") and order.applications.filter(worker=user.worker_profile).exists()
            has_invited = hasattr(user, "worker_profile") and order.invitations.filter(worker=user.worker_profile).exists()
            if not (has_applied or has_invited):
                raise ForbiddenActionError("You do not have permission to view this order.")
        return order

    @extend_schema(summary="Get Service Order Detail", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def get(self, request, order_id):
        order = self._get_accessible_order(request, order_id)
        return success_response(data=ServiceOrderSerializer(order, context={"request": request}).data)

    @extend_schema(
        summary="Edit Own Service Order (Employer Only)",
        request=ServiceOrderUpdateSerializer,
        responses={200: ServiceOrderSerializer},
        tags=["Orders"],
    )
    def patch(self, request, order_id):
        if not request.user.is_employer:
            raise ForbiddenActionError("Only employers can edit orders.")
        employer = get_object_or_404(EmployerProfile, user=request.user)
        serializer = ServiceOrderUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        order = OrderService.update_order(order_id, employer, serializer.validated_data)
        return success_response(
            data=ServiceOrderSerializer(order, context={"request": request}).data,
            message="Service order updated.",
        )

    @extend_schema(
        summary="Delete Own Draft Order (Employer Only)",
        responses={200: OpenApiResponse(description="Draft order deleted")},
        tags=["Orders"],
    )
    def delete(self, request, order_id):
        if not request.user.is_employer:
            raise ForbiddenActionError("Only employers can delete orders.")
        employer = get_object_or_404(EmployerProfile, user=request.user)
        OrderService.delete_order(order_id, employer)
        return success_response(message="Draft order deleted.")


class OrderStatusActionBaseView(APIView):
    permission_classes = [IsEmployer]
    action_method = None
    success_msg = ""

    def post(self, request, order_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        fn = getattr(OrderService, self.action_method)
        order = fn(order_id, employer)
        return success_response(
            data=ServiceOrderSerializer(order, context={"request": request}).data,
            message=self.success_msg,
        )


class OrderPublishView(OrderStatusActionBaseView):
    action_method = "publish_order"
    success_msg = "Service order published."

    @extend_schema(summary="Publish Order", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def post(self, request, order_id):
        return super().post(request, order_id)


class OrderPauseView(OrderStatusActionBaseView):
    action_method = "pause_order"
    success_msg = "Service order paused."

    @extend_schema(summary="Pause Order", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def post(self, request, order_id):
        return super().post(request, order_id)


class OrderCancelView(OrderStatusActionBaseView):
    action_method = "cancel_order"
    success_msg = "Service order cancelled."

    @extend_schema(summary="Cancel Order", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def post(self, request, order_id):
        return super().post(request, order_id)


class OrderCloseView(OrderStatusActionBaseView):
    action_method = "close_order"
    success_msg = "Service order closed."

    @extend_schema(summary="Close Order", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def post(self, request, order_id):
        return super().post(request, order_id)


class OrderCompleteView(OrderStatusActionBaseView):
    action_method = "complete_order"
    success_msg = "Service order marked as completed."

    @extend_schema(summary="Complete Order", responses={200: ServiceOrderSerializer}, tags=["Orders"])
    def post(self, request, order_id):
        return super().post(request, order_id)


class OrderImageUploadView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(
        summary="Upload Image to Order",
        request=OrderImageSerializer,
        responses={201: OrderImageSerializer},
        tags=["Orders"],
    )
    def post(self, request, order_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        order = get_object_or_404(ServiceOrder, id=order_id, employer=employer)
        if order.images.count() >= 10:
            raise BusinessRuleViolation("An order can have at most 10 images.", code="max_images_exceeded")
        serializer = OrderImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        img = serializer.save(order=order)
        return success_response(
            data=OrderImageSerializer(img, context={"request": request}).data,
            message="Order image uploaded.",
            status_code=status.HTTP_201_CREATED,
        )


class OrderImageDeleteView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(summary="Delete Order Image", responses={200: OpenApiResponse(description="Deleted")}, tags=["Orders"])
    def delete(self, request, order_id, image_id):
        employer = get_object_or_404(EmployerProfile, user=request.user)
        order = get_object_or_404(ServiceOrder, id=order_id, employer=employer)
        img = get_object_or_404(OrderImage, id=image_id, order=order)
        img.delete()
        return success_response(message="Order image deleted.")
