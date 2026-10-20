from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import RevokedToken


class RevokingJWTAuthentication(JWTAuthentication):
	def get_validated_token(self, raw_token):
		token = super().get_validated_token(raw_token)
		jti = str(token.get('jti', '')).strip()
		if jti and RevokedToken.objects.filter(jti=jti).exists():
			raise exceptions.AuthenticationFailed('Token revoked')
		return token