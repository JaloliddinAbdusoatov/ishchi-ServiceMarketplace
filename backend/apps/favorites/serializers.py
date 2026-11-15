from rest_framework import serializers
from apps.favorites.models import FavoriteOrder, FavoriteWorker
from apps.orders.serializers import ServiceOrderSerializer
from apps.profiles.serializers import WorkerProfileSerializer


class FavoriteWorkerSerializer(serializers.ModelSerializer):
    worker_detail = WorkerProfileSerializer(source="worker", read_only=True)

    class Meta:
        model = FavoriteWorker
        fields = ["id", "worker", "worker_detail", "created_at"]
        read_only_fields = ["id", "worker_detail", "created_at"]


class FavoriteOrderSerializer(serializers.ModelSerializer):
    order_detail = ServiceOrderSerializer(source="order", read_only=True)

    class Meta:
        model = FavoriteOrder
        fields = ["id", "order", "order_detail", "created_at"]
        read_only_fields = ["id", "order_detail", "created_at"]


class FavoriteWorkerCreateSerializer(serializers.Serializer):
    worker = serializers.UUIDField()


class FavoriteOrderCreateSerializer(serializers.Serializer):
    order = serializers.UUIDField()
