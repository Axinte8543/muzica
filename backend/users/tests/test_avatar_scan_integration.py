import os
import uuid
import unittest

import boto3
from botocore.exceptions import ClientError
try:
    from celery.contrib.testing.worker import start_worker
except ImportError:
    start_worker = None
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from config.celery import app as celery_app
from users.models import AvatarScanStatus, UserPrivacySettings
from users.tasks import scan_avatar_object


try:
    _start_worker = start_worker
except Exception:
    _start_worker = None


User = get_user_model()


def _integration_enabled() -> bool:
	return os.environ.get('RUN_INTEGRATION_TESTS', '').strip() == '1'


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class AvatarScanIntegrationTests(TransactionTestCase):
	@unittest.skipUnless(_integration_enabled(), 'Integration tests disabled; set RUN_INTEGRATION_TESTS=1')
	@unittest.skipUnless(_start_worker is not None, 'celery.contrib.testing.worker is unavailable')
	def test_avatar_scan_end_to_end_with_redis_clamav_and_localstack(self):
		key = f'avatars/{self.user.id}/{uuid.uuid4().hex}.bin'
		self.s3.put_object(Bucket=self.bucket, Key=key, Body=b'clean avatar bytes')

		with _start_worker(celery_app, perform_ping_check=False, concurrency=1):
			result = scan_avatar_object.apply_async(args=[self.bucket, key, self.user.id])
			value = result.get(timeout=30)

		self.profile.refresh_from_db()
		self.assertEqual(self.profile.avatar_scan_status, AvatarScanStatus.CLEAN)
		self.assertTrue(self.profile.avatar_scanned_at)
		if isinstance(value, (list, tuple)):
			self.assertTrue(value[0])
		else:
			self.assertTrue(value)

	def setUp(self):
		required_env = [
			'AWS_S3_BUCKET_NAME',
			'AWS_S3_ENDPOINT_URL',
			'CLAMAV_HOST',
			'CLAMAV_PORT',
			'CELERY_BROKER_URL',
		]
		missing = [name for name in required_env if not str(getattr(settings, name, '') or '').strip()]
		if missing:
			self.skipTest(f'Missing integration env vars: {", ".join(missing)}')

		self.bucket = settings.AWS_S3_BUCKET_NAME
		self.s3 = boto3.client(
			's3',
			aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
			aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
			region_name=getattr(settings, 'AWS_REGION', None),
			endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
		)
		try:
			self.s3.create_bucket(Bucket=self.bucket)
		except ClientError:
			pass

		self.user = User.objects.create_user(username=f'integration-{uuid.uuid4().hex[:8]}', password='StrongPass123!')
		self.profile = UserPrivacySettings.objects.create(user=self.user)
