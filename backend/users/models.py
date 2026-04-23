from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    # Keep canonical display name in Profile.full_name only.
    first_name = None
    last_name = None
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
        managed = False

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

    # AI extracted fields
    parsed_resume = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class Skill(models.Model):
    CATEGORY_CHOICES = (
        ("technical", "Technical"),
        ("soft", "Soft"),
        ("language", "Language"),
        ("other", "Other"),
    )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.profile.user.username})"
