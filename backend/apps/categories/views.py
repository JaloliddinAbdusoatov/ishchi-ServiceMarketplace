from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from apps.accounts.permissions import IsAdminOrReadOnly, IsAdminUserRole
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer, CategoryWriteSerializer
from apps.categories.services import CategoryService
from apps.common.exceptions import BusinessRuleViolation
from apps.common.pagination import StandardResultsSetPagination
from apps.common.responses import success_response


class CategoryListCreateView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        summary="List & Search Categories",
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="parent", type=str, required=False),
            OpenApiParameter(name="root_only", type=bool, required=False),
            OpenApiParameter(name="include_inactive", type=bool, required=False),
        ],
        responses={200: CategorySerializer(many=True)},
        tags=["Categories"],
    )
    def get(self, request):
        qs = Category.objects.select_related("parent").prefetch_related("children").order_by("display_order", "name")
        include_inactive = request.query_params.get("include_inactive", "").lower() in ("true", "1")
        if not (include_inactive and request.user.is_authenticated and getattr(request.user, "is_admin_user", False)):
            qs = qs.filter(is_active=True)

        if request.query_params.get("root_only", "").lower() in ("true", "1"):
            qs = qs.filter(parent__isnull=True)

        parent_id = request.query_params.get("parent")
        if parent_id:
            qs = qs.filter(parent_id=parent_id)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(name_uz__icontains=search)
                | Q(name_ru__icontains=search)
                | Q(name_en__icontains=search)
                | Q(slug__icontains=search)
                | Q(description__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(CategorySerializer(page, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Create Category (Admin Only)",
        request=CategoryWriteSerializer,
        responses={201: CategorySerializer},
        tags=["Categories"],
    )
    def post(self, request):
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return success_response(
            data=CategorySerializer(category, context={"request": request}).data,
            message="Category created.",
            status_code=status.HTTP_201_CREATED,
        )


class CategoryDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(summary="Get Category Detail", responses={200: CategorySerializer}, tags=["Categories"])
    def get(self, request, category_id):
        qs = Category.objects.select_related("parent").prefetch_related("children")
        if not (request.user.is_authenticated and getattr(request.user, "is_admin_user", False)):
            qs = qs.filter(is_active=True)
        category = get_object_or_404(qs, id=category_id)
        return success_response(data=CategorySerializer(category, context={"request": request}).data)

    @extend_schema(
        summary="Update Category (Admin Only)",
        request=CategoryWriteSerializer,
        responses={200: CategorySerializer},
        tags=["Categories"],
    )
    def patch(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        serializer = CategoryWriteSerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = CategoryService.update_category(category, serializer.validated_data)
        return success_response(
            data=CategorySerializer(updated, context={"request": request}).data,
            message="Category updated.",
        )

    @extend_schema(
        summary="Delete Category (Admin Only)",
        responses={200: OpenApiResponse(description="Category deleted")},
        tags=["Categories"],
    )
    def delete(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        if category.children.exists():
            raise BusinessRuleViolation("Cannot delete a category that has child categories.", code="has_children")
        if category.orders.exists():
            raise BusinessRuleViolation("Cannot delete a category referenced by orders. Deactivate it instead.", code="category_in_use")
        category.worker_assignments.all().delete()
        category.delete()
        return success_response(message="Category deleted.")


class CategoryDeactivateView(APIView):
    permission_classes = [IsAdminUserRole]

    @extend_schema(
        summary="Deactivate Category (Admin Only)",
        description="Deactivates category and removes active worker assignments referencing it.",
        responses={200: CategorySerializer},
        tags=["Categories"],
    )
    def post(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        updated = CategoryService.deactivate_category(category)
        return success_response(
            data=CategorySerializer(updated, context={"request": request}).data,
            message="Category deactivated and active worker assignments cleared.",
        )
