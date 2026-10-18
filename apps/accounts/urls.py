from django.urls import path

from .views import LoginView, LogoutView, SignUpView

app_name = "accounts"

urlpatterns = [
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
]
