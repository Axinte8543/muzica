from django.urls import re_path

from .views import CompatibilityView, PublicUserProfileView, SimilarUsersView, UserSearchView


urlpatterns = [
	re_path(r"^search/?$", UserSearchView.as_view()),
	re_path(r"^similar/?$", SimilarUsersView.as_view()),
	re_path(r"^(?P<user_id>\d+)/compatibility/?$", CompatibilityView.as_view()),
	re_path(r"^public/(?P<username>[^/]+)/?$", PublicUserProfileView.as_view()),
]
