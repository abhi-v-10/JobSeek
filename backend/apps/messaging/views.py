from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Message, Conversation
from .serializers import MessageSerializer, ConversationSerializer


User = get_user_model()


class ConversationListAPIView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            Q(participant_1=self.request.user) | Q(participant_2=self.request.user)
        ).order_by("-updated_at")


class ConversationMessagesAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get("id")
        conversation = get_object_or_404(
            Conversation, 
            Q(participant_1=self.request.user) | Q(participant_2=self.request.user),
            id=conversation_id
        )
        # Mark messages as read
        Message.objects.filter(conversation=conversation, receiver=self.request.user).update(is_read=True)
        return conversation.messages.order_by("created_at")


class MessageCreateAPIView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        conversation_id = self.request.data.get("conversation")
        if not conversation_id:
            raise ValidationError({"conversation": "This field is required."})

        conversation = get_object_or_404(
            Conversation,
            Q(participant_1=self.request.user) | Q(participant_2=self.request.user),
            id=conversation_id
        )
        
        receiver = conversation.participant_2 if conversation.participant_1 == self.request.user else conversation.participant_1
        
        instance = serializer.save(sender=self.request.user, receiver=receiver, conversation=conversation)
        # Update conversation timestamp
        conversation.save()
        
        # Broadcast the message to WebSocket room group
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation.id}'
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': serializer.data
            }
        )

# Keep for legacy/internal use if needed
class MessageListAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        target_user_id = self.request.query_params.get("user_id")
        if not target_user_id:
            raise ValidationError({"user_id": "This query parameter is required."})

        return Message.objects.select_related("sender", "receiver").filter(
            Q(sender=self.request.user, receiver_id=target_user_id)
            | Q(sender_id=target_user_id, receiver=self.request.user)
        ).order_by("created_at")
