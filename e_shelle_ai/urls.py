"""e_shelle_ai/urls.py — Routes de l'agent IA central E-Shelle"""
from django.urls import path
from . import views

app_name = "eshelle_ai"

urlpatterns = [
    path("admin-dashboard/",                 views.admin_dashboard,                 name="admin_dashboard"),

    # Interface principale
    path("",                                views.ChatView.as_view(),               name="chat"),
    path("c/<int:pk>/",                     views.ConversationLoadView.as_view(),   name="conversation"),

    # API Chat (streaming SSE)
    path("api/chat/",                       views.ChatAPIView.as_view(),            name="api_chat"),

    # API Image (DALL-E 3 / Imagen 3)
    path("api/image/",                      views.GenerateImageView.as_view(),      name="api_image"),

    # API Video (Veo)
    path("api/video/start/",                views.StartVideoView.as_view(),         name="api_video_start"),
    path("api/video/poll/",                 views.PollVideoView.as_view(),          name="api_video_poll"),

    # Conversations
    path("conversations/",                  views.ConversationListView.as_view(),   name="conversations"),
    path("conversations/new/",              views.NewConversationView.as_view(),    name="conversation_new"),
    path("conversations/<int:pk>/delete/",  views.DeleteConversationView.as_view(), name="conversation_delete"),

    # Utilitaires
    path("quota/",                          views.QuotaStatusView.as_view(),        name="quota"),
    path("memory/clear/",                   views.ClearMemoryView.as_view(),        name="memory_clear"),
]
