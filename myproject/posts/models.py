from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class Location(models.Model):
	name = models.CharField(max_length=120)
	state = models.CharField(max_length=120, blank=True)
	country = models.CharField(max_length=120)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["name"]
		constraints = [
			models.UniqueConstraint(fields=["name", "state", "country"], name="post_loc_unique_nsc")
		]
		indexes = [
			models.Index(fields=["is_active", "name"], name="posts_location_active_name_idx"),
		]

	def __str__(self):
		parts = [self.name]
		if self.state:
			parts.append(self.state)
		parts.append(self.country)
		return ", ".join(parts)


class Productions(models.Model):
	name = models.CharField(max_length=120, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["name"]
		indexes = [
			models.Index(fields=["name"], name="posts_prod_name_idx"),
		]

	def __str__(self):
		return self.name


class Genders(models.Model):
	name = models.CharField(max_length=80, unique=True)

	class Meta:
		ordering = ["name"]
		indexes = [
			models.Index(fields=["name"], name="posts_gender_name_idx"),
		]

	def __str__(self):
		return self.name


class Post(models.Model):
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="posts",
	)
	title = models.CharField(max_length=255)
	location_option = models.ForeignKey(
		Location,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="posts",
	)
	# production_type field removed
	genders = models.ManyToManyField(Genders, blank=True, related_name="posts")
	min_age = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(0), MaxValueValidator(150)],
	)
	max_age = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(0), MaxValueValidator(150)],
	)
	description = models.TextField()
	requirements = models.TextField(null=True, blank=True, help_text="Additional requirements for the post")
	phone_number = models.CharField(max_length=50, null=True, blank=True, default=None)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.CheckConstraint(
				check=Q(min_age__isnull=True) | Q(max_age__isnull=True) | Q(min_age__lte=F("max_age")),
				name="posts_post_min_age_lte_max_age",
			)
		]

	def clean(self):
		super().clean()
		if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
			raise ValidationError({"min_age": "min_age cannot be greater than max_age."})

	def __str__(self):
		return f"{self.title} (#{self.pk})"


class SavedPost(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
	)
	post = models.ForeignKey(
		Post,
		on_delete=models.CASCADE,
		related_name="saved_by",
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.UniqueConstraint(fields=["user", "post"], name="posts_savedpost_unique_user_post")
		]
		indexes = [
			models.Index(fields=["user", "-created_at"], name="svpost_user_cr_idx"),
			models.Index(fields=["post", "-created_at"], name="svpost_post_cr_idx"),
		]

	def __str__(self):
		return f"SavedPost(user={self.user_id}, post={self.post_id})"


class PostApplication(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="post_applications",
	)
	post = models.ForeignKey(
		Post,
		on_delete=models.CASCADE,
		related_name="applications",
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.UniqueConstraint(fields=["user", "post"], name="posts_application_unique_user_post")
		]
		indexes = [
			models.Index(fields=["user", "-created_at"], name="papp_user_cr_idx"),
			models.Index(fields=["post", "-created_at"], name="papp_post_cr_idx"),
		]

	def __str__(self):
		return f"PostApplication(user={self.user_id}, post={self.post_id})"
