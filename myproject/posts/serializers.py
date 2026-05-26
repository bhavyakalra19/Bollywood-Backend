from rest_framework import serializers

from .models import Genders, Location, Post, Productions


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name"]




class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genders
        fields = ["id", "name"]


class PostListSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()
    location_option = LocationSerializer(read_only=True)
    # production_type removed
    genders = GenderSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "created_by",
            "title",
            "location_option",
            "genders",
            "min_age",
            "max_age",
            "description",
            "requirements",
            "is_active",
            "created_at",
            "updated_at",
            "is_saved",
            "is_applied",
            "phone_number"
        ]

    def get_is_saved(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.saved_by.filter(user=request.user).exists()

    def get_is_applied(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.applications.filter(user=request.user).exists()
