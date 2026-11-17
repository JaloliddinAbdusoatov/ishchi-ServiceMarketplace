from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.accounts.permissions import IsActiveAccount
from apps.common.exceptions import BusinessRuleViolation
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.favorites.models import FavoriteOrder, FavoriteWorker
from apps.favorites.serializers import (
    FavoriteOrderCreateSerializer,
    FavoriteOrderSerializer,
    FavoriteWorkerCreateSerializer,
    FavoriteWorkerSerializer,
)
from apps.orders.models import ServiceOrder
from apps.orders.access import visible_orders
from apps.profiles.models import WorkerProfile


class FavoriteWorkerListCreateView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="List Favorite Workers", responses={200: FavoriteWorkerSerializer(many=True)}, tags=["Favorites"])
    def get(self, request):
        qs = FavoriteWorker.objects.filter(
            user=request.user,
            worker__user__is_active=True,
            worker__user__account_status="ACTIVE",
            worker__user__is_anonymized=False,
        ).select_related("worker__user")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FavoriteWorkerSerializer(page, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Add Favorite Worker",
        request=FavoriteWorkerCreateSerializer,
        responses={201: FavoriteWorkerSerializer},
        tags=["Favorites"],
    )
    def post(self, request):
        serializer = FavoriteWorkerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        worker = get_object_or_404(
            WorkerProfile,
            id=serializer.validated_data["worker"],
            user__is_active=True,
            user__account_status="ACTIVE",
            user__is_anonymized=False,
        )
        if str(worker.user_id) == str(request.user.id):
            raise BusinessRuleViolation("You cannot favorite yourself.", code="cannot_favorite_self")
        fav, created = FavoriteWorker.objects.get_or_create(user=request.user, worker=worker)
        return success_response(
            data=FavoriteWorkerSerializer(fav, context={"request": request}).data,
            message="Worker added to favorites." if created else "Worker already in favorites.",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FavoriteWorkerDeleteView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="Remove Favorite Worker", responses={200: OpenApiResponse(description="Removed")}, tags=["Favorites"])
    def delete(self, request, worker_id):
        fav = get_object_or_404(FavoriteWorker, user=request.user, worker_id=worker_id)
        fav.delete()
        return success_response(message="Worker removed from favorites.")


class FavoriteOrderListCreateView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="List Favorite Orders", responses={200: FavoriteOrderSerializer(many=True)}, tags=["Favorites"])
    def get(self, request):
        qs = FavoriteOrder.objects.filter(user=request.user, order__in=visible_orders(request.user)).select_related("order__employer", "order__category")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FavoriteOrderSerializer(page, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Add Favorite Order",
        request=FavoriteOrderCreateSerializer,
        responses={201: FavoriteOrderSerializer},
        tags=["Favorites"],
    )
    def post(self, request):
        serializer = FavoriteOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = get_object_or_404(visible_orders(request.user), id=serializer.validated_data["order"])
        fav, created = FavoriteOrder.objects.get_or_create(user=request.user, order=order)
        return success_response(
            data=FavoriteOrderSerializer(fav, context={"request": request}).data,
            message="Order added to favorites." if created else "Order already in favorites.",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FavoriteOrderDeleteView(APIView):
    permission_classes = [IsActiveAccount]

    @extend_schema(summary="Remove Favorite Order", responses={200: OpenApiResponse(description="Removed")}, tags=["Favorites"])
    def delete(self, request, order_id):
        fav = get_object_or_404(FavoriteOrder, user=request.user, order_id=order_id)
        fav.delete()
        return success_response(message="Order removed from favorites.")
