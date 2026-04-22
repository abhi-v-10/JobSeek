from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "receiver",
            "content",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "sender"]
