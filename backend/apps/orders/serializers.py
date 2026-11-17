from rest_framework import serializers
from django.urls import reverse
from apps.common.validators import validate_image_file
from apps.orders.models import OrderImage, OrderStatus, ServiceOrder


class OrderImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(validators=[validate_image_file])

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = reverse("api-v1:orders-image-content", kwargs={
            "order_id": instance.order_id, "image_id": instance.pk})
        return data

    class Meta:
        model = OrderImage
        fields = ["id", "image", "caption", "display_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class ServiceOrderSerializer(serializers.ModelSerializer):
    employer_name = serializers.SerializerMethodField()
    employer_user_id = serializers.UUIDField(source="employer.user_id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    assigned_worker_name = serializers.CharField(source="assigned_worker.full_name", read_only=True, default=None)
    assigned_worker_user_id = serializers.UUIDField(source="assigned_worker.user_id", read_only=True, default=None)
    images = OrderImageSerializer(many=True, read_only=True)
    applications_count = serializers.IntegerField(source="applications.count", read_only=True)
    hired_worker_count = serializers.IntegerField(read_only=True)
    team = serializers.SerializerMethodField()

    def get_team(self, obj):
        return [{"id": str(w.id), "user_id": str(w.user_id), "name": w.full_name} for w in obj.get_hired_workers()]

    class Meta:
        model = ServiceOrder
        fields = [
            "id",
            "employer",
            "employer_user_id",
            "employer_name",
            "category",
            "category_name",
            "assigned_worker",
            "assigned_worker_user_id",
            "assigned_worker_name",
            "capacity", "hired_worker_count", "team",
            "title",
            "description",
            "budget",
            "budget_type",
            "location",
            "district",
            "address",
            "work_type",
            "deadline",
            "start_date",
            "status",
            "payment_status",
            "images",
            "applications_count",
            "published_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_employer_name(self, obj):
        if obj.employer.employer_type == "COMPANY" and obj.employer.company_name:
            return obj.employer.company_name
        return obj.employer.full_name


class ServiceOrderCreateSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(min_value=1, max_value=50, default=1)
    status = serializers.ChoiceField(
        choices=[OrderStatus.DRAFT, OrderStatus.PUBLISHED],
        required=False,
        default=OrderStatus.DRAFT,
    )

    class Meta:
        model = ServiceOrder
        fields = [
            "category",
            "capacity",
            "title",
            "description",
            "budget",
            "budget_type",
            "location",
            "district",
            "address",
            "work_type",
            "deadline",
            "start_date",
            "status",
        ]

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be strictly greater than zero.")
        return value


class ServiceOrderUpdateSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(min_value=1, max_value=50, required=False)
    class Meta:
        model = ServiceOrder
        fields = [
            "category",
            "capacity",
            "title",
            "description",
            "budget",
            "budget_type",
            "location",
            "district",
            "address",
            "work_type",
            "deadline",
            "start_date",
        ]

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be strictly greater than zero.")
        return value
