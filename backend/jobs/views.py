from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from users.models import Profile

from .models import Job
from .serializers import JobSerializer


class JobListCreateAPIView(generics.ListCreateAPIView):
	serializer_class = JobSerializer

	def get_queryset(self):
		return Job.objects.select_related("posted_by").order_by("-created_at")

	def get_permissions(self):
		if self.request.method == "POST":
			return [permissions.IsAuthenticated()]
		return [permissions.AllowAny()]

	def perform_create(self, serializer):
		profile, _ = Profile.objects.get_or_create(user=self.request.user)
		if profile.user_type != "poster":
			raise PermissionDenied("Only users with poster role can create jobs.")
		serializer.save(posted_by=self.request.user)


class JobDetailAPIView(generics.RetrieveAPIView):
	queryset = Job.objects.select_related("posted_by")
	serializer_class = JobSerializer
	lookup_field = "id"
	permission_classes = [permissions.AllowAny]
