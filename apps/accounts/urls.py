from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
    SignUpView,
)

app_name = "accounts"

urlpatterns = [
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "accounts/password/reset/sent/",
        PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "accounts/password/reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
