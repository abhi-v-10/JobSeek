from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer,
    ChatSessionDetailSerializer,
    ChatMessageSerializer,
    ChatMessageCreateSerializer
)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ChatSession and its messages.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_value_regex = "[0-9a-fA-F-]+"

    def get_queryset(self):
        """
        Only return active sessions belonging to the current user.
        """
        return ChatSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by("-updated_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ChatSessionDetailSerializer
        return ChatSessionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete by marking session as inactive.
        """
        session = self.get_object()
        session.is_active = False
        session.save()
        return Response({
            "success": True,
            "message": "Session deleted successfully"
        })

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, id=None):
        """
        POST: Save a new message (user or assistant) to the session.
        GET: Retrieve all messages for the session.
        """
        session = self.get_object()

        if request.method == "POST":
            serializer = ChatMessageCreateSerializer(data=request.data)
            if serializer.is_valid():
                # Save message linked to session
                message = serializer.save(session=session)

                # Update session timestamp
                session.updated_at = timezone.now()
                session.save(update_fields=["updated_at"])

                # Return success response with saved message data
                response_serializer = ChatMessageSerializer(message)
                return Response({
                    "success": True,
                    "message": "Message saved successfully.",
                    "data": response_serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # GET method: List all messages for this session
        messages = session.messages.all().order_by("created_at")
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })