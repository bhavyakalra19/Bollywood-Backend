from django.db import models

class Video(models.Model):
    name = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name
