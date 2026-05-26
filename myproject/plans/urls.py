from django.urls import path

from .views import MyPurchaseListAPIView, PlanListAPIView, PurchaseCreateAPIView

app_name = "plans"

urlpatterns = [
    path("plans/", PlanListAPIView.as_view(), name="plan-list"),
    path("plans/purchase/", PurchaseCreateAPIView.as_view(), name="purchase-create"),
    path("plans/my-purchases/", MyPurchaseListAPIView.as_view(), name="my-purchases"),
]
