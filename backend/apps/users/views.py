import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .auth import KeyRotationRefreshToken

from .models import PasswordResetOTP, Profile, Skill
from .serializers import (
	ChangePasswordSerializer,
	ForgotPasswordSendOTPSerializer,
	ProfileSerializer,
	ResetPasswordSerializer,
	SkillSerializer,
	VerifyOTPSerializer,
)


User = get_user_model()
logger = logging.getLogger(__name__)
PASSWORD_RESET_OTP_EXPIRY_MINUTES = 5
PASSWORD_RESET_OTP_MAX_ATTEMPTS = 5


def get_serializer_error_message(errors):
	for field_errors in errors.values():
		if isinstance(field_errors, list) and field_errors:
			return str(field_errors[0])
		if isinstance(field_errors, dict):
			return get_serializer_error_message(field_errors)
	return "Invalid request."


def generate_otp():
	return f"{secrets.randbelow(1_000_000):06d}"


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

		user = User.objects.filter(email=email).first()
		if user:
			if not user.has_usable_password():
				user.set_password(password)
				user.save(update_fields=["password"])
				profile, _ = Profile.objects.get_or_create(user=user)
			else:
				return Response(
					{"error": "Email already registered"},
					status=status.HTTP_400_BAD_REQUEST,
				)
		else:
			if User.objects.filter(username=username).exists():
				return Response(
					{"error": "Username already exists"},
					status=status.HTTP_400_BAD_REQUEST,
				)
			user = User.objects.create_user(username=username, email=email, password=password)
			profile, _ = Profile.objects.get_or_create(user=user)

		from allauth.account.models import EmailAddress
		email_addr, _ = EmailAddress.objects.get_or_create(user=user, email=email)
		email_addr.verified = True
		email_addr.primary = True
		email_addr.save(update_fields=['verified', 'primary'])

		full_name = request.data.get("full_name")
		mobile_number = request.data.get("mobile_number")
		user_type = request.data.get("user_type")
		allowed_user_types = {choice[0] for choice in Profile.USER_TYPE_CHOICES}

		if user_type and user_type not in allowed_user_types:
			# If user was newly created, it might be better to delete. But if it was existing, we shouldn't.
			# Let's just return an error instead of deleting for safety.
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

		refresh = KeyRotationRefreshToken.for_user(user)
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

		if not user_obj.has_usable_password():
			return Response(
				{"error": "This account was created with a social login. Please use Google/GitHub to sign in, or set a password via Forgot Password."},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		user = authenticate(request=request, username=user_obj.username, password=password)
		if not user:
			return Response(
				{"error": "Invalid credentials"},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		profile, _ = Profile.objects.get_or_create(user=user)
		
		# Rotate JWT key to invalidate all previous sessions/tokens immediately
		profile.rotate_jwt_key()
		
		refresh = KeyRotationRefreshToken.for_user(user)
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
		serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
		if not serializer.is_valid():
			message = self._get_error_message(serializer.errors)
			return Response(
				{"success": False, "message": message},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if check_password(serializer.validated_data["new_password"], request.user.password):
			return Response(
				{"success": False, "message": "New password cannot be the same as the current password."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		request.user.set_password(serializer.validated_data["new_password"])
		request.user.save(update_fields=["password"])
		update_session_auth_hash(request, request.user)

		from allauth.account.models import EmailAddress
		email_addr, _ = EmailAddress.objects.get_or_create(user=request.user, email=request.user.email)
		email_addr.verified = True
		email_addr.primary = True
		email_addr.save(update_fields=['verified', 'primary'])

		return Response(
			{"success": True, "message": "Password changed successfully."},
			status=status.HTTP_200_OK,
		)

	def _get_error_message(self, errors):
		for field_errors in errors.values():
			if isinstance(field_errors, list) and field_errors:
				return str(field_errors[0])
			if isinstance(field_errors, dict):
				return self._get_error_message(field_errors)
		return "Unable to change password."


class ForgotPasswordSendOTPAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = ForgotPasswordSendOTPSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(
				{"success": False, "message": get_serializer_error_message(serializer.errors)},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = serializer.user
		email = serializer.validated_data["email"]
		otp = generate_otp()
		expires_at = timezone.now() + timedelta(minutes=PASSWORD_RESET_OTP_EXPIRY_MINUTES)

		with transaction.atomic():
			PasswordResetOTP.objects.filter(
				user=user,
				email__iexact=email,
				is_used=False,
			).update(is_used=True)

			otp_record = PasswordResetOTP.objects.create(
				user=user,
				email=email,
				otp_code=make_password(otp),
				expires_at=expires_at,
			)

		try:
			send_mail(
				subject="JobSeek Password Reset OTP",
				message=(
					"Hello,\n\n"
					f"Your JobSeek password reset OTP is: {otp}\n\n"
					"This OTP is valid for 5 minutes.\n\n"
					"If you did not request this, ignore this email.\n\n"
					"- JobSeek Team"
				),
				from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
				recipient_list=[email],
				fail_silently=False,
			)
		except Exception:
			logger.exception("Failed to send password reset OTP email.")
			otp_record.mark_used()
			return Response(
				{"success": False, "message": "Unable to send OTP. Please try again later."},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)

		return Response(
			{"success": True, "message": "OTP sent successfully."},
			status=status.HTTP_200_OK,
		)


class VerifyOTPAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = VerifyOTPSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(
				{"success": False, "message": get_serializer_error_message(serializer.errors)},
				status=status.HTTP_400_BAD_REQUEST,
			)

		email = serializer.validated_data["email"]
		otp = serializer.validated_data["otp"]

		with transaction.atomic():
			otp_record = (
				PasswordResetOTP.objects.select_for_update()
				.filter(email__iexact=email, is_used=False)
				.order_by("-created_at")
				.first()
			)

			if not otp_record:
				return Response(
					{"success": False, "message": "Invalid or expired OTP."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if otp_record.is_expired():
				otp_record.mark_used()
				return Response(
					{"success": False, "message": "OTP has expired."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if otp_record.attempts >= PASSWORD_RESET_OTP_MAX_ATTEMPTS:
				otp_record.mark_used()
				return Response(
					{"success": False, "message": "Maximum OTP attempts exceeded."},
					status=status.HTTP_429_TOO_MANY_REQUESTS,
				)

			if not check_password(otp, otp_record.otp_code):
				otp_record.attempts += 1
				update_fields = ["attempts"]
				response_status = status.HTTP_400_BAD_REQUEST
				message = "Invalid OTP."

				if otp_record.attempts >= PASSWORD_RESET_OTP_MAX_ATTEMPTS:
					otp_record.is_used = True
					update_fields.append("is_used")
					response_status = status.HTTP_429_TOO_MANY_REQUESTS
					message = "Maximum OTP attempts exceeded."

				otp_record.save(update_fields=update_fields)
				return Response(
					{"success": False, "message": message},
					status=response_status,
				)

			if not otp_record.is_verified:
				otp_record.is_verified = True
				otp_record.save(update_fields=["is_verified"])

		return Response(
			{"success": True, "message": "OTP verified successfully."},
			status=status.HTTP_200_OK,
		)


class ResetPasswordAPIView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = ResetPasswordSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(
				{"success": False, "message": get_serializer_error_message(serializer.errors)},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = serializer.validated_data["user"]
		email = serializer.validated_data["email"]
		otp = serializer.validated_data["otp"]
		new_password = serializer.validated_data["new_password"]

		with transaction.atomic():
			otp_record = (
				PasswordResetOTP.objects.select_for_update()
				.filter(user=user, email__iexact=email, is_used=False)
				.order_by("-created_at")
				.first()
			)

			if not otp_record:
				return Response(
					{"success": False, "message": "Invalid or expired OTP."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if otp_record.is_expired():
				otp_record.mark_used()
				return Response(
					{"success": False, "message": "OTP has expired."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if not otp_record.is_verified:
				return Response(
					{"success": False, "message": "OTP verification is required before resetting password."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if otp_record.attempts >= PASSWORD_RESET_OTP_MAX_ATTEMPTS:
				otp_record.mark_used()
				return Response(
					{"success": False, "message": "Maximum OTP attempts exceeded."},
					status=status.HTTP_429_TOO_MANY_REQUESTS,
				)

			if not check_password(otp, otp_record.otp_code):
				otp_record.attempts += 1
				update_fields = ["attempts"]
				response_status = status.HTTP_400_BAD_REQUEST
				message = "Invalid OTP."

				if otp_record.attempts >= PASSWORD_RESET_OTP_MAX_ATTEMPTS:
					otp_record.is_used = True
					update_fields.append("is_used")
					response_status = status.HTTP_429_TOO_MANY_REQUESTS
					message = "Maximum OTP attempts exceeded."

				otp_record.save(update_fields=update_fields)
				return Response(
					{"success": False, "message": message},
					status=response_status,
				)

			user.set_password(new_password)
			user.save(update_fields=["password"])
			otp_record.mark_used()

			from allauth.account.models import EmailAddress
			email_addr, _ = EmailAddress.objects.get_or_create(user=user, email=email)
			email_addr.verified = True
			email_addr.primary = True
			email_addr.save(update_fields=['verified', 'primary'])

			PasswordResetOTP.objects.filter(
				user=user,
				email__iexact=email,
				is_used=False,
			).update(is_used=True)

		return Response(
			{"success": True, "message": "Password reset successfully."},
			status=status.HTTP_200_OK,
		)


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


class BulkSkillUpdateAPIView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		profile, _ = Profile.objects.get_or_create(user=request.user)
		skills_data = request.data.get("skills", [])
		
		# Expected format: [{"name": "Python", "category": "technical"}, ...]
		
		# Clear existing skills or handle sync
		# For simplicity, we'll clear and recreate or sync based on name/category
		
		# Let's group skills by category from the request
		categories = ["technical", "language", "other"]
		
		new_skills = []
		for skill_item in skills_data:
			name = skill_item.get("name")
			category = skill_item.get("category")
			if name and category in categories:
				new_skills.append(Skill(profile=profile, name=name, category=category))
		
		# Transactional update
		from django.db import transaction
		try:
			with transaction.atomic():
				# Remove old skills
				Skill.objects.filter(profile=profile).delete()
				# Bulk create new ones
				Skill.objects.bulk_create(new_skills)
		except Exception as e:
			return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
			
		return Response(ProfileSerializer(profile, context={"request": request}).data)


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


class ResumeAPIView(APIView):
	"""
	Secure endpoint to retrieve the current user's parsed resume.
	Used by FastAPI SeekBot to fetch resume text for AI analysis.

	GET /api/users/me/resume/
	"""
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		profile, _ = Profile.objects.get_or_create(user=request.user)

		if not profile.resume:
			return Response(
				{
					"success": False,
					"message": "No resume uploaded.",
				},
				status=status.HTTP_404_NOT_FOUND,
			)

		# Build resume URL without exposing filesystem paths
		resume_url = request.build_absolute_uri(profile.resume.url) if profile.resume else None

		return Response(
			{
				"success": True,
				"resume_uploaded": True,
				"resume_text": profile.resume_text or "",
				"resume_url": resume_url,
				"resume_last_parsed_at": (
					profile.resume_last_parsed_at.isoformat()
					if profile.resume_last_parsed_at
					else None
				),
			},
			status=status.HTTP_200_OK,
		)
