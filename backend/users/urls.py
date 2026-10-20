from django.urls import re_path
from .views import LoginView, MeView, RefreshView, RegisterView, VerifyEmailView, ResendVerificationView, PasswordResetRequestView, PasswordResetConfirmView
from .views import RequestEmailChangeView, ConfirmEmailChangeView
from .views import AvatarPresignView, AvatarFinalizeView, AvatarScanStatusView
from .views import TOTPSetupView, TOTPConfirmView, TOTPDisableView, TOTPVerifyView, ChangePasswordView
from .views import WebAuthnRegisterOptionsView, WebAuthnRegisterCompleteView, WebAuthnLoginOptionsView, WebAuthnLoginCompleteView
from .views import SessionListView, SessionRevokeView, SessionRevokeAllView

urlpatterns = [
    re_path(r"^register/?$", RegisterView.as_view()),
    re_path(r"^login/?$", LoginView.as_view()),
    re_path(r"^refresh/?$", RefreshView.as_view()),
    re_path(r"^me/?$", MeView.as_view()),
    re_path(r"^verify-email/?$", VerifyEmailView.as_view()),
    re_path(r"^verify-email/resend/?$", ResendVerificationView.as_view()),
    re_path(r"^password-reset/?$", PasswordResetRequestView.as_view()),
    re_path(r"^password-reset/confirm/?$", PasswordResetConfirmView.as_view()),
    re_path(r"^email-change/request/?$", RequestEmailChangeView.as_view()),
    re_path(r"^email-change/confirm/?$", ConfirmEmailChangeView.as_view()),
    re_path(r"^avatar/presign/?$", AvatarPresignView.as_view()),
    re_path(r"^avatar/finalize/?$", AvatarFinalizeView.as_view()),
    re_path(r"^avatar/status/?$", AvatarScanStatusView.as_view()),
    re_path(r"^totp/setup/?$", TOTPSetupView.as_view()),
    re_path(r"^totp/confirm/?$", TOTPConfirmView.as_view()),
    re_path(r"^totp/disable/?$", TOTPDisableView.as_view()),
    re_path(r"^totp/verify/?$", TOTPVerifyView.as_view()),
    re_path(r"^password/change/?$", ChangePasswordView.as_view()),
    re_path(r"^webauthn/register/options/?$", WebAuthnRegisterOptionsView.as_view()),
    re_path(r"^webauthn/register/complete/?$", WebAuthnRegisterCompleteView.as_view()),
    re_path(r"^webauthn/login/options/?$", WebAuthnLoginOptionsView.as_view()),
    re_path(r"^webauthn/login/complete/?$", WebAuthnLoginCompleteView.as_view()),
    re_path(r"^sessions/?$", SessionListView.as_view()),
    re_path(r"^sessions/revoke-all/?$", SessionRevokeAllView.as_view()),
    re_path(r"^sessions/(?P<session_id>\d+)/revoke/?$", SessionRevokeView.as_view()),
]
