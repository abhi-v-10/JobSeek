from rest_framework import serializers
from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "session",
            "role",
            "message_type",
            "content",
            "metadata",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["role", "message_type", "content", "metadata"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value.strip()


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ["id", "title", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "is_active",
            "created_at",
            "updated_at",
            "messages"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "messages"]