from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.shortcuts import get_object_or_404

from .serializers import (
 CompatibilitySerializer,
 AvatarScanStatusSerializer,
 RegisterSerializer,
 SimilarUserSerializer,
 UserSearchResultSerializer,
 validate_password_policy,
)
from rest_framework import permissions
from rest_framework.parsers import JSONParser
from .models import EmailVerificationToken, PasswordResetToken
from .models import EmailChangeRequest
from .models import UserTOTP
try:
	import boto3
except Exception:
	boto3 = None
import uuid
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
import pyotp
import hashlib
import secrets
import socket
import struct
import time
import json
import urllib.parse
import urllib.request
from io import BytesIO
from fido2.server import Fido2Server
from fido2.utils import websafe_encode, websafe_decode
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from interactions.similarity import common_taste_details, compatibility_payload, similar_users_for
from interactions.views import _audit_sensitive_action
from .security_events import emit_security_signal

from interactions.models import AlbumRating, AlbumReview, FriendRequest, UserActivity
from .models import RevokedToken, UserPrivacySettings, UserSession, AvatarScanStatus
from interactions.profile import profile_stats_payload_for
from interactions.serializers import (
 MyAlbumRatingSerializer,
 MyAlbumReviewSerializer,
 ProfileStatsSerializer,
 UserActivitySerializer,
)


def _parse_limit(raw: str, *, default: int, max_value: int) -> int:
	raw_s = str(raw or '').strip()
	try:
		limit = int(raw_s) if raw_s else int(default)
	except ValueError:
		limit = int(default)
	return max(1, min(int(limit), int(max_value)))


def _token_jti(token) -> str:
	try:
		return str(token.get('jti', '')).strip()
	except Exception:
		return ''


def _revoke_jti(jti: str, *, reason: str = '') -> None:
	jti = str(jti or '').strip()
	if not jti:
		return
	RevokedToken.objects.get_or_create(jti=jti, defaults={'reason': reason[:255] or None})
	emit_security_signal('token_revoked', severity='warning', jti=jti, reason=reason[:255] or '')


def _session_payload(session: UserSession, *, current_jti: str = '') -> dict:
	return {
	 'id': session.id,
	 'jwt_jti': session.jwt_jti,
	 'access_jti': session.access_jti,
	 'ip': session.ip,
	 'user_agent': session.user_agent,
	 'created_at': session.created_at,
	 'last_active': session.last_active,
	 'is_current': bool(current_jti and current_jti in {session.jwt_jti, session.access_jti}),
	}


def _record_session(*, user, request, refresh_token, access_token) -> UserSession:
	refresh_jti = _token_jti(refresh_token)
	access_jti = _token_jti(access_token)
	user_agent = str(request.META.get('HTTP_USER_AGENT', '') or '')[:512]
	ip = str(request.META.get('REMOTE_ADDR', '') or '')[:45]
	return UserSession.objects.create(
	 user=user,
	 jwt_jti=refresh_jti,
	 access_jti=access_jti,
	 ip=ip,
	 user_agent=user_agent,
	)


def _revoke_session(session: UserSession, *, reason: str = '') -> None:
	_revoke_jti(session.jwt_jti, reason=reason)
	_revoke_jti(session.access_jti, reason=reason)
	session.delete()


def _revoke_user_sessions(user, *, reason: str = '') -> int:
	count = 0
	for session in list(UserSession.objects.filter(user=user)):
		_revoke_session(session, reason=reason)
		count += 1
	return count


def _is_email_verified(user) -> bool:
	try:
		profile, _ = UserPrivacySettings.objects.get_or_create(user=user)
		return bool(profile.email_verified)
	except Exception:
		return False


def _email_not_verified_response():
	return Response(
	 {'detail': 'Contul nu este verificat momentan. Verifică emailul trimis înainte să te autentifici.'},
	 status=403,
	)


def _security_setting(name: str, default):
	return getattr(settings, name, default)


def _security_cache_key(prefix: str, user_id: int, extra: str = '') -> str:
	extra_part = f":{extra}" if extra else ''
	return f"security:{prefix}:{user_id}{extra_part}"


def _normalize_user_agent(raw: str) -> str:
	ua = ' '.join(str(raw or '').split())
	return ua[:512]


def _client_ip(request) -> str:
	forwarded = str(request.META.get('HTTP_X_FORWARDED_FOR', '') or '').split(',')[0].strip()
	if forwarded:
		return forwarded[:45]
	return str(request.META.get('REMOTE_ADDR', '') or '')[:45]


def _geoip_country_code(ip: str) -> str:
	ip = str(ip or '').strip()
	if not ip:
		return ''
	geoip_path = str(
	 getattr(settings, 'GEOIP2_COUNTRY_DB_PATH', '')
	 or getattr(settings, 'GEOIP2_DB_PATH', '')
	 or getattr(settings, 'GEOIP_DB_PATH', '')
	 or ''
	).strip()
	if not geoip_path:
		return ''
	try:
		from geoip2.database import Reader
	except Exception:
		return ''
	try:
		with Reader(geoip_path) as reader:
			response = reader.country(ip)
			return str(getattr(response.country, 'iso_code', '') or '').strip().upper()
	except Exception:
		return ''


def _is_login_locked(user, *, ip: str) -> tuple[bool, str | None]:
	lock_key = _security_cache_key('login-lock', user.id, ip)
	lock_until = cache.get(lock_key)
	if not lock_until:
		return False, None
	if float(lock_until) <= time.time():
		cache.delete(lock_key)
		return False, None
	return True, lock_key


def _mark_login_failure(user, *, ip: str, username: str, request=None) -> tuple[bool, int]:
                                                         
	failure_key = _security_cache_key('login-failures', user.id, ip)
	locked_key = _security_cache_key('login-lock', user.id, ip)
	failures = int(cache.get(failure_key, 0)) + 1
	cache.set(failure_key, failures, timeout=3600)
	threshold = int(_security_setting('LOGIN_LOCK_THRESHOLD', 5))
	duration = int(_security_setting('LOGIN_LOCK_DURATION_SECONDS', 900))
	if failures >= threshold:
		cache.set(locked_key, time.time() + duration, timeout=duration)
		if request is not None:
			_alert_login_lockout(user=user, request=request, failures=failures)
		return True, failures
	return False, failures


def _clear_login_failures(user, *, ip: str) -> None:
	cache.delete(_security_cache_key('login-failures', user.id, ip))
	cache.delete(_security_cache_key('login-lock', user.id, ip))


def _detect_login_anomaly(user, *, request, ip: str, user_agent: str) -> dict:
	previous_sessions = list(UserSession.objects.filter(user=user).order_by('-last_active')[:25])
	known_ips = {str(session.ip or '').strip() for session in previous_sessions if session.ip}
	known_uas = {str(session.user_agent or '').strip() for session in previous_sessions if session.user_agent}
	current_country = _geoip_country_code(ip)
	previous_country = ''
	for session in previous_sessions:
		candidate_country = _geoip_country_code(str(session.ip or '').strip())
		if candidate_country:
			previous_country = candidate_country
			break
	return {
	 'is_new_ip': ip not in known_ips,
	 'is_new_device': user_agent not in known_uas,
	 'country_changed': bool(previous_country and current_country and previous_country != current_country),
	 'known_sessions': len(previous_sessions),
	 'current_country': current_country,
	 'previous_country': previous_country,
	}


def _send_security_email(user, *, subject: str, message: str) -> None:
	if not getattr(settings, 'SECURITY_EMAIL_ALERTS_ENABLED', True):
		return
	email = str(getattr(user, 'email', '') or '').strip()
	if not email:
		return
	try:
		send_mail(
		 subject=subject,
		 message=message,
		 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
		 recipient_list=[email],
		 fail_silently=True,
		)
	except Exception:
		pass


def _security_summary(request) -> str:
	return (
	 f"IP: {_client_ip(request)}\n"
	 f"User-Agent: {_normalize_user_agent(request.META.get('HTTP_USER_AGENT', ''))}\n"
	 f"Time: {timezone.now().isoformat()}"
	)


def _alert_login_success(user, *, request, anomaly: dict | None = None) -> None:
	parts = ["A new login to your account was just completed."]
	if anomaly:
		if anomaly.get('is_new_ip'):
			parts.append('The login came from a new IP address.')
		if anomaly.get('is_new_device'):
			parts.append('The login came from a new device or browser.')
		if anomaly.get('country_changed'):
			parts.append('The login appears to come from a different country.')
	parts.append('If this was not you, change your password and revoke active sessions immediately.')
	parts.append('')
	parts.append(_security_summary(request))
	_send_security_email(user, subject='New login on your account', message='\n'.join(parts))


def _alert_sensitive_change(user, *, subject: str, details: str, request=None) -> None:
	message = [details, '']
	if request is not None:
		message.append(_security_summary(request))
	_send_security_email(user, subject=subject, message='\n'.join(message))

                                                         
	try:
		_audit_sensitive_action(actor=user, action_type='metadata_suggestion_decided', target_type='account_security', target_id=user.id, summary=subject[:255], metadata={'details': details})
	except Exception:
		pass


def _alert_login_lockout(user, *, request, failures: int) -> None:
	emit_security_signal(
	 'login_lockout',
	 severity='warning',
	 user_id=user.id,
	 failures=failures,
	 ip=_client_ip(request),
	 user_agent=_normalize_user_agent(request.META.get('HTTP_USER_AGENT', '')),
	)
	_send_security_email(
	 user,
	 subject='Login cooldown activated',
	 message=(
	  f'We detected {failures} failed login attempts and temporarily locked logins for this account.\n\n'
	  f'If this was not you, review active sessions and change your password.\n\n'
	  f'{_security_summary(request)}'
	 ),
	)


def _note_successful_login(user, *, request, refresh_token, access_token) -> None:
	ip = _client_ip(request)
	user_agent = _normalize_user_agent(request.META.get('HTTP_USER_AGENT', ''))
	anomaly = _detect_login_anomaly(
	 user,
	 request=request,
	 ip=ip,
	 user_agent=user_agent,
	)
	_record_session(user=user, request=request, refresh_token=refresh_token, access_token=access_token)
	is_anomalous = bool(anomaly.get('is_new_ip') or anomaly.get('is_new_device') or anomaly.get('country_changed'))
	if is_anomalous:
		emit_security_signal(
		 'login_anomaly_detected',
		 severity='warning',
		 user_id=user.id,
		 ip=ip,
		 user_agent=user_agent,
		 is_new_ip=bool(anomaly.get('is_new_ip')),
		 is_new_device=bool(anomaly.get('is_new_device')),
		 country_changed=bool(anomaly.get('country_changed')),
		 known_sessions=int(anomaly.get('known_sessions') or 0),
		 current_country=str(anomaly.get('current_country') or ''),
		 previous_country=str(anomaly.get('previous_country') or ''),
		)
	if not getattr(settings, 'SECURITY_EMAIL_ALERTS_ENABLED', True):
		return
	if is_anomalous:
		_alert_login_success(user, request=request, anomaly=anomaly)


def _decode_websafe_value(value):
	if isinstance(value, str):
		try:
			return websafe_decode(value.encode('utf-8'))
		except Exception:
			return value
	return value


def _encode_websafe_value(value):
	if isinstance(value, str):
		return value
	if isinstance(value, (bytes, bytearray, memoryview)):
		return websafe_encode(bytes(value)).decode()
	return value


def _webauthn_rp_id(request) -> str:
	configured = str(getattr(settings, 'WEBAUTHN_RP_ID', '') or '').strip()
	if configured:
		return configured
	origin = str(request.META.get('HTTP_ORIGIN', '') or '').strip()
	if origin:
		try:
			parsed = urllib.parse.urlparse(origin)
			if parsed.hostname:
				return parsed.hostname
		except Exception:
			pass
	host = str(request.get_host().split(':')[0] if request.get_host() else '').strip()
	if host in {'127.0.0.1', 'localhost', '::1'}:
		return 'localhost'
	return host or 'localhost'


def _decode_public_key_options(options: dict) -> dict:
	public_key = options.get('publicKey') if isinstance(options, dict) else None
	if not isinstance(public_key, dict):
		return options
	if 'challenge' in public_key:
		public_key['challenge'] = _decode_websafe_value(public_key['challenge'])
	if isinstance(public_key.get('user'), dict) and 'id' in public_key['user']:
		public_key['user']['id'] = _decode_websafe_value(public_key['user']['id'])
	for key in ('allowCredentials', 'excludeCredentials'):
		credentials = public_key.get(key) or []
		for credential in credentials:
			if isinstance(credential, dict) and 'id' in credential:
				credential['id'] = _decode_websafe_value(credential['id'])
	return options


def _scan_avatar_object(*, bucket: str, key: str) -> tuple[bool, str]:
	host = str(getattr(settings, 'CLAMAV_HOST', '') or '').strip()
	port = int(getattr(settings, 'CLAMAV_PORT', 3310) or 3310)
	if not host:
		if getattr(settings, 'AVATAR_SCAN_REQUIRED', False):
			return False, 'malware scanner not configured'
		return True, 'scanner disabled'

	if boto3 is None:
		return False, 'S3 support not installed'

	s3 = boto3.client(
	 's3',
	 aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
	 aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
	 region_name=getattr(settings, 'AWS_REGION', None),
	)
	obj = s3.get_object(Bucket=bucket, Key=key)
	body = obj.get('Body')
	if body is None:
		return False, 'avatar object unavailable'
	data = body.read()
	try:
		with socket.create_connection((host, port), timeout=10) as sock:
			sock.sendall(b'zINSTREAM\0')
			stream = BytesIO(data)
			while True:
				chunk = stream.read(8192)
				if not chunk:
					sock.sendall(struct.pack('!I', 0))
					break
				sock.sendall(struct.pack('!I', len(chunk)))
				sock.sendall(chunk)
			resp = sock.recv(1024).decode('utf-8', errors='ignore')
		if 'FOUND' in resp.upper():
			return False, resp.strip() or 'malware detected'
		return True, resp.strip() or 'clean'
	except Exception as exc:
		if getattr(settings, 'AVATAR_SCAN_REQUIRED', False):
			return False, f'scan unavailable: {exc}'
		return True, f'scan skipped: {exc}'


User = get_user_model()


class RegisterView(generics.CreateAPIView):
	queryset = User.objects.all()
	serializer_class = RegisterSerializer
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_register'

	def create(self, request, *args, **kwargs):
		ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
		username = str(request.data.get('username', '')).strip() or 'anon'
		cache_key = f"auth_register:{username}:{ip}"

                                                                  
		resp = super().create(request, *args, **kwargs)
                                                
		if getattr(resp, 'status_code', None) == 201:
			cache.delete(cache_key)
			return resp
                                    
		attempts = cache.get(cache_key, 0) + 1
		cache.set(cache_key, attempts, timeout=60)
		if attempts > 3:
			from rest_framework.response import Response as DRFResponse
			return DRFResponse({'detail': 'Request was throttled.'}, status=429)
		return resp


class LoginView(TokenObtainPairView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_login'

	def post(self, request, *args, **kwargs):
		ip = _client_ip(request)
		username = str(request.data.get('username', '')).strip() or 'anon'
		cache_key = f"auth_login:{username}:{ip}"
		try:
			user = User.objects.get(username=username)
		except User.DoesNotExist:
			user = None
		if user is not None:
			locked, _ = _is_login_locked(user, ip=ip)
			if locked:
				return Response({'detail': 'login temporarily locked due to repeated failures'}, status=423)
			if not _is_email_verified(user):
				return _email_not_verified_response()
		resp = super().post(request, *args, **kwargs)
                                      
		if getattr(resp, 'status_code', None) == 200:
			try:
				access = AccessToken(str(resp.data.get('access', '')))
				refresh = RefreshToken(str(resp.data.get('refresh', '')))
				if user is None:
					user = User.objects.get(username=username)
				_note_successful_login(user, request=request, refresh_token=refresh, access_token=access)
				_clear_login_failures(user, ip=ip)
			except Exception:
				pass
			cache.delete(cache_key)
			return resp
                           
		attempts = cache.get(cache_key, 0) + 1
		cache.set(cache_key, attempts, timeout=60)
		locked = False
		if user is not None:
			locked, failures = _mark_login_failure(user, ip=ip, username=username, request=request)
			if locked:
				from rest_framework.response import Response as DRFResponse
				return DRFResponse({
				 'detail': 'login temporarily locked due to repeated failures',
				 'failures': failures,
				}, status=423)
		if attempts > 5:
			from rest_framework.response import Response as DRFResponse
			return DRFResponse({'detail': 'Request was throttled.'}, status=429)
		return resp


class RefreshView(TokenRefreshView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_refresh'

	def post(self, request, *args, **kwargs):
		refresh_raw = str(request.data.get('refresh', '')).strip()
		if refresh_raw:
			try:
				refresh = RefreshToken(refresh_raw)
				if RevokedToken.objects.filter(jti=_token_jti(refresh)).exists():
					return Response({'detail': 'token revoked'}, status=401)
			except Exception:
				pass
		resp = super().post(request, *args, **kwargs)
		if getattr(resp, 'status_code', None) == 200 and refresh_raw:
			try:
				refresh = RefreshToken(refresh_raw)
				user = User.objects.get(id=refresh['user_id'])
				access = AccessToken(str(resp.data.get('access', '')))
				session = UserSession.objects.filter(user=user, jwt_jti=_token_jti(refresh)).first()
				if session:
					session.access_jti = _token_jti(access)
					session.save(update_fields=['access_jti', 'last_active'])
			except Exception:
				pass
		return resp


class MeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		return Response({
		 "id": request.user.id,
		 "username": request.user.username,
		 "email": request.user.email,
		})


class SessionListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		current_jti = _token_jti(request.auth) if request.auth is not None else ''
		current_session = None
		if current_jti:
			current_session = (
			 request.user.sessions
			 .filter(Q(jwt_jti=current_jti) | Q(access_jti=current_jti))
			 .order_by('-last_active', '-created_at')
			 .first()
			)
			if current_session:
				current_session.last_active = timezone.now()
				current_session.save(update_fields=['last_active'])

		timeout_seconds = int(getattr(settings, 'ACTIVE_SESSION_INACTIVITY_TIMEOUT_SECONDS', 43200) or 0)
		if timeout_seconds > 0:
			cutoff = timezone.now() - timedelta(seconds=timeout_seconds)
			stale_sessions = request.user.sessions.filter(last_active__lt=cutoff)
			if current_session:
				stale_sessions = stale_sessions.exclude(pk=current_session.pk)
			for session in list(stale_sessions):
				_revoke_session(session, reason='inactive session expired')

		sessions = request.user.sessions.order_by('-last_active', '-created_at')
		if timeout_seconds > 0:
			cutoff = timezone.now() - timedelta(seconds=timeout_seconds)
			sessions = sessions.filter(last_active__gte=cutoff)
		return Response([_session_payload(session, current_jti=current_jti) for session in sessions])


class SessionRevokeView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, session_id: int):
		session = get_object_or_404(UserSession, pk=session_id, user=request.user)
		_revoke_session(session, reason='revoked by user')
		return Response({'detail': 'session revoked'})


class SessionRevokeAllView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		count = _revoke_user_sessions(request.user, reason='revoked all by user')
		return Response({'detail': 'sessions revoked', 'count': count})



class VerifyEmailView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		token = str(request.data.get('token', '')).strip()
		if not token:
			return Response({'detail': 'token required'}, status=400)
		try:
			ev = EmailVerificationToken.objects.get(token=token, used=False)
		except EmailVerificationToken.DoesNotExist:
			return Response({'detail': 'invalid token'}, status=400)
		if ev.is_expired():
			return Response({'detail': 'token expired'}, status=400)
		ev.used = True
		ev.save()
                                                                            
		try:
			profile, _ = UserPrivacySettings.objects.get_or_create(user=ev.user)
			profile.email_verified = True
			profile.save(update_fields=['email_verified'])
		except Exception:
                                   
			pass
		return Response({'detail': 'email verified'})


class ResendVerificationView(APIView):
\
\
\
\
    
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = str(request.data.get('email', '')).strip()
		user = None
		if request.user and request.user.is_authenticated:
			user = request.user
		elif email:
			try:
				user = User.objects.get(email__iexact=email)
			except User.DoesNotExist:
				return Response({'detail': 'no account with that email'}, status=404)
		else:
			return Response({'detail': 'email required'}, status=400)

		if not user.email:
			return Response({'detail': 'user has no email address'}, status=400)

                
		import uuid
		token = EmailVerificationToken.objects.create(user=user, token=str(uuid.uuid4()))
		verification_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={token.token}"
		try:
			send_mail(
			 subject='Verify your email',
			 message=f'Please verify your email by visiting: {verification_url}',
			 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
			 recipient_list=[user.email],
			 fail_silently=True,
			)
		except Exception:
			pass
		return Response({'detail': 'verification sent'})


class RequestEmailChangeView(APIView):
\
\
\
\
    
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'email_change'

	def post(self, request):
		user = request.user
		new_email = str(request.data.get('new_email', '')).strip()
		password = str(request.data.get('password', '')).strip()
		if not new_email or not password:
			return Response({'detail': 'new_email and password required'}, status=400)
		if not user.check_password(password):
			return Response({'detail': 'invalid password'}, status=401)

                                            
		import uuid
		token = str(uuid.uuid4())
		req = EmailChangeRequest.objects.create(user=user, new_email=new_email, token=token)
		confirm_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/confirm-email-change?token={token}"
                             
		try:
			send_mail(
			 subject='Confirm your new email',
			 message=f'Click to confirm your new email address: {confirm_url}',
			 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
			 recipient_list=[new_email],
			 fail_silently=True,
			)
		except Exception:
			pass

                    
		try:
			if user.email:
				send_mail(
				 subject='Email change requested',
				 message=f'A request was made to change your account email to {new_email}. If this was not you, contact support.',
				 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
				 recipient_list=[user.email],
				 fail_silently=True,
				)
		except Exception:
			pass
		_alert_sensitive_change(
		 user,
		 subject='Email change requested',
		 details=f'An email change request was created for {new_email}.',
		 request=request,
		)

		return Response({'detail': 'email change requested'})


class TOTPSetupView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
                                                       
		user = request.user
		secret = pyotp.random_base32()
		issuer = getattr(settings, 'TOTP_ISSUER', 'licenta-muzica')
		otpauth = pyotp.totp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=issuer)
                                                     
		cache.set(f"totp_setup:{user.id}", secret, timeout=600)
		return Response({'secret': secret, 'otpauth_url': otpauth})


class TOTPConfirmView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		code = str(request.data.get('code', '')).strip()
		if not code:
			return Response({'detail': 'code required'}, status=400)
		user = request.user
		secret = cache.get(f"totp_setup:{user.id}")
		if not secret:
			return Response({'detail': 'no totp setup in progress'}, status=400)
		totp = pyotp.TOTP(secret)
		if not totp.verify(code, valid_window=1):
			return Response({'detail': 'invalid code'}, status=400)
                       
		totp_obj, _ = UserTOTP.objects.get_or_create(user=user)
		totp_obj.secret = secret
		totp_obj.enabled = True
                         
		codes = []
		hashed = []
		for _ in range(8):
			c = secrets.token_urlsafe(8)
			codes.append(c)
			hashed.append(hashlib.sha256(c.encode()).hexdigest())
		totp_obj.backup_codes = '\n'.join(hashed)
		totp_obj.save()
		cache.delete(f"totp_setup:{user.id}")
		_alert_sensitive_change(
		 user,
		 subject='Two-factor authentication enabled',
		 details='Two-factor authentication was enabled on your account.',
		 request=request,
		)
		return Response({'detail': 'totp enabled', 'backup_codes': codes})


class TOTPDisableView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		password = str(request.data.get('password', '')).strip()
		code = str(request.data.get('code', '')).strip()
		if not password:
			return Response({'detail': 'password required'}, status=400)
		user = request.user
		if not user.check_password(password):
			return Response({'detail': 'invalid password'}, status=401)
		try:
			totp_obj = user.totp
		except Exception:
			return Response({'detail': 'not enabled'}, status=400)
		if totp_obj.enabled:
                             
			if not code:
				return Response({'detail': 'code required'}, status=400)
			if not pyotp.TOTP(totp_obj.secret).verify(code):
                             
				code_hash = hashlib.sha256(code.encode()).hexdigest()
				if code_hash not in (totp_obj.backup_codes or '').split('\n'):
					return Response({'detail': 'invalid code'}, status=400)
           
		totp_obj.secret = None
		totp_obj.enabled = False
		totp_obj.backup_codes = ''
		totp_obj.save()
		_alert_sensitive_change(
		 user,
		 subject='Two-factor authentication disabled',
		 details='Two-factor authentication was disabled on your account.',
		 request=request,
		)
		return Response({'detail': 'totp disabled'})


class TOTPVerifyView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
                                                                                        
		username = request.data.get('username')
		code = str(request.data.get('code', '')).strip()
		if not code:
			return Response({'detail': 'code required'}, status=400)
		if username:
			try:
				from django.contrib.auth import get_user_model
				UserModel = get_user_model()
				u = UserModel.objects.get(username=username)
				totp_obj = u.totp
			except Exception:
				return Response({'detail': 'invalid user or totp not enabled'}, status=400)
		else:
			if not request.user or not request.user.is_authenticated:
				return Response({'detail': 'not authenticated'}, status=401)
			try:
				totp_obj = request.user.totp
			except Exception:
				return Response({'detail': 'totp not enabled'}, status=400)
		if pyotp.TOTP(totp_obj.secret).verify(code):
			return Response({'detail': 'ok'})
                      
		code_hash = hashlib.sha256(code.encode()).hexdigest()
		if code_hash in (totp_obj.backup_codes or '').split('\n'):
                            
			codes = (totp_obj.backup_codes or '').split('\n')
			try:
				codes.remove(code_hash)
			except ValueError:
				pass
			totp_obj.backup_codes = '\n'.join(codes)
			totp_obj.save()
			return Response({'detail': 'ok (backup code)'})
		return Response({'detail': 'invalid code'}, status=400)


class ChangePasswordView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		current = str(request.data.get('current_password', '')).strip()
		new = str(request.data.get('new_password', '')).strip()
		totp_code = str(request.data.get('totp_code', '')).strip()
		if not current or not new:
			return Response({'detail': 'current and new password required'}, status=400)
		user = request.user
		if not user.check_password(current):
			return Response({'detail': 'invalid current password'}, status=401)
                                          
		try:
			totp_obj = user.totp
			if totp_obj.enabled:
				if not totp_code:
					return Response({'detail': 'totp code required'}, status=400)
				if not pyotp.TOTP(totp_obj.secret).verify(totp_code):
					return Response({'detail': 'invalid totp code'}, status=400)
		except Exception:
			pass
		user.set_password(new)
		user.save()
		count = _revoke_user_sessions(user, reason='password changed')
		_alert_sensitive_change(
		 user,
		 subject='Password changed',
		 details='Your password was changed and existing sessions were revoked.',
		 request=request,
		)
		return Response({'detail': 'password changed', 'revoked_sessions': count})


class WebAuthnRegisterOptionsView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		user = request.user
		rp_id = _webauthn_rp_id(request)
		rp_name = getattr(settings, 'WEBAUTHN_RP_NAME', 'Licenta Muzica')
		rp = PublicKeyCredentialRpEntity(id=rp_id, name=rp_name)
		user_entity = PublicKeyCredentialUserEntity(
		 id=str(user.id).encode('utf-8'),
		 name=user.username,
		 display_name=user.username,
		)
		server = Fido2Server(rp)
                                                        
		existing = []
		for c in user.webauthn_credentials.all():
			existing.append({'id': c.credential_id, 'type': 'public-key'})
		registration_data, state = server.register_begin(user_entity, credentials=existing)
                        
		cache.set(f"webauthn_reg:{user.id}", state, timeout=600)
                                                                                            
		registration_data = _decode_public_key_options(registration_data)
		registration_data['publicKey']['challenge'] = _encode_websafe_value(registration_data['publicKey']['challenge'])
		registration_data['publicKey']['user']['id'] = _encode_websafe_value(registration_data['publicKey']['user']['id'])
                         
		for cred in registration_data['publicKey'].get('excludeCredentials', []):
			cred['id'] = _encode_websafe_value(cred['id'])
		return Response(registration_data)


class WebAuthnRegisterCompleteView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		user = request.user
		data = request.data
		client_attestation = data.get('attestation')
		if not client_attestation:
			return Response({'detail': 'attestation required'}, status=400)
		state = cache.get(f"webauthn_reg:{user.id}")
		if not state:
			return Response({'detail': 'no registration in progress'}, status=400)
		rp_id = _webauthn_rp_id(request)
		rp = PublicKeyCredentialRpEntity(id=rp_id, name=getattr(settings, 'WEBAUTHN_RP_NAME', 'Licenta Muzica'))
		server = Fido2Server(rp)
		try:
			att_obj = client_attestation
			if isinstance(att_obj, dict):
				att_obj = {
				 **att_obj,
				 'clientDataJSON': _decode_websafe_value(att_obj.get('clientDataJSON')),
				 'attestationObject': _decode_websafe_value(att_obj.get('attestationObject')),
				}
			result = server.register_complete(state, att_obj['clientDataJSON'], att_obj['attestationObject'])
		except Exception as e:
                                                                            
			if getattr(settings, 'DEBUG', False):
				return Response({'detail': 'registration failed', 'error': str(e)}, status=400)
			return Response({'detail': 'registration failed'}, status=400)
		cred_data = result.credential_data
                    
		WebAuthnCredential.objects.create(
		 user=user,
		 credential_id=cred_data.credential_id,
		 public_key=cred_data.public_key,
		 sign_count=result.sign_count,
		 transports=','.join(att_obj.get('transports', []) or []),
		)
		cache.delete(f"webauthn_reg:{user.id}")
		_alert_sensitive_change(
		 user,
		 subject='Passkey added',
		 details='A new passkey / WebAuthn credential was added to your account.',
		 request=request,
		)
		return Response({'detail': 'registered'})


class WebAuthnLoginOptionsView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		username = request.data.get('username')
		if not username:
			return Response({'detail': 'username required'}, status=400)
		from django.contrib.auth import get_user_model
		UserModel = get_user_model()
		try:
			user = UserModel.objects.get(username=username)
		except UserModel.DoesNotExist:
			return Response({'detail': 'unknown user'}, status=404)
		if not _is_email_verified(user):
			return _email_not_verified_response()
		rp_id = _webauthn_rp_id(request)
		rp = PublicKeyCredentialRpEntity(id=rp_id, name=getattr(settings, 'WEBAUTHN_RP_NAME', 'Licenta Muzica'))
		server = Fido2Server(rp)
		credentials = []
		for c in user.webauthn_credentials.all():
			credentials.append({'type': 'public-key', 'id': c.credential_id})
		auth_data, state = server.authenticate_begin(credentials)
		cache.set(f"webauthn_auth:{user.id}", state, timeout=600)
                                                                                            
		auth_data['publicKey']['challenge'] = _encode_websafe_value(auth_data['publicKey']['challenge'])
		for cred in auth_data['publicKey'].get('allowCredentials', []):
			cred['id'] = _encode_websafe_value(cred['id'])
		return Response(auth_data)


class WebAuthnLoginCompleteView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		username = request.data.get('username')
		assertion = request.data.get('assertion')
		if not username or not assertion:
			return Response({'detail': 'username and assertion required'}, status=400)
		from django.contrib.auth import get_user_model
		UserModel = get_user_model()
		try:
			user = UserModel.objects.get(username=username)
		except UserModel.DoesNotExist:
			return Response({'detail': 'unknown user'}, status=404)
		if not _is_email_verified(user):
			return _email_not_verified_response()
		state = cache.get(f"webauthn_auth:{user.id}")
		if not state:
			return Response({'detail': 'no auth in progress'}, status=400)
		rp_id = _webauthn_rp_id(request)
		rp = PublicKeyCredentialRpEntity(id=rp_id, name=getattr(settings, 'WEBAUTHN_RP_NAME', 'Licenta Muzica'))
		server = Fido2Server(rp)
		try:
			auth_data = assertion
			if isinstance(auth_data, dict):
				auth_data = {
				 **auth_data,
				 'credentialId': _decode_websafe_value(auth_data.get('credentialId')),
				 'clientDataJSON': _decode_websafe_value(auth_data.get('clientDataJSON')),
				 'authenticatorData': _decode_websafe_value(auth_data.get('authenticatorData')),
				 'signature': _decode_websafe_value(auth_data.get('signature')),
				}
			auth_result = server.authenticate_complete(state, [
                                                     
			 (c.credential_id, c.public_key, c.sign_count) for c in user.webauthn_credentials.all()
			], auth_data['credentialId'], auth_data['clientDataJSON'], auth_data['authenticatorData'], auth_data['signature'])
		except Exception:
			return Response({'detail': 'authentication failed'}, status=400)
                     
		cred = user.webauthn_credentials.filter(credential_id=auth_result.credential_id).first()
		if cred:
			cred.sign_count = auth_result.new_sign_count
			cred.save()
                    
		refresh = RefreshToken.for_user(user)
		access = str(refresh.access_token)
		refresh_token = str(refresh)
		_note_successful_login(user, request=request, refresh_token=refresh, access_token=refresh.access_token)
		cache.delete(f"webauthn_auth:{user.id}")
		return Response({'access': access, 'refresh': refresh_token})


class AvatarPresignView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		if boto3 is None:
			return Response({'detail': 'S3 support not installed'}, status=501)
		filename = str(request.data.get('filename', '')).strip()
		content_type = str(request.data.get('content_type', '')).strip()
		if not filename or not content_type:
			return Response({'detail': 'filename and content_type required'}, status=400)
                                                                                            
		bucket = getattr(settings, 'AWS_S3_BUCKET_NAME', '')
		region = getattr(settings, 'AWS_REGION', None)
		endpoint_url = str(getattr(settings, 'AWS_S3_ENDPOINT_URL', '') or '').strip()
		if not bucket:
			return Response({'detail': 'S3 bucket not configured'}, status=500)
		key = f"avatars/{request.user.id}/{uuid.uuid4()}_{filename}"
		s3 = boto3.client('s3',
		      aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
		      aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
		      region_name=region,
		      endpoint_url=endpoint_url or None)
		try:
			presigned = s3.generate_presigned_url(
			 'put_object',
			 Params={'Bucket': bucket, 'Key': key, 'ContentType': content_type, 'ACL': 'private'},
			 ExpiresIn=int(getattr(settings, 'S3_PRESIGN_EXPIRY', 3600)),
			)
		except Exception as e:
			return Response({'detail': 'failed to generate presigned url'}, status=500)
                                                                               
		if endpoint_url:
			public_url = f"{endpoint_url.rstrip('/')}/{bucket}/{key}"
		else:
			public_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}" if region else f"https://{bucket}.s3.amazonaws.com/{key}"
		return Response({'upload_url': presigned, 'key': key, 'public_url': public_url})


class AvatarFinalizeView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		if boto3 is None:
			return Response({'detail': 'S3 support not installed'}, status=501)
		bucket = str(getattr(settings, 'AWS_S3_BUCKET_NAME', '') or '').strip()
		endpoint_url = str(getattr(settings, 'AWS_S3_ENDPOINT_URL', '') or '').strip()
		key = str(request.data.get('key', '')).strip()
		public_url = str(request.data.get('public_url', '')).strip()
		if not bucket or not key:
			return Response({'detail': 'key required'}, status=400)
                                                                                                 
		profile, _ = UserPrivacySettings.objects.get_or_create(user=request.user)
		profile.pending_avatar_url = public_url or ''
		profile.pending_avatar_key = key
		profile.avatar_scan_status = AvatarScanStatus.PENDING
		profile.avatar_scan_requested_at = timezone.now()
		profile.avatar_scan_message = ''
		profile.save(update_fields=['pending_avatar_url', 'pending_avatar_key', 'avatar_scan_status', 'avatar_scan_requested_at', 'avatar_scan_message'])

                                                         
		try:
			from .tasks import scan_avatar_object

			scan_avatar_object.apply_async(args=[bucket, key, request.user.id], countdown=2)
		except Exception:
                                                        
			is_clean, scan_message = _scan_avatar_object(bucket=bucket, key=key)
			if not is_clean:
				profile.avatar_scan_status = AvatarScanStatus.REJECTED
				profile.avatar_scan_message = scan_message[:255]
				profile.avatar_scanned_at = timezone.now()
				profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
				emit_security_signal(
				 'avatar_rejected',
				 severity='warning',
				 user_id=request.user.id,
				 bucket=bucket,
				 key=key,
				 message=scan_message[:255],
				)
				return Response({'detail': scan_message}, status=400)
                                      
			profile.avatar_url = public_url or ''
			profile.avatar_scan_status = AvatarScanStatus.CLEAN
			profile.avatar_scanned_at = timezone.now()
			profile.save(update_fields=['avatar_url', 'avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
			return Response({'detail': 'avatar activated (sync)', 'avatar_url': profile.avatar_url})

		return Response({'detail': 'scan queued', 'avatar_url': public_url, 'status': 'pending'})


class AvatarScanStatusView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		profile, _ = UserPrivacySettings.objects.get_or_create(user=request.user)
		return Response(AvatarScanStatusSerializer(profile).data)


class ConfirmEmailChangeView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		token = str(request.data.get('token', '')).strip()
		if not token:
			return Response({'detail': 'token required'}, status=400)
		try:
			r = EmailChangeRequest.objects.get(token=token, used=False)
		except EmailChangeRequest.DoesNotExist:
			return Response({'detail': 'invalid token'}, status=400)
		if r.is_expired():
			return Response({'detail': 'token expired'}, status=400)

		user = r.user
		old_email = user.email
		user.email = r.new_email
		try:
			user.save()
                                                           
			try:
				profile = getattr(user, 'privacy', None)
				if profile is not None:
					profile.email_verified = True
					profile.save()
			except Exception:
				pass
		except Exception:
			return Response({'detail': 'failed to update email'}, status=500)
		_alert_sensitive_change(
		 user,
		 subject='Email changed',
		 details=f'Your account email was changed from {old_email} to {user.email}.',
		 request=None,
		)

		r.used = True
		r.save()

                              
		try:
			if old_email:
				send_mail(
				 subject='Email changed',
				 message=f'Your account email was changed from {old_email} to {user.email}',
				 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
				 recipient_list=[old_email],
				 fail_silently=True,
				)
		except Exception:
			pass

		return Response({'detail': 'email changed'})


class PasswordResetRequestView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		email = str(request.data.get('email', '')).strip()
		if not email:
			return Response({'detail': 'email required'}, status=400)
		users = User.objects.filter(email__iexact=email)
		for u in users:
			token = PasswordResetToken.objects.create(user=u, token=str(uuid.uuid4()))
			reset_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/reset-password?token={token.token}"
			send_mail(
			 subject='Password reset',
			 message=f'Use this link to reset your password: {reset_url}',
			 from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
			 recipient_list=[u.email],
			 fail_silently=True,
			)
		return Response({'detail': 'If an account exists for that email, password reset instructions have been sent.'})


class PasswordResetConfirmView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		token = str(request.data.get('token', '')).strip()
		new_password = str(request.data.get('password', '')).strip()
		if not token or not new_password:
			return Response({'detail': 'token and password required'}, status=400)
		try:
			pr = PasswordResetToken.objects.get(token=token, used=False)
		except PasswordResetToken.DoesNotExist:
			return Response({'detail': 'invalid token'}, status=400)
		if pr.is_expired():
			return Response({'detail': 'token expired'}, status=400)
		try:
			validate_password_policy(new_password)
		except serializers.ValidationError as exc:
			return Response(exc.detail, status=400)
		user = pr.user
		user.set_password(new_password)
		user.save()
		pr.used = True
		pr.save()
		return Response({'detail': 'password set'})


class SimilarUsersView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		try:
			limit = int(limit_raw) if limit_raw else 10
		except ValueError:
			limit = 10
		limit = max(1, min(limit, 50))

		candidate_limit = min(50, max(limit * 3, limit))
		candidates = similar_users_for(request.user, limit=candidate_limit)
		candidate_ids = [int(s.user.id) for s in candidates]
		unavailable_ids = set()
		if candidate_ids:
			unavailable_ids = set(
			 FriendRequest.objects.filter(
			  Q(sender=request.user, receiver_id__in=candidate_ids)
			  | Q(receiver=request.user, sender_id__in=candidate_ids),
			  status__in=[
			   FriendRequest.Status.ACCEPTED,
			   FriendRequest.Status.PENDING,
			  ],
			 ).values_list('sender_id', 'receiver_id')
			)
			unavailable_ids = {
			 int(other_id)
			 for sender_id, receiver_id in unavailable_ids
			 for other_id in (sender_id, receiver_id)
			 if int(other_id) != int(request.user.id)
			}
		similar = [
		 s for s in candidates
		 if int(s.user.id) not in unavailable_ids
		][:limit]
		payload = [
		 {
		  "user_id": s.user.id,
		  "username": s.user.username,
		  "similarity": round(float(s.similarity), 2),
		  **common_taste_details(request.user, s.user),
		 }
		 for s in similar
		]
		return Response(SimilarUserSerializer(payload, many=True).data)


class CompatibilityView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, user_id: int):
		other = get_object_or_404(User, pk=user_id)
		if other.id != request.user.id:
			try:
				if not bool(other.privacy.public_compatibility):
					return Response(status=status.HTTP_404_NOT_FOUND)
			except UserPrivacySettings.DoesNotExist:
				pass
		payload = compatibility_payload(request.user, other)
		return Response(CompatibilitySerializer(payload).data)


class UserSearchView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		q = str(request.query_params.get("q", "")).strip()
		limit_raw = str(request.query_params.get("limit", "")).strip()
		try:
			limit = int(limit_raw) if limit_raw else 10
		except ValueError:
			limit = 10
		limit = max(1, min(limit, 50))

		if not q:
			return Response([])

		qs = (
		 User.objects.filter(username__icontains=q)
		 .exclude(id=request.user.id)
		 .order_by("username")
		 .values("id", "username")
		)[:limit]
		return Response(UserSearchResultSerializer(list(qs), many=True).data)


class PublicUserProfileView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, username: str):
		normalized = str(username or '').strip()
		user_obj = get_object_or_404(User, username=normalized)

		reviews_limit = _parse_limit(request.query_params.get('reviews_limit', ''), default=5, max_value=20)
		ratings_limit = _parse_limit(request.query_params.get('ratings_limit', ''), default=5, max_value=20)
		activity_limit = _parse_limit(request.query_params.get('activity_limit', ''), default=10, max_value=50)

		stats = profile_stats_payload_for(user_obj)

		reviews = (
		 AlbumReview.objects.select_related('user', 'album', 'album__artist')
		 .filter(
		  user=user_obj,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .order_by('-created_at')[:reviews_limit]
		)

		ratings = (
		 AlbumRating.objects.select_related('user', 'album', 'album__artist')
		 .filter(
		  user=user_obj,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .order_by('-created_at')[:ratings_limit]
		)

		public_activity = True
		try:
			public_activity = bool(user_obj.privacy.public_activity)
		except UserPrivacySettings.DoesNotExist:
			public_activity = True

		activity = (
		 UserActivity.objects.select_related('actor')
		 .filter(actor=user_obj)
		 .order_by('-created_at')[:activity_limit]
		) if public_activity else UserActivity.objects.none()

		payload = {
		 "user_id": user_obj.id,
		 "username": user_obj.username,
		 "stats": ProfileStatsSerializer(stats).data,
		 "recent_reviews": MyAlbumReviewSerializer(reviews, many=True).data,
		 "recent_album_ratings": MyAlbumRatingSerializer(ratings, many=True).data,
		 "recent_activity": UserActivitySerializer(activity, many=True).data,
		}
		return Response(payload)
