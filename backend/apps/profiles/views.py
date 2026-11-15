from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, permissions, status
from rest_framework.views import APIView

from apps.accounts.permissions import IsEmployer, IsWorker
from apps.categories.serializers import WorkerCategoriesAssignSerializer, WorkerCategoryReadSerializer
from apps.categories.services import CategoryService
from apps.common.exceptions import BusinessRuleViolation
from apps.common.responses import success_response
from apps.profiles.filters import WorkerProfileFilter
from apps.profiles.models import EmployerProfile, VerificationStatus, WorkerPortfolioItem, WorkerProfile
from apps.profiles.serializers import (
    EmployerProfileSerializer,
    WorkerPortfolioItemSerializer,
    WorkerProfileSerializer,
    WorkerVerificationRequestSerializer,
)


class MyWorkerProfileView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Get My Worker Profile", responses={200: WorkerProfileSerializer}, tags=["Profiles"])
    def get(self, request):
        profile = get_object_or_404(
            WorkerProfile.objects.prefetch_related("worker_categories__category", "portfolio_items"),
            user=request.user,
        )
        return success_response(data=WorkerProfileSerializer(profile, context={"request": request}).data)

    @extend_schema(
        summary="Create My Worker Profile",
        request=WorkerProfileSerializer,
        responses={201: WorkerProfileSerializer},
        tags=["Profiles"],
    )
    def post(self, request):
        if WorkerProfile.objects.filter(user=request.user).exists():
            raise BusinessRuleViolation("Worker profile already exists. Use PATCH to update.", code="profile_exists")
        serializer = WorkerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(
            user=request.user,
            verification_status=VerificationStatus.UNSUBMITTED,
            is_verified=False,
        )
        return success_response(
            data=WorkerProfileSerializer(profile, context={"request": request}).data,
            message="Worker profile created.",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update My Worker Profile",
        request=WorkerProfileSerializer,
        responses={200: WorkerProfileSerializer},
        tags=["Profiles"],
    )
    def patch(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        serializer = WorkerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=WorkerProfileSerializer(profile, context={"request": request}).data,
            message="Worker profile updated.",
        )


class WorkerVerificationRequestView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(
        summary="Submit Worker Verification Request",
        description="Moves verification_status to PENDING for administrator review. Cannot self-verify.",
        request=WorkerVerificationRequestSerializer,
        responses={200: WorkerProfileSerializer},
        tags=["Profiles"],
    )
    def post(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        if profile.verification_status == VerificationStatus.VERIFIED:
            raise BusinessRuleViolation("Your worker profile is already verified.", code="already_verified")
        serializer = WorkerVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile.verification_status = VerificationStatus.PENDING
        profile.is_verified = False
        if serializer.validated_data.get("notes"):
            profile.verification_notes = serializer.validated_data["notes"]
        profile.save(update_fields=["verification_status", "is_verified", "verification_notes", "updated_at"])
        return success_response(
            data=WorkerProfileSerializer(profile, context={"request": request}).data,
            message="Verification request submitted for administrator review.",
        )


class WorkerPortfolioListCreateView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="List My Portfolio Items", responses={200: WorkerPortfolioItemSerializer(many=True)}, tags=["Profiles"])
    def get(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        items = profile.portfolio_items.all()
        return success_response(data=WorkerPortfolioItemSerializer(items, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Add Portfolio Item",
        request=WorkerPortfolioItemSerializer,
        responses={201: WorkerPortfolioItemSerializer},
        tags=["Profiles"],
    )
    def post(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        serializer = WorkerPortfolioItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(worker=profile)
        return success_response(
            data=WorkerPortfolioItemSerializer(item, context={"request": request}).data,
            message="Portfolio item added.",
            status_code=status.HTTP_201_CREATED,
        )


class WorkerPortfolioDetailView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(
        summary="Update Portfolio Item",
        request=WorkerPortfolioItemSerializer,
        responses={200: WorkerPortfolioItemSerializer},
        tags=["Profiles"],
    )
    def patch(self, request, item_id):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        item = get_object_or_404(WorkerPortfolioItem, id=item_id, worker=profile)
        serializer = WorkerPortfolioItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=WorkerPortfolioItemSerializer(item, context={"request": request}).data,
            message="Portfolio item updated.",
        )

    @extend_schema(
        summary="Delete Portfolio Item",
        responses={200: OpenApiResponse(description="Deleted")},
        tags=["Profiles"],
    )
    def delete(self, request, item_id):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        item = get_object_or_404(WorkerPortfolioItem, id=item_id, worker=profile)
        item.delete()
        return success_response(message="Portfolio item deleted.")


class MyWorkerCategoriesView(APIView):
    permission_classes = [IsWorker]

    @extend_schema(summary="Get My Assigned Categories", responses={200: WorkerCategoryReadSerializer(many=True)}, tags=["Profiles"])
    def get(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        qs = profile.worker_categories.select_related("category").filter(category__is_active=True)
        return success_response(data=WorkerCategoryReadSerializer(qs, many=True).data)

    @extend_schema(
        summary="Assign Worker Categories (Max 10)",
        request=WorkerCategoriesAssignSerializer,
        responses={200: WorkerCategoryReadSerializer(many=True)},
        tags=["Profiles"],
    )
    def put(self, request):
        profile = get_object_or_404(WorkerProfile, user=request.user)
        serializer = WorkerCategoriesAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned = CategoryService.update_worker_categories(profile, serializer.validated_data["categories"])
        return success_response(
            data=WorkerCategoryReadSerializer(assigned, many=True).data,
            message="Worker categories updated.",
        )


class MyEmployerProfileView(APIView):
    permission_classes = [IsEmployer]

    @extend_schema(summary="Get My Employer Profile", responses={200: EmployerProfileSerializer}, tags=["Profiles"])
    def get(self, request):
        profile = get_object_or_404(EmployerProfile, user=request.user)
        return success_response(data=EmployerProfileSerializer(profile, context={"request": request}).data)

    @extend_schema(
        summary="Create My Employer Profile",
        request=EmployerProfileSerializer,
        responses={201: EmployerProfileSerializer},
        tags=["Profiles"],
    )
    def post(self, request):
        if EmployerProfile.objects.filter(user=request.user).exists():
            raise BusinessRuleViolation("Employer profile already exists. Use PATCH to update.", code="profile_exists")
        serializer = EmployerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return success_response(
            data=EmployerProfileSerializer(profile, context={"request": request}).data,
            message="Employer profile created.",
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update My Employer Profile",
        request=EmployerProfileSerializer,
        responses={200: EmployerProfileSerializer},
        tags=["Profiles"],
    )
    def patch(self, request):
        profile = get_object_or_404(EmployerProfile, user=request.user)
        serializer = EmployerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=EmployerProfileSerializer(profile, context={"request": request}).data,
            message="Employer profile updated.",
        )


class WorkerDiscoveryListView(generics.ListAPIView):
    """Search, filter, and browse active non-anonymized workers."""

    permission_classes = [permissions.AllowAny]
    serializer_class = WorkerProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = WorkerProfileFilter
    search_fields = ["full_name", "bio", "location", "district", "skills"]
    ordering_fields = ["rating_avg", "experience_years", "hourly_rate", "completed_orders_count", "created_at"]
    ordering = ["-is_verified", "-rating_avg"]

    def get_queryset(self):
        return (
            WorkerProfile.objects.filter(user__is_active=True, user__account_status="ACTIVE", user__is_anonymized=False)
            .select_related("user")
            .prefetch_related("worker_categories__category", "portfolio_items")
            .distinct()
        )

    @extend_schema(summary="Search & Filter Workers", tags=["Marketplace Discovery"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class WorkerDiscoveryDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Worker Public Profile", responses={200: WorkerProfileSerializer}, tags=["Marketplace Discovery"])
    def get(self, request, worker_id):
        worker = get_object_or_404(
            WorkerProfile.objects.select_related("user").prefetch_related("worker_categories__category", "portfolio_items"),
            id=worker_id,
            user__is_active=True,
            user__account_status="ACTIVE",
            user__is_anonymized=False,
        )
        return success_response(data=WorkerProfileSerializer(worker, context={"request": request}).data)


class EmployerDiscoveryDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(summary="Get Employer Public Profile", responses={200: EmployerProfileSerializer}, tags=["Marketplace Discovery"])
    def get(self, request, employer_id):
        employer = get_object_or_404(
            EmployerProfile.objects.select_related("user"),
            id=employer_id,
            user__is_active=True,
            user__account_status="ACTIVE",
            user__is_anonymized=False,
        )
        return success_response(data=EmployerProfileSerializer(employer, context={"request": request}).data)
