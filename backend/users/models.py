from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField

class Profile(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("admin", "Admin"),
    )

    USER_TYPE_CHOICES = (
        ("seeker", "Job Seeker"),
        ("poster", "Job Poster"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default="seeker",
    )

    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    resume_uploaded_at = models.DateTimeField(null=True, blank=True)

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
