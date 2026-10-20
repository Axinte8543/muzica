from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class AvatarScanStatus(models.TextChoices):
	IDLE = 'idle', 'Idle'
	PENDING = 'pending', 'Pending'
	CLEAN = 'clean', 'Clean'
	REJECTED = 'rejected', 'Rejected'
	FAILED = 'failed', 'Failed'


class UserPrivacySettings(models.Model):
	user = models.OneToOneField(
	 settings.AUTH_USER_MODEL,
	 on_delete=models.CASCADE,
	 related_name='privacy',
	)
	public_lists = models.BooleanField(default=True)
	public_activity = models.BooleanField(default=True)
	public_compatibility = models.BooleanField(default=True)

                                                                      
	email_verified = models.BooleanField(default=False)

                                                                           
	avatar_url = models.URLField(null=True, blank=True)
	avatar_scan_status = models.CharField(max_length=16, choices=AvatarScanStatus.choices, default=AvatarScanStatus.IDLE)
	pending_avatar_url = models.URLField(null=True, blank=True)
	pending_avatar_key = models.CharField(max_length=512, null=True, blank=True)
	avatar_scan_message = models.CharField(max_length=255, blank=True, default='')
	avatar_scan_requested_at = models.DateTimeField(null=True, blank=True)
	avatar_scanned_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'User privacy settings'
		verbose_name_plural = 'User privacy settings'

	def __str__(self):
		return f"PrivacySettings(user_id={self.user_id})"


class EmailVerificationToken(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_tokens')
	token = models.CharField(max_length=128, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	used = models.BooleanField(default=False)

	def is_expired(self):
                              
		return self.created_at + timedelta(days=7) < timezone.now()


class PasswordResetToken(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reset_tokens')
	token = models.CharField(max_length=128, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	used = models.BooleanField(default=False)

	def is_expired(self):
                                            
		return self.created_at + timedelta(days=1) < timezone.now()


class EmailChangeRequest(models.Model):
                                                                        
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_change_requests')
	new_email = models.EmailField()
	token = models.CharField(max_length=128, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	used = models.BooleanField(default=False)

	def is_expired(self):
                       
		return self.created_at + timedelta(days=7) < timezone.now()


class UserTOTP(models.Model):
                                                  
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='totp')
	secret = models.CharField(max_length=128, null=True, blank=True)
	enabled = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
                                                                                  
	backup_codes = models.TextField(null=True, blank=True)

	def __str__(self):
		return f"UserTOTP(user_id={self.user_id}, enabled={self.enabled})"


class WebAuthnCredential(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='webauthn_credentials')
	credential_id = models.BinaryField()             
	public_key = models.BinaryField()
	sign_count = models.BigIntegerField(default=0)
	transports = models.CharField(max_length=200, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'credential_id')

	def __str__(self):
		return f"WebAuthnCredential(user_id={self.user_id}, created={self.created_at})"


class UserSession(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
	jwt_jti = models.CharField(max_length=255, null=True, blank=True)
	access_jti = models.CharField(max_length=255, null=True, blank=True)
	ip = models.CharField(max_length=45, null=True, blank=True)
	user_agent = models.CharField(max_length=512, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	last_active = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"UserSession(user_id={self.user_id}, ip={self.ip}, ua={self.user_agent})"


class RevokedToken(models.Model):
	jti = models.CharField(max_length=255, unique=True)
	revoked_at = models.DateTimeField(auto_now_add=True)
	reason = models.CharField(max_length=255, null=True, blank=True)

	def __str__(self):
		return f"RevokedToken(jti={self.jti})"
