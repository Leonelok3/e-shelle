from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from .models import (
    FacebookPageConfig,
    ContentRule,
    PostTemplate,
    ScheduledPost,
    PublishedPost,
    AgentLog,
    AgentStats,
)


# ------------------------------------------------------------------ #
# FacebookPageConfig                                                  #
# ------------------------------------------------------------------ #

@admin.register(FacebookPageConfig)
class FacebookPageConfigAdmin(admin.ModelAdmin):
    list_display = (
        "page_name", "page_id", "is_active", "token_status",
        "last_token_refresh", "updated_at"
    )
    list_filter = ("is_active",)
    readonly_fields = ("created_at", "updated_at", "last_token_refresh")
    fieldsets = (
        ("Informations de la page", {
            "fields": ("page_id", "page_name", "is_active")
        }),
        ("Tokens d'accès", {
            "fields": ("page_access_token", "app_id", "app_secret", "token_expires_at"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "last_token_refresh"),
            "classes": ("collapse",),
        }),
    )
    actions = ["verify_token_action", "test_publish_action"]

    def token_status(self, obj):
        if not obj.page_access_token:
            return format_html('<span style="color:#dc3545;font-weight:bold">Manquant</span>')
        if not obj.token_expires_at:
            return format_html('<span style="color:#b7791f;font-weight:bold">Non vérifié auprès de Meta</span>')
        if obj.is_token_valid():
            return format_html('<span style="color:#b7791f;font-weight:bold">Date d’expiration future · vérifier auprès de Meta</span>')
        return format_html('<span style="color:#dc3545;font-weight:bold">Expiré</span>')
    token_status.short_description = "Statut Token"

    def verify_token_action(self, request, queryset):
        from .facebook_api import FacebookAPIClient
        for config in queryset:
            client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
            info = client.verify_token()
            if info.get("is_valid"):
                self.message_user(request, f"✓ Token valide pour {config.page_name}", messages.SUCCESS)
            else:
                self.message_user(request, f"✗ Token INVALIDE pour {config.page_name}", messages.ERROR)
    verify_token_action.short_description = "Vérifier le token Facebook"

    def test_publish_action(self, request, queryset):
        from .facebook_api import FacebookAPIClient, FacebookAPIError
        for config in queryset:
            try:
                client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
                result = client.publish_text_post(
                    "🤖 Test de publication automatique E-Shelle Auto-Post. "
                    "Ce post confirme que l'intégration Facebook fonctionne correctement."
                )
                self.message_user(
                    request,
                    f"✓ Post test publié sur {config.page_name} — ID: {result.get('id')}",
                    messages.SUCCESS,
                )
            except FacebookAPIError as e:
                self.message_user(request, f"✗ Erreur pour {config.page_name}: {e}", messages.ERROR)
    test_publish_action.short_description = "Publier un post de test"


# ------------------------------------------------------------------ #
# ContentRule                                                         #
# ------------------------------------------------------------------ #

@admin.register(ContentRule)
class ContentRuleAdmin(admin.ModelAdmin):
    list_display = (
        "section", "is_active", "tone", "post_frequency_per_day",
        "preferred_hours", "include_emoji", "include_hashtags"
    )
    list_filter = ("is_active", "tone", "section")
    list_editable = ("is_active", "post_frequency_per_day")
    fieldsets = (
        ("Configuration principale", {
            "fields": ("section", "is_active", "tone", "post_frequency_per_day", "preferred_hours")
        }),
        ("Options de contenu", {
            "fields": ("include_emoji", "include_hashtags", "max_post_length", "custom_instructions")
        }),
    )


# ------------------------------------------------------------------ #
# PostTemplate                                                        #
# ------------------------------------------------------------------ #

@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "template_type", "is_active", "usage_count", "created_at")
    list_filter = ("section", "template_type", "is_active")
    search_fields = ("name", "template_body")
    readonly_fields = ("usage_count", "created_at")


# ------------------------------------------------------------------ #
# ScheduledPost                                                       #
# ------------------------------------------------------------------ #

@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = (
        "title", "section", "status", "scheduled_at",
        "ai_generated", "requires_approval", "retry_count", "created_at"
    )
    list_filter = ("status", "section", "ai_generated", "requires_approval")
    search_fields = ("title", "content")
    readonly_fields = ("id", "created_at", "updated_at", "retry_count", "error_message")
    actions = ["approve_posts", "cancel_posts", "publish_now_action"]

    fieldsets = (
        ("Informations", {
            "fields": ("id", "page_config", "section", "title", "status")
        }),
        ("Contenu", {
            "fields": ("content", "image_url", "link_url")
        }),
        ("Planification", {
            "fields": ("scheduled_at", "requires_approval", "ai_generated")
        }),
        ("Suivi", {
            "fields": ("retry_count", "error_message", "source_object_id", "source_object_type"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def approve_posts(self, request, queryset):
        updated = queryset.filter(status="en_attente").update(status="approuve")
        self.message_user(request, f"{updated} posts approuvés.", messages.SUCCESS)
    approve_posts.short_description = "Approuver les posts sélectionnés"

    def cancel_posts(self, request, queryset):
        updated = queryset.exclude(status="publie").update(status="annule")
        self.message_user(request, f"{updated} posts annulés.", messages.WARNING)
    cancel_posts.short_description = "Annuler les posts sélectionnés"

    def publish_now_action(self, request, queryset):
        from .tasks import publish_scheduled_post
        count = 0
        for post in queryset.filter(status__in=("en_attente", "approuve")):
            publish_scheduled_post.delay(str(post.id))
            count += 1
        self.message_user(request, f"{count} posts envoyés en publication.", messages.SUCCESS)
    publish_now_action.short_description = "Publier maintenant (via Celery)"


# ------------------------------------------------------------------ #
# PublishedPost                                                       #
# ------------------------------------------------------------------ #

@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = (
        "section", "content_preview", "published_at",
        "likes_count", "comments_count", "shares_count", "facebook_link"
    )
    list_filter = ("section", "published_at")
    search_fields = ("content", "facebook_post_id")
    readonly_fields = (
        "id", "facebook_post_id", "published_at",
        "likes_count", "comments_count", "shares_count",
        "reach", "stats_updated_at"
    )
    date_hierarchy = "published_at"
    actions = ["sync_stats_action"]

    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_preview.short_description = "Aperçu du contenu"

    def facebook_link(self, obj):
        url = obj.get_facebook_url()
        return format_html('<a href="{}" target="_blank">Voir sur FB</a>', url)
    facebook_link.short_description = "Lien Facebook"

    def sync_stats_action(self, request, queryset):
        from .tasks import sync_post_stats
        for post in queryset:
            sync_post_stats.delay(str(post.id))
        self.message_user(request, f"Synchronisation lancée pour {queryset.count()} posts.", messages.INFO)
    sync_stats_action.short_description = "Synchroniser les statistiques"


# ------------------------------------------------------------------ #
# AgentLog                                                            #
# ------------------------------------------------------------------ #

@admin.register(AgentLog)
class AgentLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "level_badge", "section", "action", "message_preview",
        "tokens_used", "duration_ms"
    )
    list_filter = ("level", "action", "section", "created_at")
    search_fields = ("message",)
    readonly_fields = ("id", "created_at", "level", "action", "section", "message", "details", "tokens_used", "duration_ms")
    date_hierarchy = "created_at"

    def level_badge(self, obj):
        colors = {
            "info": "#17a2b8",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545",
        }
        color = colors.get(obj.level, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;font-size:11px">{}</span>',
            color, obj.level.upper()
        )
    level_badge.short_description = "Niveau"

    def message_preview(self, obj):
        return obj.message[:80] + "..." if len(obj.message) > 80 else obj.message
    message_preview.short_description = "Message"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------------ #
# AgentStats                                                          #
# ------------------------------------------------------------------ #

@admin.register(AgentStats)
class AgentStatsAdmin(admin.ModelAdmin):
    list_display = (
        "date", "total_posts_published", "total_posts_generated",
        "total_posts_failed", "total_tokens_used",
        "total_likes", "total_comments", "total_reach"
    )
    readonly_fields = (
        "date", "total_posts_generated", "total_posts_published",
        "total_posts_failed", "total_tokens_used",
        "posts_by_section", "total_reach", "total_likes",
        "total_comments", "created_at", "updated_at"
    )
    date_hierarchy = "date"

    def has_add_permission(self, request):
        return False
