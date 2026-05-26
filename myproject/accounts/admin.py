from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import RegistrationOTP, User, UserFCMToken, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	model = User
	list_display = (
		"id",
		"email",
		"phone",
		"is_email_verified",
		"is_phone_verified",
		"fcm_token",
		"is_staff",
		"is_active",
		"created_at",
	)
	list_filter = ("is_staff", "is_active", "is_email_verified", "is_phone_verified", "fcm_token")
	search_fields = ("email", "phone")
	ordering = ("-created_at",)

	fieldsets = (
		(None, {"fields": ("email", "phone", "password")} ),
		(
			"Verification",
			{"fields": ("is_email_verified", "is_phone_verified", "fcm_token")},
		),
		(
			"Permissions",
			{"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
		),
		("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
	)
	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("email", "phone", "password1", "password2", "is_staff", "is_active"),
			},
		),
	)
	readonly_fields = ("created_at", "updated_at", "last_login")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "full_name", "gender", "city", "country", "created_at")
	search_fields = ("user__email", "user__phone", "full_name", "city", "state", "country")
	list_filter = ("gender", "country", "state")


@admin.register(RegistrationOTP)
class RegistrationOTPAdmin(admin.ModelAdmin):
	list_display = ("id", "otp_type", "target_value", "is_verified", "is_consumed", "expires_at", "created_at")
	search_fields = ("target_value", "code")
	list_filter = ("otp_type", "is_verified", "is_consumed")
	readonly_fields = ("created_at", "updated_at", "verified_at", "consumed_at")


@admin.register(UserFCMToken)
class UserFCMTokenAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "uid", "token", "is_active", "created_at", "updated_at")
	list_filter = ("is_active", "created_at", "updated_at")
	search_fields = ("user__email", "user__phone", "uid", "token")
	autocomplete_fields = ("user",)
	readonly_fields = ("created_at", "updated_at")
