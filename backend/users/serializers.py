from rest_framework import serializers

from .models import Profile, Skill


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

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
            "linkedin_url",
            "github_url",
            "parsed_resume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "parsed_resume", "user"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "profile", "name", "category", "created_at"]
        read_only_fields = ["created_at", "profile"]
