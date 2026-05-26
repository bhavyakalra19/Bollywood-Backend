from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import ForgotPasswordOTPRequestSerializer, ForgotPasswordOTPVerifySerializer
from .models import UserProfile
from .services import OTPDeliveryError
from .serializers import (
    AuthUserProfileSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    SignupOTPRequestSerializer,
    SignupOTPVerifySerializer,
    UserFCMTokenUpsertSerializer,
    UserSerializer,
)

User = get_user_model()



class ForgotPasswordOTPRequestAPIView(generics.GenericAPIView):
    serializer_class = ForgotPasswordOTPRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class ForgotPasswordOTPVerifyAPIView(generics.GenericAPIView):
    serializer_class = ForgotPasswordOTPVerifySerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        headers = self.get_success_headers(serializer.data)

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        payload = {
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return Response(payload, status=status.HTTP_201_CREATED, headers=headers)


class LoginAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AuthUserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UserProfileUpdateAPIView(generics.UpdateAPIView):
    serializer_class = AuthUserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class SignupOTPRequestAPIView(generics.GenericAPIView):
    serializer_class = SignupOTPRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = serializer.save()
        except OTPDeliveryError as e:
            import traceback
            print(traceback.format_exc())
            print(f"OTP delivery error: {e}")
            return Response(
                {"detail": "OTP service is temporarily unavailable. Please try again shortly."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(payload, status=status.HTTP_200_OK)


class SignupOTPVerifyAPIView(generics.GenericAPIView):
    serializer_class = SignupOTPVerifySerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_200_OK)


class UserFCMTokenUpsertAPIView(generics.CreateAPIView):
    serializer_class = UserFCMTokenUpsertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            {
                "id": instance.id,
                "uid": instance.uid,
                "token": instance.token,
                "is_active": instance.is_active,
                "created_at": instance.created_at,
                "updated_at": instance.updated_at,
            },
            status=status.HTTP_200_OK,
        )
