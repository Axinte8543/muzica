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
	RegisterSerializer,
	SimilarUserSerializer,
	UserSearchResultSerializer,
)

from interactions.similarity import common_taste_details, compatibility_payload, similar_users_for

from interactions.models import AlbumRating, AlbumReview, UserActivity
from .models import UserPrivacySettings
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


User = get_user_model()


class RegisterView(generics.CreateAPIView):
	queryset = User.objects.all()
	serializer_class = RegisterSerializer
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_register'


class LoginView(TokenObtainPairView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_login'


class RefreshView(TokenRefreshView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'auth_refresh'


class MeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		return Response({
			"id": request.user.id,
			"username": request.user.username,
			"email": request.user.email,
		})


class SimilarUsersView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		try:
			limit = int(limit_raw) if limit_raw else 10
		except ValueError:
			limit = 10
		limit = max(1, min(limit, 50))

		similar = similar_users_for(request.user, limit=limit)
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
