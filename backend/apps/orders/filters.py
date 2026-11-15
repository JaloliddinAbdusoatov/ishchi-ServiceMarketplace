import django_filters
from apps.orders.models import ServiceOrder


class ServiceOrderFilter(django_filters.FilterSet):
    category = django_filters.UUIDFilter(field_name="category_id")
    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")
    district = django_filters.CharFilter(field_name="district", lookup_expr="icontains")
    budget_min = django_filters.NumberFilter(field_name="budget", lookup_expr="gte")
    budget_max = django_filters.NumberFilter(field_name="budget", lookup_expr="lte")
    budget_type = django_filters.CharFilter(field_name="budget_type")
    work_type = django_filters.CharFilter(field_name="work_type")
    status = django_filters.CharFilter(field_name="status")
    employer = django_filters.UUIDFilter(field_name="employer_id")

    class Meta:
        model = ServiceOrder
        fields = [
            "category",
            "location",
            "district",
            "budget_min",
            "budget_max",
            "budget_type",
            "work_type",
            "status",
            "employer",
        ]
