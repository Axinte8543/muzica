from django.urls import re_path
from .views import LoginView, MeView, RefreshView, RegisterView

urlpatterns = [
    re_path(r"^register/?$", RegisterView.as_view()),
    re_path(r"^login/?$", LoginView.as_view()),
    re_path(r"^refresh/?$", RefreshView.as_view()),
    re_path(r"^me/?$", MeView.as_view()),
]
