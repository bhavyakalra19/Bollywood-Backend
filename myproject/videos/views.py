from rest_framework import generics, permissions
from .models import Video
from .serializers import VideoSerializer

class VideoListAPIView(generics.ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Video.objects.filter(is_active=True).order_by('-updated_at')
