from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile, Skill
from .serializers import ProfileSerializer, SkillSerializer


User = get_user_model()


class CreateUserAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def _build_success_response(self, request, user, profile, refresh, message, status_code):
		return Response(
			{
				"message": message,
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
				},
				"profile": ProfileSerializer(profile, context={"request": request}).data,
				"tokens": {
					"access": str(refresh.access_token),
					"refresh": str(refresh),
				},
			},
			status=status_code,
		)

	def post(self, request):
		username = (request.data.get("username") or "").strip()
		email = (request.data.get("email") or "").strip()
		password = request.data.get("password") or ""

		if not username or not password:
			return Response(
				{"error": "Username and password are required"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if len(password) < 6:
			return Response(
				{"error": "Password must be at least 6 characters long"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if User.objects.filter(username=username).exists():
			return Response(
				{"error": "Username already exists"},
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
				{"error": "Invalid user_type. Use seeker or poster"},
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
		return self._build_success_response(
			request=request,
			user=user,
			profile=profile,
			refresh=refresh,
			message="User registered successfully",
			status_code=status.HTTP_201_CREATED,
		)


class LoginAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def _build_success_response(self, request, user, profile, refresh, message, status_code):
		return Response(
			{
				"message": message,
				"user": {
					"id": user.id,
					"username": user.username,
					"email": user.email,
				},
				"profile": ProfileSerializer(profile, context={"request": request}).data,
				"tokens": {
					"access": str(refresh.access_token),
					"refresh": str(refresh),
				},
			},
			status=status_code,
		)

	def post(self, request):
		email = (request.data.get("email") or "").strip()
		password = request.data.get("password") or ""

		if not email or not password:
			return Response(
				{"error": "Email and password are required"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user_obj = User.objects.filter(email=email).first()
		if not user_obj:
			return Response(
				{"error": "Invalid credentials"},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		user = authenticate(request=request, username=user_obj.username, password=password)
		if not user:
			return Response(
				{"error": "Invalid credentials"},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		profile, _ = Profile.objects.get_or_create(user=user)
		refresh = RefreshToken.for_user(user)
		return self._build_success_response(
			request=request,
			user=user,
			profile=profile,
			refresh=refresh,
			message="Login successful",
			status_code=status.HTTP_200_OK,
		)


class LogoutAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		try:
			# If the client sends the refresh token, we can blacklist it
			refresh_token = request.data.get("refresh")
			if refresh_token:
				token = RefreshToken(refresh_token)
				token.blacklist()
		except Exception:
			# If blacklisting fails (e.g. token_blacklist app not installed or token invalid), 
			# we gracefully continue to log them out from the session anyway.
			pass

		# Log the user out of the Django session (if session authentication is used alongside JWT)
		from django.contrib.auth import logout
		logout(request)

		return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)


class CurrentProfileAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser, JSONParser]

	def _get_profile(self, user):
		profile, _ = Profile.objects.get_or_create(user=user)
		return profile

	def _serialize_profile(self, profile, request):
		return ProfileSerializer(profile, context={"request": request})

	def get(self, request):
		profile = self._get_profile(request.user)
		serializer = self._serialize_profile(profile, request)
		return Response(serializer.data)

	def patch(self, request):
		if "email" in request.data:
			return Response(
				{"error": "Email cannot be changed after registration"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		username = request.data.get("username")
		if username is not None:
			username = username.strip()
			if not username:
				return Response({"error": "Username cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
			if User.objects.exclude(pk=request.user.pk).filter(username=username).exists():
				return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

		profile = self._get_profile(request.user)
		update_data = request.data.copy()
		update_data.pop("email", None)
		update_data.pop("username", None)
		serializer = ProfileSerializer(profile, data=update_data, partial=True, context={"request": request})
		serializer.is_valid(raise_exception=True)
		serializer.save()

		if username is not None:
			request.user.username = username
			request.user.save(update_fields=["username"])

		return Response(self._serialize_profile(profile, request).data)

	def put(self, request):
		if "email" in request.data:
			return Response(
				{"error": "Email cannot be changed after registration"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		username = request.data.get("username")
		if username is not None:
			username = username.strip()
			if not username:
				return Response({"error": "Username cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
			if User.objects.exclude(pk=request.user.pk).filter(username=username).exists():
				return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

		profile = self._get_profile(request.user)
		update_data = request.data.copy()
		update_data.pop("email", None)
		update_data.pop("username", None)
		serializer = ProfileSerializer(profile, data=update_data, partial=False, context={"request": request})
		serializer.is_valid(raise_exception=True)
		serializer.save()

		if username is not None:
			request.user.username = username
			request.user.save(update_fields=["username"])

		return Response(self._serialize_profile(profile, request).data)


class ChangePasswordAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		current_password = request.data.get("current_password") or ""
		new_password = request.data.get("new_password") or ""
		confirm_password = request.data.get("confirm_password") or ""

		if not current_password or not new_password or not confirm_password:
			return Response(
				{"error": "Current password, new password, and confirm password are required"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if not request.user.check_password(current_password):
			return Response(
				{"error": "Current password is incorrect"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if new_password != confirm_password:
			return Response(
				{"error": "New passwords do not match"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if len(new_password) < 6:
			return Response(
				{"error": "Password must be at least 6 characters long"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		request.user.set_password(new_password)
		request.user.save(update_fields=["password"])
		return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)


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

class DashboardAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		profile, _ = Profile.objects.get_or_create(user=request.user)
		return Response({
			"message": f"Welcome to the dashboard, {profile.full_name or request.user.username}!",
			"user_type": profile.user_type,
			"stats": {
				"total_jobs": 0,
				"total_messages": 0
			}
		}, status=status.HTTP_200_OK)
