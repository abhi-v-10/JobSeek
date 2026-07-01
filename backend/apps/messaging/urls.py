from django.urls import path
from .views import (
    ConversationListAPIView, 
    ConversationMessagesAPIView, 
    MessageCreateAPIView,
    MessageListAPIView
)

app_name = "messaging"

urlpatterns = [
    path("conversations/", ConversationListAPIView.as_view(), name="conversation-list"),
    path("conversations/<int:id>/messages/", ConversationMessagesAPIView.as_view(), name="conversation-messages"),
    path("", MessageCreateAPIView.as_view(), name="message-create"),
    path("history/", MessageListAPIView.as_view(), name="message-history"),
]
