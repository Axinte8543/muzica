from django.conf import settings
from django.db import models


class UserPrivacySettings(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='privacy',
	)
	public_lists = models.BooleanField(default=True)
	public_activity = models.BooleanField(default=True)
	public_compatibility = models.BooleanField(default=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'User privacy settings'
		verbose_name_plural = 'User privacy settings'

	def __str__(self):
		return f"PrivacySettings(user_id={self.user_id})"
