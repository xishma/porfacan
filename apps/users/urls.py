from django.urls import path

from .views import (
    ResendVerificationEmailView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRegisterView,
)

app_name = "users"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path(
        "profile/resend-verification/",
        ResendVerificationEmailView.as_view(),
        name="resend-verification",
    ),
]
