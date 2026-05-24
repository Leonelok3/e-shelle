from django.contrib import admin

from .models import ConversationSession, Message


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_key", "created_at", "updated_at"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "user__email", "session_key"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "module_detected", "created_at"]
    list_filter = ["role", "module_detected", "created_at"]
    search_fields = ["content"]
    readonly_fields = ["created_at"]

# Register your models here.
