import sys
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone


class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="users_user_set",
        related_query_name="user",
        db_table="auth_user_groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="users_user_set",
        related_query_name="user",
        db_table="auth_user_user_permissions",
    )

    class Meta:
        db_table = "auth_user"
        managed = "test" in sys.argv or "test_coverage" in sys.argv


class Profile(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("admin", "Admin"),
    )

    USER_TYPE_CHOICES = (
        ("seeker", "Job Seeker"),
        ("poster", "Job Poster"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default="seeker",
    )

    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", null=True, blank=True)
    resume_uploaded_at = models.DateTimeField(null=True, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True, default="")
    github_url = models.URLField(max_length=500, blank=True, default="")

    # Resume text extraction
    resume_text = models.TextField(null=True, blank=True)
    resume_last_parsed_at = models.DateTimeField(null=True, blank=True)

    # AI extracted fields
    parsed_resume = models.JSONField(null=True, blank=True)

    # Token invalidation
    jwt_key = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def rotate_jwt_key(self):
        import uuid
        self.jwt_key = str(uuid.uuid4())
        self.save(update_fields=["jwt_key", "updated_at"])

    def __str__(self):
        return self.user.username


class Skill(models.Model):
    CATEGORY_CHOICES = (
        ("technical", "Technical"),
        ("language", "Language"),
        ("other", "Other"),
    )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_otps")
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=128)
    is_verified = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "is_used", "is_verified"]),
            models.Index(fields=["user", "is_used", "created_at"]),
            models.Index(fields=["expires_at", "is_used"]),
        ]

    def __str__(self):
        return f"Password reset OTP for {self.email}"

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])
