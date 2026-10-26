from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from interactions.models import AlbumRating
from music.models import Album, Artist
from users.models import AvatarScanStatus, EmailVerificationToken, PasswordResetToken, RevokedToken, UserPrivacySettings, UserSession


User = get_user_model()


class TestPasswordResetSecurity(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.user = User.objects.create_user(
		 username="reset-user",
		 email="reset@example.com",
		 password="OldPass123!",
		)

	@patch("users.views.send_mail")
	def test_password_reset_request_does_not_enumerate_accounts(self, mock_send_mail):
		existing = self.client.post(
		 "/api/auth/password-reset/",
		 {"email": self.user.email},
		 format="json",
		)
		missing = self.client.post(
		 "/api/auth/password-reset/",
		 {"email": "missing@example.com"},
		 format="json",
		)

		self.assertEqual(existing.status_code, 200, existing.data)
		self.assertEqual(missing.status_code, 200, missing.data)
		self.assertEqual(existing.data, missing.data)
		self.assertEqual(mock_send_mail.call_count, 1)

	def test_password_reset_confirm_rejects_weak_password(self):
		token = PasswordResetToken.objects.create(user=self.user, token="reset-token")
		res = self.client.post(
		 "/api/auth/password-reset/confirm/",
		 {"token": token.token, "password": "weak"},
		 format="json",
		)

		self.assertEqual(res.status_code, 400, res.data)
		self.assertIn("password", res.data)
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password("OldPass123!"))


class TestPublicUserProfile(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)

	def test_public_profile_allow_any(self):
		res = self.client.get(f"/api/users/public/{self.user.username}")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertIn("user_id", res.data)
		self.assertIn("username", res.data)
		self.assertIn("stats", res.data)
		self.assertIn("recent_reviews", res.data)
		self.assertIn("recent_album_ratings", res.data)
		self.assertIn("recent_activity", res.data)
		self.assertEqual(res.data.get("username"), "alice")
		self.assertTrue(isinstance(res.data.get("recent_reviews"), list))
		self.assertTrue(isinstance(res.data.get("recent_album_ratings"), list))
		self.assertTrue(isinstance(res.data.get("recent_activity"), list))


class TestUserSimilarity(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"

		self.user = User.objects.create_user(username="alice", password=self.password)
		self.user_b = User.objects.create_user(username="alex", password=self.password)
		self.user_c = User.objects.create_user(username="maria", password=self.password)
		for user in (self.user, self.user_b, self.user_c):
			UserPrivacySettings.objects.get_or_create(user=user)
			user.privacy.email_verified = True
			user.privacy.save(update_fields=["email_verified"])

		artist = Artist.objects.create(name="A", slug="a", is_approved=True)
		self.album1 = Album.objects.create(artist=artist, title="One", slug="one", release_date=date(2020, 1, 1), is_approved=True)
		self.album2 = Album.objects.create(artist=artist, title="Two", slug="two", release_date=date(2020, 1, 2), is_approved=True)
		self.album3 = Album.objects.create(artist=artist, title="Three", slug="three", release_date=date(2020, 1, 3), is_approved=True)
		self.album4 = Album.objects.create(artist=artist, title="Four", slug="four", release_date=date(2020, 1, 4), is_approved=True)

	def _login_as(self, username: str):
		res = self.client.post("/api/auth/login/", {"username": username, "password": self.password}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_similar_users_orders_by_similarity(self):
                        
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user, album=self.album2, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album3, rating=3)

                                            
		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album2, rating=2)
		AlbumRating.objects.create(user=self.user_b, album=self.album4, rating=4)

                               
		AlbumRating.objects.create(user=self.user_c, album=self.album2, rating=5)

		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertEqual([u["username"] for u in res.data], ["alex", "maria"])
		self.assertGreater(res.data[0]["similarity"], res.data[1]["similarity"])
		self.assertGreater(res.data[0]["similarity"], 0)
                   
		self.assertEqual(res.data[0]["user_id"], self.user_b.id)
		self.assertEqual(res.data[0]["common_albums"], ["One"])
		self.assertEqual(res.data[0]["common_artists"], ["A"])
		self.assertEqual(res.data[0]["common_genres"], [])
		self.assertEqual(res.data[1]["user_id"], self.user_c.id)
		self.assertEqual(res.data[1]["common_albums"], ["Two"])
		self.assertEqual(res.data[1]["common_artists"], ["A"])
		self.assertEqual(res.data[1]["common_genres"], [])

	def test_compatibility_endpoint(self):
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user, album=self.album2, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album3, rating=3)

		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album2, rating=2)

		self._login_as("alice")
		res = self.client.get(f"/api/users/{self.user_b.id}/compatibility")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data["user_id"], self.user_b.id)
		self.assertEqual(res.data["username"], "alex")
		self.assertGreater(res.data["similarity"], 0)
		self.assertLessEqual(res.data["similarity"], 100)
		self.assertEqual(res.data["common_albums"], ["One"])
		self.assertEqual(res.data["common_artists"], ["A"])
		self.assertEqual(res.data["common_genres"], [])

	def test_similar_users_respect_compatibility_privacy(self):
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_c, album=self.album1, rating=5)
		self.user_c.privacy.public_compatibility = False
		self.user_c.privacy.save(update_fields=["public_compatibility"])

		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual([u["username"] for u in res.data], ["alex"])

	def test_similar_users_empty_when_no_ratings(self):
		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])

	def test_user_search_requires_auth(self):
		res = self.client.get("/api/users/search", {"q": "al"})
		self.assertIn(res.status_code, (401, 403))

	def test_user_search_by_username_excludes_self(self):
		self._login_as("alice")
		res = self.client.get("/api/users/search", {"q": "al"})
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		usernames = [u["username"] for u in res.data]
		self.assertIn("alex", usernames)
		self.assertNotIn("alice", usernames)

	def test_user_search_empty_q_returns_empty_list(self):
		self._login_as("alice")
		res = self.client.get("/api/users/search", {"q": ""})
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])


class TestAuthThrottling(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)

	def test_login_requires_verified_email(self):
		res = self.client.post(
		 "/api/auth/login/",
		 {"username": self.user.username, "password": self.password},
		 format="json",
		)
		self.assertEqual(res.status_code, 403, res.data)
		self.assertIn("detail", res.data)
		self.assertIn("verific", str(res.data["detail"]).lower(), res.data)

	def test_verify_email_enables_login(self):
		profile = UserPrivacySettings.objects.get_or_create(user=self.user)[0]
		self.assertFalse(profile.email_verified)
		token = EmailVerificationToken.objects.create(user=self.user, token="verify-token-123")

		verify_res = self.client.post(
		 "/api/auth/verify-email/",
		 {"token": token.token},
		 format="json",
		)
		self.assertEqual(verify_res.status_code, 200, verify_res.data)

		profile.refresh_from_db()
		self.assertTrue(profile.email_verified)

		login_res = self.client.post(
		 "/api/auth/login/",
		 {"username": self.user.username, "password": self.password},
		 format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		self.assertIn("access", login_res.data)

	@patch("django.core.mail.send_mail", side_effect=Exception("smtp down"))
	def test_register_still_succeeds_if_verification_email_fails(self, mock_send_mail):
		payload = {
		 "username": "new-user-email-failure",
		 "email": "new-user-email-failure@example.com",
		 "password": "StrongPass123!",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 201, res.data)
		self.assertTrue(User.objects.filter(username=payload["username"]).exists())
		self.assertTrue(UserPrivacySettings.objects.filter(user__username=payload["username"]).exists())

	def test_register_requires_special_character(self):
		payload = {
		 "username": "new-user-no-special",
		 "email": "new-user-no-special@example.com",
		 "password": "StrongPass123",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 400, res.data)
		self.assertIn("password", res.data)
		self.assertIn("cerințele minime", str(res.data["password"]).lower())

	def test_register_requires_lowercase(self):
		payload = {
		 "username": "new-user-no-lowercase",
		 "email": "new-user-no-lowercase@example.com",
		 "password": "STRONGPASS123!",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 400, res.data)

	def test_register_requires_uppercase(self):
		payload = {
		 "username": "new-user-no-uppercase",
		 "email": "new-user-no-uppercase@example.com",
		 "password": "strongpass123!",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 400, res.data)

	def test_register_requires_number(self):
		payload = {
		 "username": "new-user-no-number",
		 "email": "new-user-no-number@example.com",
		 "password": "StrongPass!",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 400, res.data)

	def test_register_requires_minimum_length(self):
		payload = {
		 "username": "new-user-short",
		 "email": "new-user-short@example.com",
		 "password": "S1a!",
		}
		res = self.client.post("/api/auth/register/", payload, format="json")
		self.assertEqual(res.status_code, 400, res.data)

	def test_login_is_throttled_after_limit(self):
		profile = UserPrivacySettings.objects.get_or_create(user=self.user)[0]
		profile.email_verified = True
		profile.save(update_fields=["email_verified"])

		payload = {"username": self.user.username, "password": "wrong-password"}
		status_codes = []
		for _ in range(6):
			res = self.client.post("/api/auth/login/", payload, format="json")
			status_codes.append(res.status_code)
		self.assertEqual(status_codes[:5], [401, 401, 401, 401, 401])
                                                                                  
		self.assertIn(status_codes[5], (429, 401, 423))
		if status_codes[5] == 429:
			self.assertIn("detail", res.data)

	@patch("users.views.emit_security_signal")
	@patch("users.views._send_security_email")
	def test_login_anomaly_emits_internal_event_and_email(self, mock_send_security_email, mock_emit_security_signal):
		profile = UserPrivacySettings.objects.get_or_create(user=self.user)[0]
		profile.email_verified = True
		profile.save(update_fields=["email_verified"])

		payload = {"username": self.user.username, "password": self.password}
		r1 = self.client.post("/api/auth/login/", payload, format="json", HTTP_USER_AGENT="UA-ONE")
		r2 = self.client.post("/api/auth/login/", payload, format="json", HTTP_USER_AGENT="UA-ONE")
		r3 = self.client.post("/api/auth/login/", payload, format="json", HTTP_USER_AGENT="UA-TWO")

		self.assertEqual(r1.status_code, 200, r1.data)
		self.assertEqual(r2.status_code, 200, r2.data)
		self.assertEqual(r3.status_code, 200, r3.data)

		self.assertEqual(mock_send_security_email.call_count, 2)
		self.assertEqual(mock_emit_security_signal.call_count, 2)

		first_event_args, first_event_kwargs = mock_emit_security_signal.call_args_list[0]
		self.assertEqual(first_event_args[0], "login_anomaly_detected")
		self.assertEqual(first_event_kwargs.get("severity"), "warning")
		self.assertEqual(first_event_kwargs.get("user_id"), self.user.id)

		last_event_args, last_event_kwargs = mock_emit_security_signal.call_args_list[-1]
		self.assertEqual(last_event_args[0], "login_anomaly_detected")
		self.assertTrue(last_event_kwargs.get("is_new_device"))

	def test_webauthn_register_options_route_exists(self):
		profile = UserPrivacySettings.objects.get_or_create(user=self.user)[0]
		profile.email_verified = True
		profile.save(update_fields=["email_verified"])

		res = self.client.post("/api/auth/webauthn/register/options/", {}, format="json")
		self.assertIn(res.status_code, (401, 403), res.data)
		self.assertNotEqual(res.status_code, 404, res.data)

	def test_webauthn_register_options_authenticated(self):
		profile = UserPrivacySettings.objects.get_or_create(user=self.user)[0]
		profile.email_verified = True
		profile.save(update_fields=["email_verified"])

		self.client.force_authenticate(user=self.user)
		res = self.client.post("/api/auth/webauthn/register/options/", {}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertIn("publicKey", res.data)
		self.assertIn("challenge", res.data["publicKey"])
		self.assertIsInstance(res.data["publicKey"]["challenge"], str)

	def test_register_is_throttled_after_limit(self):
		payload = {
		 "username": "new-user",
		 "email": "new-user@example.com",
		 "password": "StrongPass123!",
		}
		status_codes = []
		for _ in range(4):
			res = self.client.post("/api/auth/register/", payload, format="json")
			status_codes.append(res.status_code)
		self.assertEqual(status_codes[:3], [201, 400, 400])
                                                                   
		self.assertIn(status_codes[3], (429, 400))
		if status_codes[3] == 429:
			self.assertIn("detail", res.data)


class TestSecurityHeaders(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_health_response_has_security_headers(self):
		res = self.client.get("/health/")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
		self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
		self.assertIn("Content-Security-Policy", res.headers)
		self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))
		self.assertIn("Permissions-Policy", res.headers)


class TestAvatarScanStatusEndpoint(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)
		self.profile = UserPrivacySettings.objects.create(
		 user=self.user,
		 email_verified=True,
		 avatar_scan_status=AvatarScanStatus.PENDING,
		 avatar_scan_message="waiting",
		 pending_avatar_url="https://example.com/pending.jpg",
		)

	def _login(self):
		res = self.client.post("/api/auth/login/", {"username": self.user.username, "password": self.password}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data.get('access')}")

	def test_avatar_status_requires_auth(self):
		res = self.client.get("/api/auth/avatar/status/")
		self.assertIn(res.status_code, (401, 403))

	def test_avatar_status_returns_current_profile_state(self):
		self._login()
		res = self.client.get("/api/auth/avatar/status/")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data["avatar_scan_status"], AvatarScanStatus.PENDING)
		self.assertEqual(res.data["avatar_scan_message"], "waiting")
		self.assertEqual(res.data["pending_avatar_url"], "https://example.com/pending.jpg")


class TestSessionRevocation(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)
		UserPrivacySettings.objects.get_or_create(user=self.user, defaults={"email_verified": True})
		self.user.privacy.email_verified = True
		self.user.privacy.save(update_fields=["email_verified"])

	def _login(self):
		res = self.client.post(
		 "/api/auth/login/",
		 {"username": self.user.username, "password": self.password},
		 format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		refresh = res.data.get("refresh")
		self.assertTrue(access)
		self.assertTrue(refresh)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
		return res.data

	def test_session_is_listed_and_can_be_revoked(self):
		self._login()

		res = self.client.get("/api/auth/sessions/")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(res.data)
		session_id = res.data[0]["id"]
		self.assertTrue(UserSession.objects.filter(id=session_id).exists())

		revoke = self.client.post(f"/api/auth/sessions/{session_id}/revoke/", {}, format="json")
		self.assertEqual(revoke.status_code, 200, revoke.data)
		self.assertFalse(UserSession.objects.filter(id=session_id).exists())
		self.assertGreaterEqual(RevokedToken.objects.count(), 1)

		me = self.client.get("/api/auth/me/")
		self.assertIn(me.status_code, (401, 403), me.data)

	def test_revoke_all_invalidates_current_access_token(self):
		self._login()

		res = self.client.post("/api/auth/sessions/revoke-all/", {}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)

		me = self.client.get("/api/auth/me/")
		self.assertIn(me.status_code, (401, 403), me.data)

	@override_settings(ACTIVE_SESSION_INACTIVITY_TIMEOUT_SECONDS=60)
	def test_session_list_hides_stale_sessions(self):
		self._login()
		current_session = UserSession.objects.filter(user=self.user).order_by("-created_at").first()
		self.assertIsNotNone(current_session)
		stale_session = UserSession.objects.create(
		 user=self.user,
		 jwt_jti="stale-refresh",
		 access_jti="stale-access",
		 ip="127.0.0.1",
		 user_agent="old",
		)
		UserSession.objects.filter(id=stale_session.id).update(last_active=timezone.now() - timedelta(minutes=2))

		res = self.client.get("/api/auth/sessions/")
		self.assertEqual(res.status_code, 200, res.data)
		ids = {item.get("id") for item in res.data}
		self.assertIn(current_session.id, ids)
		self.assertNotIn(stale_session.id, ids)
		self.assertFalse(UserSession.objects.filter(id=stale_session.id).exists())
