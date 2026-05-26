from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Location, Post, PostApplication, SavedPost


class PostsAPITests(APITestCase):
	def setUp(self):
		self.creator = User.objects.create_user(email="creator@example.com", password="StrongPass123")
		self.user = User.objects.create_user(email="user@example.com", password="StrongPass123")
		self.post = Post.objects.create(
			created_by=self.creator,
			title="Casting Call",
			description="Sample description",
			is_active=True,
		)

class PostLocationAPITests(APITestCase):
	def setUp(self):
		self.creator = User.objects.create_user(email="location-creator@example.com", password="StrongPass123")
		self.user = User.objects.create_user(email="poster@example.com", password="StrongPass123")
		self.location = Location.objects.create(name="Mumbai", state="Maharashtra", country="India")
		self.post = Post.objects.create(
			created_by=self.creator,
			title="Casting Call",
			description="Need actor",
			location_option=self.location,
			is_active=True,
		)

	def test_location_list_api(self):
		url = reverse("posts:location-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["name"], "Mumbai")

	def test_post_list_includes_location_option(self):
		url = reverse("posts:post-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data[0]["location_option"]["name"], "Mumbai")

	def test_list_posts(self):
		url = reverse("posts:post-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)

	def test_save_and_unsave_post(self):
		self.client.force_authenticate(user=self.user)

		save_url = reverse("posts:post-save", kwargs={"post_id": self.post.id})
		save_response = self.client.post(save_url)
		self.assertEqual(save_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(SavedPost.objects.filter(user=self.user, post=self.post).count(), 1)

		unsave_url = reverse("posts:post-unsave", kwargs={"post_id": self.post.id})
		unsave_response = self.client.post(unsave_url)
		self.assertEqual(unsave_response.status_code, status.HTTP_200_OK)
		self.assertEqual(SavedPost.objects.filter(user=self.user, post=self.post).count(), 0)

	def test_apply_and_unapply_post(self):
		self.client.force_authenticate(user=self.user)

		apply_url = reverse("posts:post-apply", kwargs={"post_id": self.post.id})
		apply_response = self.client.post(apply_url)
		self.assertEqual(apply_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(PostApplication.objects.filter(user=self.user, post=self.post).count(), 1)

		unapply_url = reverse("posts:post-unapply", kwargs={"post_id": self.post.id})
		unapply_response = self.client.post(unapply_url)
		self.assertEqual(unapply_response.status_code, status.HTTP_200_OK)
		self.assertEqual(PostApplication.objects.filter(user=self.user, post=self.post).count(), 0)

	def test_saved_post_list_for_authenticated_user(self):
		other_post = Post.objects.create(
			created_by=self.creator,
			title="Another Casting Call",
			description="Another description",
			is_active=True,
		)
		other_user = User.objects.create_user(email="other-user@example.com", password="StrongPass123")

		SavedPost.objects.create(user=self.user, post=self.post)
		SavedPost.objects.create(user=other_user, post=other_post)

		self.client.force_authenticate(user=self.user)
		url = reverse("posts:saved-post-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], self.post.id)

	def test_applied_post_list_for_authenticated_user(self):
		other_post = Post.objects.create(
			created_by=self.creator,
			title="Different Role",
			description="Different description",
			is_active=True,
		)
		other_user = User.objects.create_user(email="another-user@example.com", password="StrongPass123")

		PostApplication.objects.create(user=self.user, post=self.post)
		PostApplication.objects.create(user=other_user, post=other_post)

		self.client.force_authenticate(user=self.user)
		url = reverse("posts:applied-post-list")
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], self.post.id)

	def test_saved_and_applied_lists_require_authentication(self):
		saved_url = reverse("posts:saved-post-list")
		applied_url = reverse("posts:applied-post-list")

		saved_response = self.client.get(saved_url)
		applied_response = self.client.get(applied_url)

		self.assertEqual(saved_response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(applied_response.status_code, status.HTTP_401_UNAUTHORIZED)
