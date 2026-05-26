from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Plan, Purchase


class PlanPurchaseAPITests(APITestCase):
	def setUp(self):
		self.user = User.objects.create_user(email="buyer@example.com", password="StrongPass123")
		self.plan = Plan.objects.create(name="Pro", code="pro", price="299.00", duration_days=30)
		self.client.force_authenticate(user=self.user)

	def test_purchase_plan_success(self):
		url = reverse("plans:purchase-create")
		response = self.client.post(url, {"plan_id": self.plan.id}, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(Purchase.objects.count(), 1)
		self.user.refresh_from_db()
		self.assertTrue(self.user.is_premium)

	def test_purchase_plan_rejects_second_active_purchase(self):
		Purchase.objects.create(user=self.user, plan=self.plan, amount=self.plan.price)
		url = reverse("plans:purchase-create")
		response = self.client.post(url, {"plan_id": self.plan.id}, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
