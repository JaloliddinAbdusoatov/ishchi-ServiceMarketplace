from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from apps.accounts.permissions import IsActiveAccount
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response
from apps.common.exceptions import BusinessRuleViolation
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewCreateSerializer, ReviewSerializer
from apps.reviews.services import ReviewService


class ReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsActiveAccount()]
        return [permissions.AllowAny()]

    @extend_schema(
        summary="List Reviews",
        parameters=[
            OpenApiParameter(name="reviewee", type=str, required=False),
            OpenApiParameter(name="reviewer", type=str, required=False),
            OpenApiParameter(name="order", type=str, required=False),
            OpenApiParameter(name="direction", type=str, required=False),
        ],
        responses={200: ReviewSerializer(many=True)},
        tags=["Reviews"],
    )
    def get(self, request):
        qs = Review.objects.select_related("order", "reviewer", "reviewee")
        for param, field in (
            ("reviewee", "reviewee_id"),
            ("reviewer", "reviewer_id"),
            ("order", "order_id"),
            ("direction", "direction"),
        ):
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ReviewSerializer(page, many=True).data)

    @extend_schema(
        summary="Submit Review for Completed Order",
        request=ReviewCreateSerializer,
        responses={201: ReviewSerializer},
        tags=["Reviews"],
    )
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = ReviewService.create_review(
            reviewer=request.user,
            order_id=serializer.validated_data["order"],
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data.get("comment", ""),
            reviewee_id=serializer.validated_data.get("reviewee"),
        )
        return success_response(
            data=ReviewSerializer(review).data,
            message="Review submitted successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ReviewEligibilityView(APIView):
    """Checks whether the authenticated user is eligible to submit a review for a given order."""

    permission_classes = [IsActiveAccount]

    @extend_schema(
        summary="Check Review Eligibility for Order",
        parameters=[OpenApiParameter(name="order", type=str, required=True)],
        responses={200: ReviewSerializer},
        tags=["Reviews"],
    )
    def get(self, request):
        from apps.orders.models import OrderStatus, ServiceOrder
        from apps.reviews.models import ReviewDirection

        order_id = request.query_params.get("order")
        if not order_id:
            return success_response(
                data={"eligible": False, "reason": "order query parameter is required.", "direction": None, "existing_review": None}
            )

        order = (
            ServiceOrder.objects.select_related("employer__user", "assigned_worker__user")
            .filter(id=order_id)
            .first()
        )
        if not order:
            return success_response(
                data={"eligible": False, "reason": "Order not found.", "direction": None, "existing_review": None}
            )
        try:
            direction, reviewee = ReviewService.participants(order, request.user)
        except BusinessRuleViolation as exc:
            return success_response(data={"eligible": False, "reason": str(exc.detail), "direction": None, "existing_review": None})
        existing = Review.objects.filter(order=order, reviewer=request.user, reviewee=reviewee).select_related("order", "reviewer", "reviewee").first()
        return success_response(data={
            "eligible": existing is None,
            "reason": "You have already reviewed this participant." if existing else "Eligible to submit review.",
            "direction": direction,
            "reviewee_id": str(reviewee.id),
            "reviewee_name": reviewee.full_name,
            "existing_review": ReviewSerializer(existing).data if existing else None,
        })