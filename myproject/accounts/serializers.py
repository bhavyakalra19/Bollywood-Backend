import base64
import binascii
import uuid
from io import BytesIO

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import RegistrationOTP, UserFCMToken, UserProfile
from .services import (
    OTPDeliveryError,
    consume_verified_registration_otp,
    request_registration_otp,
    sync_user_fcm_token_flag,
    verify_registration_otp,
)

User = get_user_model()

class ForgotPasswordOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(regex=r"^\+?[1-9]\d{7,14}$", required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        if bool(email) == bool(phone):
            raise serializers.ValidationError("Provide exactly one of email or phone.")
        if email and not User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "No user with this email exists."})
        if phone and not User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "No user with this phone exists."})
        return attrs

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone")
        try:
            if email:
                otp = request_registration_otp(channel=RegistrationOTP.OTPType.EMAIL, target_value=email)
                channel = RegistrationOTP.OTPType.EMAIL
            else:
                otp = request_registration_otp(channel=RegistrationOTP.OTPType.PHONE, target_value=phone)
                channel = RegistrationOTP.OTPType.PHONE
        except OTPDeliveryError as exc:
            raise serializers.ValidationError({"detail": str(exc)})
        payload = {
            "detail": "OTP sent successfully.",
            "channel": channel,
            "expires_at": otp.expires_at,
        }
        if settings.DEBUG:
            payload["otp"] = otp.code
        return payload


class ForgotPasswordOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(regex=r"^\+?[1-9]\d{7,14}$", required=False)
    otp = serializers.RegexField(regex=r"^\d{6}$", max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        if bool(email) == bool(phone):
            raise serializers.ValidationError("Provide exactly one of email or phone.")
        return attrs

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone")
        otp_code = validated_data["otp"]
        new_password = validated_data["new_password"]
        if email:
            channel = RegistrationOTP.OTPType.EMAIL
            target_value = email
            user = User.objects.filter(email__iexact=email).first()
        else:
            channel = RegistrationOTP.OTPType.PHONE
            target_value = phone
            user = User.objects.filter(phone=phone).first()
        is_valid = verify_registration_otp(channel=channel, target_value=target_value, otp_code=otp_code)
        if not is_valid:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})
        if not user:
            raise serializers.ValidationError({"detail": "User not found."})
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        return {"detail": "Password reset successfully."}

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if data is None:
            return None

        if isinstance(data, str):
            if not data.strip():
                return None

            file_ext = None
            if data.startswith("data:image") and ";base64," in data:
                header, data = data.split(";base64,", 1)
                try:
                    file_ext = header.split("/")[1]
                except (IndexError, AttributeError):
                    file_ext = None

            # Normalize whitespace/newlines that can appear in JSON transported base64.
            data = "".join(data.split())

            try:
                decoded_file = base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise serializers.ValidationError("Invalid base64 image data.") from exc

            try:
                image = Image.open(BytesIO(decoded_file))
                image.verify()
                guessed_ext = (image.format or "").lower()
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                raise serializers.ValidationError("Invalid base64 image data.") from exc

            if guessed_ext == "jpeg":
                guessed_ext = "jpg"
            file_ext = guessed_ext or file_ext or "jpg"

            data = ContentFile(decoded_file, name=f"{uuid.uuid4().hex}.{file_ext}")

        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "is_email_verified",
            "is_phone_verified",
            "fcm_token",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
            "is_premium",
        ]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "avatar",
            "date_of_birth",
            "gender",
            "height",
            "city",
            "state",
            "country",
            "address",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    otp = serializers.RegexField(regex=r"^\d{6}$", max_length=6, write_only=True)
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["email", "phone", "password", "otp", "profile"]

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if not email and not phone:
            raise serializers.ValidationError("At least one of email or phone is required.")

        otp_code = attrs.get("otp")
        verified = False
        verified_channel = None
        if email:
            verified = consume_verified_registration_otp(
                channel=RegistrationOTP.OTPType.EMAIL,
                target_value=email,
                otp_code=otp_code,
            )
            if verified:
                verified_channel = RegistrationOTP.OTPType.EMAIL

        if not verified and phone:
            verified = consume_verified_registration_otp(
                channel=RegistrationOTP.OTPType.PHONE,
                target_value=phone,
                otp_code=otp_code,
            )
            if verified:
                verified_channel = RegistrationOTP.OTPType.PHONE

        if not verified:
            raise serializers.ValidationError({"otp": "Invalid, expired, or unverified OTP."})

        attrs["_verified_channel"] = verified_channel
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        verified_channel = validated_data.pop("_verified_channel", None)
        profile_data = validated_data.pop("profile", {})
        password = validated_data.pop("password")
        validated_data.pop("otp", None)

        user = User.objects.create_user(password=password, **validated_data)
        if verified_channel == RegistrationOTP.OTPType.EMAIL:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
        elif verified_channel == RegistrationOTP.OTPType.PHONE:
            user.is_phone_verified = True
            user.save(update_fields=["is_phone_verified", "updated_at"])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()
        return user


class SignupOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(regex=r"^\+?[1-9]\d{7,14}$", required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if bool(email) == bool(phone):
            raise serializers.ValidationError("Provide exactly one of email or phone.")

        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "An account with this email already exists."})
        if phone and User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": "An account with this phone already exists."})

        return attrs

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone")

        try:
            if email:
                otp = request_registration_otp(channel=RegistrationOTP.OTPType.EMAIL, target_value=email)
                channel = RegistrationOTP.OTPType.EMAIL
            else:
                otp = request_registration_otp(channel=RegistrationOTP.OTPType.PHONE, target_value=phone)
                channel = RegistrationOTP.OTPType.PHONE
        except OTPDeliveryError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

        payload = {
            "detail": "OTP sent successfully.",
            "channel": channel,
            "expires_at": otp.expires_at,
        }
        if settings.DEBUG:
            payload["otp"] = otp.code
        return payload


class SignupOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.RegexField(regex=r"^\+?[1-9]\d{7,14}$", required=False)
    otp = serializers.RegexField(regex=r"^\d{6}$", max_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if bool(email) == bool(phone):
            raise serializers.ValidationError("Provide exactly one of email or phone.")

        return attrs

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone")
        otp_code = validated_data["otp"]

        if email:
            channel = RegistrationOTP.OTPType.EMAIL
            target_value = email
        else:
            channel = RegistrationOTP.OTPType.PHONE
            target_value = phone

        is_valid = verify_registration_otp(channel=channel, target_value=target_value, otp_code=otp_code)
        if not is_valid:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

        return {
            "detail": "OTP verified successfully.",
            "channel": channel,
        }


class AuthUserProfileSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "full_name",
            "avatar",
            "date_of_birth",
            "gender",
            "height",
            "city",
            "state",
            "country",
            "address",
        ]


class CustomTokenObtainPairSerializer(serializers.Serializer):
    identifier = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(phone=identifier)
            except User.DoesNotExist as exc:
                raise serializers.ValidationError("Invalid credentials.") from exc

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        refresh = RefreshToken.for_user(user)
        refresh["email"] = user.email or ""
        refresh["phone"] = user.phone or ""
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
        }


class UserFCMTokenUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFCMToken
        fields = ["token"]

    def create(self, validated_data):
        user = self.context["request"].user
        uid = str(user.id)
        obj, _ = UserFCMToken.objects.update_or_create(
            user=user,
            uid=uid,
            defaults={
                "token": validated_data["token"],
                "is_active": True,
            },
        )
        sync_user_fcm_token_flag(user)
        return obj
