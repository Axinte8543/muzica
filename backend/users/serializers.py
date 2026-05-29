from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserPrivacySettings


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        return user


class SimilarUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    username = serializers.CharField()
    similarity = serializers.FloatField()
    common_genres = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    common_artists = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    common_albums = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )


class CompatibilitySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    similarity = serializers.FloatField()
    common_genres = serializers.ListField(child=serializers.CharField())
    common_artists = serializers.ListField(child=serializers.CharField())
    common_albums = serializers.ListField(child=serializers.CharField())


class UserSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class UserPrivacySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrivacySettings
        fields = ["public_lists", "public_activity", "public_compatibility", "updated_at"]
        read_only_fields = ["updated_at"]
