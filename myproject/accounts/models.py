from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
	email = models.EmailField(unique=True, null=True, blank=True)
	phone = models.CharField(
		max_length=20,
		unique=True,
		null=True,
		blank=True,
		validators=[RegexValidator(regex=r"^\+?[1-9]\d{7,14}$", message="Invalid phone number format.")],
	)
	is_email_verified = models.BooleanField(default=False)
	is_phone_verified = models.BooleanField(default=False)
	fcm_token = models.BooleanField(default=False)
	is_premium = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	is_staff = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	objects = UserManager()

	USERNAME_FIELD = "email"
	REQUIRED_FIELDS = []

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.email or self.phone or f"User {self.pk}"


class UserProfile(models.Model):
	class GenderChoices(models.TextChoices):
		MALE = "male", "Male"
		FEMALE = "female", "Female"
		OTHER = "other", "Other"
		PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
	full_name = models.CharField(max_length=255, blank=True)
	avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
	date_of_birth = models.DateField(null=True, blank=True)
	gender = models.CharField(max_length=20, choices=GenderChoices.choices, blank=True)
	height = models.CharField(max_length=20, blank=True)
	city = models.CharField(max_length=120, blank=True)
	state = models.CharField(max_length=120, blank=True)
	country = models.CharField(max_length=120, blank=True)
	address = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.full_name or f"Profile {self.user_id}"


class RegistrationOTP(models.Model):
	class OTPType(models.TextChoices):
		EMAIL = "email", "Email"
		PHONE = "phone", "Phone"

	otp_type = models.CharField(max_length=10, choices=OTPType.choices)
	target_value = models.CharField(max_length=255)
	code = models.CharField(max_length=6)
	expires_at = models.DateTimeField()
	is_verified = models.BooleanField(default=False)
	verified_at = models.DateTimeField(null=True, blank=True)
	is_consumed = models.BooleanField(default=False)
	consumed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["otp_type", "target_value", "is_verified", "is_consumed"]),
			models.Index(fields=["expires_at"]),
		]

	def __str__(self):
		return f"RegistrationOTP({self.otp_type}) for {self.target_value}"


class UserFCMToken(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fcm_tokens")
	uid = models.CharField(max_length=255)
	token = models.CharField(max_length=512)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]
		constraints = [
			models.UniqueConstraint(fields=["user", "uid"], name="accounts_fcm_unique_user_uid"),
		]
		indexes = [
			models.Index(fields=["user", "is_active"], name="accounts_fcm_user_active_idx"),
			models.Index(fields=["token"], name="accounts_fcm_token_idx"),
		]

	def __str__(self):
		return f"UserFCMToken(user={self.user_id}, uid={self.uid})"