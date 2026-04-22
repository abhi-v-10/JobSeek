from rest_framework import serializers

from .models import Profile, Skill


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "full_name",
            "mobile_number",
            "role",
            "user_type",
            "resume",
            "resume_uploaded_at",
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
