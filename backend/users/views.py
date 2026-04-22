from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile, Skill
from .serializers import ProfileSerializer, SkillSerializer


class CreateUserAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		username = (request.data.get("username") or "").strip()
		email = (request.data.get("email") or "").strip()
		password = request.data.get("password") or ""

		if not username or not password:
			return Response(
				{"detail": "username and password are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if len(password) < 6:
			return Response(
				{"detail": "Password must be at least 6 characters long."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if User.objects.filter(username=username).exists():
			return Response(
				{"detail": "A user with this username already exists."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = User.objects.create_user(username=username, email=email, password=password)
		profile, _ = Profile.objects.get_or_create(user=user)

		full_name = request.data.get("full_name")
		mobile_number = request.data.get("mobile_number")
		user_type = request.data.get("user_type")
		allowed_user_types = {choice[0] for choice in Profile.USER_TYPE_CHOICES}

		if user_type and user_type not in allowed_user_types:
			user.delete()
			return Response(
				{"detail": "Invalid user_type. Use 'seeker' or 'poster'."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if full_name is not None:
			profile.full_name = full_name
		if mobile_number is not None:
			profile.mobile_number = mobile_number
		if user_type:
			profile.user_type = user_type
		profile.save()

		refresh = RefreshToken.for_user(user)
		return Response(
			{
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
				},
				"profile": ProfileSerializer(profile).data,
				"refresh": str(refresh),
				"access": str(refresh.access_token),
			},
			status=status.HTTP_201_CREATED,
		)


class LoginAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		username = (request.data.get("username") or "").strip()
		password = request.data.get("password") or ""

		if not username or not password:
			return Response(
				{"detail": "username and password are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = authenticate(request=request, username=username, password=password)
		if not user:
			return Response(
				{"detail": "Invalid credentials."},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		profile, _ = Profile.objects.get_or_create(user=user)
		refresh = RefreshToken.for_user(user)
		return Response(
			{
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
				},
				"profile": ProfileSerializer(profile).data,
				"refresh": str(refresh),
				"access": str(refresh.access_token),
			},
			status=status.HTTP_200_OK,
		)


class CurrentProfileAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def _get_profile(self, user):
		profile, _ = Profile.objects.get_or_create(user=user)
		return profile

	def get(self, request):
		profile = self._get_profile(request.user)
		serializer = ProfileSerializer(profile)
		return Response(serializer.data)

	def patch(self, request):
		profile = self._get_profile(request.user)
		serializer = ProfileSerializer(profile, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)

	def put(self, request):
		profile = self._get_profile(request.user)
		serializer = ProfileSerializer(profile, data=request.data, partial=False)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)


class SkillCreateAPIView(generics.CreateAPIView):
	serializer_class = SkillSerializer
	permission_classes = [permissions.IsAuthenticated]

	def perform_create(self, serializer):
		profile, _ = Profile.objects.get_or_create(user=self.request.user)
		serializer.save(profile=profile)


class SkillDeleteAPIView(generics.DestroyAPIView):
	serializer_class = SkillSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		return Skill.objects.filter(profile__user=self.request.user)


class SwitchUserRoleAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def patch(self, request):
		user_type = request.data.get("user_type")
		allowed_user_types = {choice[0] for choice in Profile.USER_TYPE_CHOICES}

		if user_type not in allowed_user_types:
			raise ValidationError({"user_type": "Use 'seeker' or 'poster'."})

		profile, _ = Profile.objects.get_or_create(user=request.user)
		profile.user_type = user_type
		profile.save(update_fields=["user_type", "updated_at"])

		return Response(ProfileSerializer(profile).data, status=status.HTTP_200_OK)
