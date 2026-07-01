from django.contrib import admin
from .models import Message, Conversation

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "participant_1", "participant_2", "job", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("participant_1__username", "participant_2__username", "job__position")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "receiver", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__username", "sender__email", "receiver__username", "receiver__email", "content")
    readonly_fields = ("created_at", "updated_at")