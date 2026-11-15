from rest_framework import serializers
from apps.reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    reviewee_name = serializers.CharField(source="reviewee.full_name", read_only=True)
    order_title = serializers.CharField(source="order.title", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "order",
            "order_title",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "direction",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
    reviewee = serializers.UUIDField(required=False)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
