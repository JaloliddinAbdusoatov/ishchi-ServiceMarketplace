import django_filters
from apps.profiles.models import WorkerProfile


class WorkerProfileFilter(django_filters.FilterSet):
    category = django_filters.UUIDFilter(field_name="worker_categories__category_id")
    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")
    district = django_filters.CharFilter(field_name="district", lookup_expr="icontains")
    is_verified = django_filters.BooleanFilter(field_name="is_verified")
    is_available = django_filters.BooleanFilter(field_name="is_available")
    pricing_type = django_filters.CharFilter(field_name="pricing_type")
    min_rating = django_filters.NumberFilter(field_name="rating_avg", lookup_expr="gte")
    min_experience = django_filters.NumberFilter(field_name="experience_years", lookup_expr="gte")
    max_hourly_rate = django_filters.NumberFilter(field_name="hourly_rate", lookup_expr="lte")

    class Meta:
        model = WorkerProfile
        fields = [
            "category",
            "location",
            "district",
            "is_verified",
            "is_available",
            "pricing_type",
            "min_rating",
            "min_experience",
            "max_hourly_rate",
        ]
