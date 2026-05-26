from rest_framework import generics, permissions

from .models import Plan, Purchase
from .serializers import PlanSerializer, PurchaseCreateSerializer, PurchaseSerializer


class PlanListAPIView(generics.ListAPIView):
	serializer_class = PlanSerializer
	permission_classes = [permissions.AllowAny]

	def get_queryset(self):
		return Plan.objects.filter(is_active=True)


class PurchaseCreateAPIView(generics.CreateAPIView):
	serializer_class = PurchaseCreateSerializer
	permission_classes = [permissions.IsAuthenticated]


class MyPurchaseListAPIView(generics.ListAPIView):
	serializer_class = PurchaseSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		return Purchase.objects.filter(user=self.request.user).select_related("plan")
