from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AuthProfileAPITests(APITestCase):
	def _login_and_authenticate(self, identifier, password):
		login_url = reverse("accounts:login")
		login_payload = {"identifier": identifier, "password": password}
		login_response = self.client.post(login_url, login_payload, format="json")
		token = login_response.data["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

	def test_register_requires_email_or_phone(self):
		url = reverse("accounts:register")
		payload = {"password": "StrongPass123"}

		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_register_with_email_creates_user_and_returns_tokens(self):
		otp_request_url = reverse("accounts:signup-otp-request")
		otp_request_response = self.client.post(
			otp_request_url,
			{"email": "user@example.com"},
			format="json",
		)
		self.assertEqual(otp_request_response.status_code, status.HTTP_200_OK)

		otp_verify_url = reverse("accounts:signup-otp-verify")
		otp_verify_response = self.client.post(
			otp_verify_url,
			{"email": "user@example.com", "otp": otp_request_response.data["otp"]},
			format="json",
		)
		self.assertEqual(otp_verify_response.status_code, status.HTTP_200_OK)

		url = reverse("accounts:register")
		payload = {
			"email": "user@example.com",
			"password": "StrongPass123",
			"otp": otp_request_response.data["otp"],
			"profile": {"full_name": "John Doe", "city": "Mumbai"},
		}

		response = self.client.post(url, payload, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)
		self.assertEqual(User.objects.count(), 1)
		self.assertEqual(User.objects.first().profile.full_name, "John Doe")
		self.assertTrue(User.objects.first().is_email_verified)

	def test_register_rejects_unverified_otp(self):
		otp_request_url = reverse("accounts:signup-otp-request")
		otp_request_response = self.client.post(
			otp_request_url,
			{"email": "pending@example.com"},
			format="json",
		)
		self.assertEqual(otp_request_response.status_code, status.HTTP_200_OK)

		register_url = reverse("accounts:register")
		register_response = self.client.post(
			register_url,
			{
				"email": "pending@example.com",
				"password": "StrongPass123",
				"otp": otp_request_response.data["otp"],
			},
			format="json",
		)

		self.assertEqual(register_response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_get_and_update_profile(self):
		user = User.objects.create_user(email="test@example.com", password="StrongPass123")
		self._login_and_authenticate(identifier="test@example.com", password="StrongPass123")

		get_url = reverse("accounts:profile-detail")
		get_response = self.client.get(get_url)
		self.assertEqual(get_response.status_code, status.HTTP_200_OK)

		update_url = reverse("accounts:profile-update")
		update_payload = {"full_name": "Jane Updated", "city": "Delhi"}
		update_response = self.client.patch(update_url, update_payload, format="json")

		self.assertEqual(update_response.status_code, status.HTTP_200_OK)
		user.refresh_from_db()
		self.assertEqual(user.profile.full_name, "Jane Updated")
		self.assertEqual(user.profile.city, "Delhi")
