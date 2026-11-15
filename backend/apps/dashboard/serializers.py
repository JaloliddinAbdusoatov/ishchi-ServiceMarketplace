from rest_framework import serializers


class AdminWorkerVerifySerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    notes = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)


class AdminUserSuspendSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class AdminOrderModerateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["CANCEL", "CLOSE"])
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)
