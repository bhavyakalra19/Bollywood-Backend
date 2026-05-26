from django.urls import path
from .views import VideoListAPIView

urlpatterns = [
    path('', VideoListAPIView.as_view(), name='video-list'),
]
