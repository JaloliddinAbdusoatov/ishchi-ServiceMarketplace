from rest_framework import serializers
from apps.categories.serializers import WorkerCategoryReadSerializer
from apps.common.validators import UZ_PHONE_REGEX
from apps.profiles.models import EmployerProfile, EmployerType, WorkerPortfolioItem, WorkerProfile


class WorkerPortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerPortfolioItem
        fields = [
            "id",
            "title",
            "description",
            "image",
            "project_url",
            "completed_year",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class WorkerProfileSerializer(serializers.ModelSerializer):
    categories = WorkerCategoryReadSerializer(source="worker_categories", many=True, read_only=True)
    portfolio_items = WorkerPortfolioItemSerializer(many=True, read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = WorkerProfile
        fields = [
            "id",
            "user_id",
            "full_name",
            "bio",
            "phone_number",
            "photo",
            "location",
            "district",
            "skills",
            "experience_years",
            "experience_description",
            "pricing_type",
            "hourly_rate",
            "fixed_rate_from",
            "is_available",
            "verification_status",
            "is_verified",
            "verification_notes",
            "verified_at",
            "rating_avg",
            "review_count",
            "completed_orders_count",
            "categories",
            "portfolio_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "verification_status",
            "is_verified",
            "verification_notes",
            "verified_at",
            "rating_avg",
            "review_count",
            "completed_orders_count",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated and (user.pk == instance.user_id or user.is_admin_user)):
            data["verification_notes"] = ""
        if not (request and getattr(request.user, "is_authenticated", False)):
            data["phone_number"] = None
            data["verification_notes"] = ""
        return data

    def validate_phone_number(self, value):
        if value and not UZ_PHONE_REGEX.match(value):
            raise serializers.ValidationError("Phone number must match +998XXXXXXXXX.")
        return value

    def validate_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a JSON array of strings.")
        cleaned = [str(s).strip() for s in value if str(s).strip()]
        if len(cleaned) > 30:
            raise serializers.ValidationError("At most 30 skills can be listed.")
        return cleaned

    def validate(self, attrs):
        # Explicitly reject privilege-escalation attempts in payload
        forbidden_keys = {"is_verified", "verification_status", "verified_by", "verified_at", "rating_avg", "review_count"}
        raw_keys = set(getattr(self, "initial_data", {}).keys())
        attempted = forbidden_keys.intersection(raw_keys)
        if attempted:
            raise serializers.ValidationError(
                {k: "This field is system/admin controlled and cannot be modified by the worker." for k in sorted(attempted)}
            )
        return attrs


class WorkerVerificationRequestSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")


class EmployerProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "user_id",
            "employer_type",
            "full_name",
            "company_name",
            "bio",
            "phone_number",
            "email",
            "photo",
            "location",
            "district",
            "address",
            "rating_avg",
            "review_count",
            "posted_orders_count",
            "completed_orders_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "rating_avg",
            "review_count",
            "posted_orders_count",
            "completed_orders_count",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not (request and getattr(request.user, "is_authenticated", False)):
            data["phone_number"] = None
            data["email"] = None
            data["address"] = ""
        return data

    def validate(self, attrs):
        emp_type = attrs.get("employer_type", getattr(self.instance, "employer_type", EmployerType.INDIVIDUAL))
        company_name = attrs.get("company_name", getattr(self.instance, "company_name", ""))
        if emp_type == EmployerType.COMPANY and not (company_name and company_name.strip()):
            raise serializers.ValidationError({"company_name": "Company name is required when employer_type is COMPANY."})
        return attrs
