from django.urls import path

from .views import (
    AppliedPostListAPIView,
    LocationListAPIView,
    PostApplicationAPIView,
    PostFilterOptionsAPIView,
    PostListAPIView,
    PostSaveAPIView,
    SavedPostListAPIView,
    PostUnapplyAPIView,
    PostUnsaveAPIView,
)

app_name = "posts"

urlpatterns = [
    path("posts/filter-options/", PostFilterOptionsAPIView.as_view(), name="post-filter-options"),
    path("posts/locations/", LocationListAPIView.as_view(), name="location-list"),
    path("posts/", PostListAPIView.as_view(), name="post-list"),
    path("posts/saved/", SavedPostListAPIView.as_view(), name="saved-post-list"),
    path("posts/applied/", AppliedPostListAPIView.as_view(), name="applied-post-list"),
    path("posts/<int:post_id>/save/", PostSaveAPIView.as_view(), name="post-save"),
    path("posts/<int:post_id>/unsave/", PostUnsaveAPIView.as_view(), name="post-unsave"),
    path("posts/<int:post_id>/apply/", PostApplicationAPIView.as_view(), name="post-apply"),
    path("posts/<int:post_id>/unapply/", PostUnapplyAPIView.as_view(), name="post-unapply"),
]
