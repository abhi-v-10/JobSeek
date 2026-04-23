from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message, Conversation
from jobs.serializers import JobSerializer

User = get_user_model()

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    
    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "sender_username",
            "receiver",
            "content",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "sender"]

class ConversationSerializer(serializers.ModelSerializer):
    participant_1 = UserSimpleSerializer(read_only=True)
    participant_2 = UserSimpleSerializer(read_only=True)
    job = JobSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "participant_1",
            "participant_2",
            "job",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if last:
            return MessageSerializer(last).data
        return None

    def get_unread_count(self, obj):
        user = self.context.get("request").user
        return obj.messages.filter(receiver=user, is_read=False).count()
