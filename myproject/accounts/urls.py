
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginAPIView,
    RegisterAPIView,
    SignupOTPRequestAPIView,
    SignupOTPVerifyAPIView,
    UserFCMTokenUpsertAPIView,
    UserProfileDetailAPIView,
    UserProfileUpdateAPIView,
    ForgotPasswordOTPRequestAPIView,
    ForgotPasswordOTPVerifyAPIView
)

app_name = "accounts"
   

urlpatterns = [
    path("auth/signup/otp/request/", SignupOTPRequestAPIView.as_view(), name="signup-otp-request"),
    path("auth/signup/otp/verify/", SignupOTPVerifyAPIView.as_view(), name="signup-otp-verify"),
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/fcm-token/", UserFCMTokenUpsertAPIView.as_view(), name="fcm-token-upsert"),
    path("profile/", UserProfileDetailAPIView.as_view(), name="profile-detail"),
    path("profile/update/", UserProfileUpdateAPIView.as_view(), name="profile-update"),
    path("auth/forgot-password/otp/request/", ForgotPasswordOTPRequestAPIView.as_view(), name="forgot-password-otp-request"),
    path("auth/forgot-password/otp/verify/", ForgotPasswordOTPVerifyAPIView.as_view(), name="forgot-password-otp-verify"),
]
