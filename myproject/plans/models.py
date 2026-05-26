from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Plan(models.Model):
	name = models.CharField(max_length=120)
	code = models.SlugField(max_length=120, unique=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
	duration_days = models.PositiveIntegerField(validators=[MinValueValidator(1)])
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["code"], name="plans_plan_code_idx"),
			models.Index(fields=["is_active", "-created_at"], name="plans_plan_active_idx"),
		]

	def __str__(self):
		return f"{self.name} ({self.code})"


class Purchase(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="purchases",
	)
	plan = models.ForeignKey(
		Plan,
		on_delete=models.PROTECT,
		related_name="purchases",
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	started_at = models.DateTimeField(default=timezone.now)
	expires_at = models.DateTimeField(null=True, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.UniqueConstraint(
				fields=["user"],
				condition=Q(is_active=True),
				name="plans_one_active_purchase_per_user",
			)
		]
		indexes = [
			models.Index(fields=["user", "is_active"], name="plans_purchase_user_active_idx"),
			models.Index(fields=["expires_at"], name="plans_purchase_expires_idx"),
			models.Index(fields=["plan", "-created_at"], name="plans_purch_plan_cr_idx"),
		]

	def clean(self):
		super().clean()
		if self.expires_at and self.started_at and self.expires_at <= self.started_at:
			raise ValidationError({"expires_at": "expires_at must be greater than started_at."})

	def save(self, *args, **kwargs):
		if self.amount is None:
			self.amount = self.plan.price
		if self.expires_at is None and self.started_at and self.plan_id:
			self.expires_at = self.started_at + timedelta(days=self.plan.duration_days)
		super().save(*args, **kwargs)

	def __str__(self):
		return f"Purchase(user={self.user_id}, plan={self.plan_id}, active={self.is_active})"
