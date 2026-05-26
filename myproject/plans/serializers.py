from django.utils import timezone
from django.db.models import Q
from rest_framework import serializers

from .models import Plan, Purchase


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "code", "price", "duration_days", "created_at"]


class PurchaseCreateSerializer(serializers.ModelSerializer):
    plan_id = serializers.PrimaryKeyRelatedField(source="plan", queryset=Plan.objects.filter(is_active=True))

    class Meta:
        model = Purchase
        fields = ["id", "plan_id", "amount", "started_at", "expires_at", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        now = timezone.now()
        has_active_purchase = Purchase.objects.filter(
            user=user,
            is_active=True,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).exists()

        if has_active_purchase:
            raise serializers.ValidationError("User already has an active plan purchase.")

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Purchase.objects.create(user=user, **validated_data)


class PurchaseSerializer(serializers.ModelSerializer):
    plan = serializers.StringRelatedField()

    class Meta:
        model = Purchase
        fields = ["id", "plan", "amount", "started_at", "expires_at", "is_active", "created_at"]
