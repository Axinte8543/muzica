"""Fixture preparation for legacy API integration suites, not auth-security tests."""
from django.contrib.auth import get_user_model
from users.models import UserPrivacySettings


def verify_fixture_emails():
    for user in get_user_model().objects.all():
        UserPrivacySettings.objects.update_or_create(user=user, defaults={'email_verified': True})
