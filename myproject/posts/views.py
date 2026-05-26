from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Genders, Location, Post, PostApplication, Productions, SavedPost
from .serializers import GenderSerializer, LocationSerializer, PostListSerializer


class PostListAPIView(generics.ListAPIView):
	serializer_class = PostListSerializer
	permission_classes = [permissions.AllowAny]

	def get_queryset(self):
		queryset = Post.objects.filter(is_active=True).select_related(
			"created_by", "location_option"
		).prefetch_related("genders")
		location_id = self.request.query_params.get("location")
		# production_type_id removed
		gender_id = self.request.query_params.get("gender")
		age = self.request.query_params.get("age")

		if location_id:
			queryset = queryset.filter(location_option_id=location_id)
		# production_type_id filter removed
		if gender_id:
			queryset = queryset.filter(genders__id=gender_id)
		if age:
			try:
				age_value = int(age)
			except (TypeError, ValueError):
				age_value = None
			if age_value is not None:
				queryset = queryset.filter(
					Q(min_age__isnull=True) | Q(min_age__lte=age_value),
					Q(max_age__isnull=True) | Q(max_age__gte=age_value),
				)

		return queryset.distinct()


class SavedPostListAPIView(generics.ListAPIView):
	serializer_class = PostListSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		return (
			Post.objects.filter(saved_by__user=self.request.user, is_active=True)
			.select_related("created_by", "location_option")
			.prefetch_related("genders")
			.distinct()
		)


class AppliedPostListAPIView(generics.ListAPIView):
	serializer_class = PostListSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		return (
			Post.objects.filter(applications__user=self.request.user, is_active=True)
			.select_related("created_by", "location_option")
			.prefetch_related("genders")
			.distinct()
		)


class LocationListAPIView(generics.ListAPIView):
	serializer_class = LocationSerializer
	permission_classes = [permissions.AllowAny]
	queryset = Location.objects.filter(is_active=True)





class PostFilterOptionsAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def get(self, request):
		locations = LocationSerializer(Location.objects.filter(is_active=True), many=True).data
		genders = GenderSerializer(Genders.objects.all(), many=True).data
		return Response({"locations": locations, "genders": genders})


class PostSaveAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, post_id):
		post = get_object_or_404(Post, id=post_id, is_active=True)
		_, created = SavedPost.objects.get_or_create(user=request.user, post=post)
		if created:
			return Response({"detail": "Post saved successfully."}, status=status.HTTP_201_CREATED)
		return Response({"detail": "Post is already saved."}, status=status.HTTP_200_OK)


class PostUnsaveAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, post_id):
		post = get_object_or_404(Post, id=post_id)
		deleted_count, _ = SavedPost.objects.filter(user=request.user, post=post).delete()
		if deleted_count == 0:
			return Response({"detail": "Post was not saved."}, status=status.HTTP_200_OK)
		return Response({"detail": "Post unsaved successfully."}, status=status.HTTP_200_OK)


class PostApplicationAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, post_id):
		post = get_object_or_404(Post, id=post_id, is_active=True)
		_, created = PostApplication.objects.get_or_create(user=request.user, post=post)
		if created:
			return Response({"detail": "Post application submitted successfully."}, status=status.HTTP_201_CREATED)
		return Response({"detail": "You have already applied to this post."}, status=status.HTTP_200_OK)


class PostUnapplyAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, post_id):
		post = get_object_or_404(Post, id=post_id)
		deleted_count, _ = PostApplication.objects.filter(user=request.user, post=post).delete()
		if deleted_count == 0:
			return Response({"detail": "You had not applied to this post."}, status=status.HTTP_200_OK)
		return Response({"detail": "Application withdrawn successfully."}, status=status.HTTP_200_OK)
