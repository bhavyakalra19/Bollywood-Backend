from django.contrib import admin

from .models import Plan, Purchase


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "code", "price", "duration_days", "is_active", "created_at")
	list_filter = ("is_active", "created_at")
	search_fields = ("name", "code")
	readonly_fields = ("created_at", "updated_at")
	ordering = ("-created_at",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "plan", "amount", "is_active", "started_at", "expires_at", "created_at")
	list_filter = ("is_active", "created_at", "started_at", "expires_at")
	search_fields = ("user__email", "user__phone", "plan__name", "plan__code")
	autocomplete_fields = ("user", "plan")
	readonly_fields = ("created_at", "updated_at")
	ordering = ("-created_at",)

	def get_queryset(self, request):
		return super().get_queryset(request).select_related("user", "plan")
