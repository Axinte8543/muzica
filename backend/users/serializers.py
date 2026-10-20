from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db import transaction
import logging
import re

from .models import UserPrivacySettings, EmailVerificationToken, PasswordResetToken


User = get_user_model()
logger = logging.getLogger(__name__)


def validate_password_policy(password):
    pw = str(password or '')
    min_length = int(getattr(settings, 'PASSWORD_MIN_LENGTH', 8) or 8)
    checks = {
        'minLength': len(pw) >= min_length,
        'lowercase': bool(re.search(r'[a-z]', pw)),
        'uppercase': bool(re.search(r'[A-Z]', pw)),
        'number': bool(re.search(r'[0-9]', pw)),
        'special': bool(re.search(r"[!@#$%^&*()_+\-=[\]{};':\"\\|,.<>/?`~]", pw)),
    }
    blacklist = [str(value).strip().lower() for value in getattr(settings, 'PASSWORD_BLACKLIST', []) if str(value).strip()]
    if pw.lower() in blacklist:
        checks['blacklist'] = False
    if not all(checks.values()):
        raise ValidationError({'password': 'Parola nu îndeplinește cerințele minime.'})
    return pw


class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        from django.core.mail import send_mail
        import uuid

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data.get("email", ""),
                password=validated_data["password"],
            )
                                                            
            try:
                UserPrivacySettings.objects.get_or_create(user=user)
            except Exception:
                pass


            if user.email:
                token = EmailVerificationToken.objects.create(user=user, token=str(uuid.uuid4()))
                verification_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={token.token}"
                try:
                    send_mail(
                        subject="Verify your email",
                        message=f"Please verify your email by visiting: {verification_url}",
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as exc:
                    logger.warning("Verification email could not be sent for user %s: %s", user.username, exc)
            return user

    def validate(self, attrs):
        validate_password_policy(attrs.get('password', ''))
        return attrs


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


class AvatarScanStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPrivacySettings
        fields = [
            "avatar_scan_status",
            "avatar_scan_message",
            "avatar_url",
            "pending_avatar_url",
            "pending_avatar_key",
            "avatar_scan_requested_at",
            "avatar_scanned_at",
            "updated_at",
        ]
        read_only_fields = fields


class TOTPSetupSerializer(serializers.Serializer):
                                                            
    otpauth_url = serializers.CharField(read_only=True)
    secret = serializers.CharField(read_only=True)


class TOTPConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(write_only=True, required=False)
