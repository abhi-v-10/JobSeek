import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import Profile, Skill
from .utils.resume_parser import extract_resume_text

logger = logging.getLogger(__name__)


User = get_user_model()


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "profile", "name", "category", "created_at"]
        read_only_fields = ["created_at", "profile"]


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "username",
            "email",
            "full_name",
            "mobile_number",
            "role",
            "user_type",
            "resume",
            "profile_picture",
            "resume_uploaded_at",
            "resume_text",
            "resume_last_parsed_at",
            "linkedin_url",
            "github_url",
            "parsed_resume",
            "created_at",
            "updated_at",
            "skills",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "parsed_resume",
            "user",
            "resume_text",
            "resume_last_parsed_at",
        ]

    def update(self, instance, validated_data):
        """
        Override update to auto-parse resume text when a new file is uploaded.
        """
        resume_file = validated_data.get("resume", None)
        instance = super().update(instance, validated_data)

        # Auto-parse when a new resume file is provided
        if resume_file:
            try:
                text = extract_resume_text(instance.resume.path)
                instance.resume_text = text
                instance.resume_last_parsed_at = timezone.now()
                instance.resume_uploaded_at = timezone.now()
                instance.save(
                    update_fields=[
                        "resume_text",
                        "resume_last_parsed_at",
                        "resume_uploaded_at",
                    ]
                )
            except (ValueError, Exception) as exc:
                logger.warning("Resume auto-parse failed for user %s: %s", instance.user_id, exc)
                # Don't block the upload — the file is saved, parsing can be retried

        # If resume was explicitly cleared (set to None/empty), also clear parsed data
        if "resume" in validated_data and not validated_data["resume"]:
            instance.resume_text = None
            instance.resume_last_parsed_at = None
            instance.save(update_fields=["resume_text", "resume_last_parsed_at"])

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "blank": "Old password is required.",
            "required": "Old password is required.",
        },
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        min_length=8,
        error_messages={
            "blank": "New password is required.",
            "min_length": "New password must be at least 8 characters long.",
            "required": "New password is required.",
        },
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "blank": "Confirm password is required.",
            "required": "Confirm password is required.",
        },
    )

    default_error_messages = {
        "password_mismatch": "New password and confirm password do not match.",
    }

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": self.error_messages["password_mismatch"]}
            )

        user = self.context["request"].user
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs


class ForgotPasswordSendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "blank": "Email is required.",
            "invalid": "Enter a valid email address.",
            "required": "Email is required.",
        },
    )

    def validate_email(self, value):
        email = value.strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            raise serializers.ValidationError("No active account found with this email address.")

        self.user = user
        return user.email


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "blank": "Email is required.",
            "invalid": "Enter a valid email address.",
            "required": "Email is required.",
        },
    )
    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        trim_whitespace=True,
        error_messages={
            "blank": "OTP is required.",
            "max_length": "OTP must be 6 digits.",
            "min_length": "OTP must be 6 digits.",
            "required": "OTP is required.",
        },
    )

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be 6 digits.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "blank": "Email is required.",
            "invalid": "Enter a valid email address.",
            "required": "Email is required.",
        },
    )
    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        trim_whitespace=True,
        error_messages={
            "blank": "OTP is required.",
            "max_length": "OTP must be 6 digits.",
            "min_length": "OTP must be 6 digits.",
            "required": "OTP is required.",
        },
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        min_length=8,
        error_messages={
            "blank": "New password is required.",
            "min_length": "New password must be at least 8 characters long.",
            "required": "New password is required.",
        },
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        error_messages={
            "blank": "Confirm password is required.",
            "required": "Confirm password is required.",
        },
    )

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be 6 digits.")
        return value

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"].strip(), is_active=True).first()
        if not user:
            raise serializers.ValidationError({"email": "No active account found with this email address."})

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirm password do not match."}
            )

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        attrs["email"] = user.email
        attrs["user"] = user
        return attrs
