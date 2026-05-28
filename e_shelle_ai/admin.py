"""
e_shelle_ai/admin.py
Administration complète de l'agent IA E-Shelle.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils.safestring import mark_safe
from .models import AIConversation, AIMessage, AIUserMemory, AIQuota, AILog, CentralAgentQueryLog


# ─── Inline Messages ──────────────────────────────────────────────────────────

class AIMessageInline(admin.TabularInline):
    model   = AIMessage
    fields  = ("role", "content_short", "message_type", "tokens_used", "created_at")
    readonly_fields = ("content_short", "role", "message_type", "tokens_used", "created_at")
    extra   = 0
    max_num = 20
    can_delete = False

    def content_short(self, obj):
        return obj.content[:120] + "…" if len(obj.content) > 120 else obj.content
    content_short.short_description = "Contenu"


# ─── Conversations ────────────────────────────────────────────────────────────

@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = (
        "user_link", "title_short", "module_badge", "message_count_display",
        "is_active", "created_at", "updated_at"
    )
    list_filter       = ("module_context", "is_active", "created_at")
    search_fields     = ("user__username", "user__email", "title")
    raw_id_fields     = ("user",)
    readonly_fields   = ("created_at", "updated_at")
    inlines           = [AIMessageInline]
    list_per_page     = 30
    date_hierarchy    = "created_at"

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/auth/user/{}/change/" style="color:#6366F1;font-weight:bold">{}</a>',
            obj.user.pk, obj.user.username
        )
    user_link.short_description = "Utilisateur"

    def title_short(self, obj):
        t = obj.title or "Sans titre"
        return t[:60] + "…" if len(t) > 60 else t
    title_short.short_description = "Titre"

    def module_badge(self, obj):
        colors = {
            "global": "#6366F1", "resto": "#F97316", "boutique": "#10B981",
            "marketing": "#EC4899", "pressing": "#818CF8", "gaz": "#FF6B00",
            "pharma": "#10B981",
        }
        color = colors.get(obj.module_context, "#6B7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>',
            color, obj.get_module_context_display()
        )
    module_badge.short_description = "Module"

    def message_count_display(self, obj):
        return obj.message_count
    message_count_display.short_description = "Messages"


# ─── Messages ─────────────────────────────────────────────────────────────────

@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display  = ("conversation", "role_badge", "content_short", "tokens_used", "created_at")
    list_filter   = ("role", "message_type", "created_at")
    search_fields = ("content", "conversation__user__username")
    readonly_fields = ("created_at",)
    list_per_page = 50

    def role_badge(self, obj):
        colors = {"user": "#3B82F6", "assistant": "#10B981", "system": "#6B7280"}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>',
            colors.get(obj.role, "#6B7280"), obj.role
        )
    role_badge.short_description = "Rôle"

    def content_short(self, obj):
        return obj.content[:100] + "…" if len(obj.content) > 100 else obj.content
    content_short.short_description = "Contenu"


# ─── Mémoire utilisateur ──────────────────────────────────────────────────────

@admin.register(AIUserMemory)
class AIUserMemoryAdmin(admin.ModelAdmin):
    list_display  = ("user", "summary_short", "preferences_display", "last_updated")
    search_fields = ("user__username", "summary")
    readonly_fields = ("last_updated",)
    list_per_page = 30

    def summary_short(self, obj):
        if not obj.summary:
            return "—"
        return obj.summary[:80] + "…" if len(obj.summary) > 80 else obj.summary
    summary_short.short_description = "Résumé"

    def preferences_display(self, obj):
        if not obj.preferences:
            return "—"
        return ", ".join(f"{k}={v}" for k, v in list(obj.preferences.items())[:3])
    preferences_display.short_description = "Préférences"


# ─── Quotas ───────────────────────────────────────────────────────────────────

@admin.register(AIQuota)
class AIQuotaAdmin(admin.ModelAdmin):
    list_display  = (
        "user", "plan_badge", "messages_progress",
        "images_progress", "reset_date"
    )
    list_filter   = ("plan",)
    search_fields = ("user__username",)
    readonly_fields = ("reset_date",)
    list_per_page = 50
    actions       = ["reset_quotas", "upgrade_to_pro", "upgrade_to_enterprise"]

    def plan_badge(self, obj):
        colors = {"starter": "#6B7280", "pro": "#6366F1", "enterprise": "#F59E0B"}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>',
            colors.get(obj.plan, "#6B7280"), obj.get_plan_display()
        )
    plan_badge.short_description = "Plan"

    def messages_progress(self, obj):
        pct = int((obj.messages_used / max(obj.messages_limit, 1)) * 100)
        color = "#10B981" if pct < 70 else "#F59E0B" if pct < 90 else "#EF4444"
        return format_html(
            '<div style="background:#1a1a2e;border-radius:4px;height:8px;width:100px">'
            '<div style="background:{};width:{}%;height:100%;border-radius:4px"></div></div>'
            '<small style="color:#9CA3AF">{}/{}</small>',
            color, min(pct, 100), obj.messages_used, obj.messages_limit
        )
    messages_progress.short_description = "Messages utilisés"

    def images_progress(self, obj):
        return f"{obj.images_used}/{obj.images_limit}"
    images_progress.short_description = "Images"

    @admin.action(description="♻️ Reset quotas sélectionnés")
    def reset_quotas(self, request, queryset):
        queryset.update(messages_used=0, images_used=0)
        self.message_user(request, f"{queryset.count()} quota(s) remis à zéro.")

    @admin.action(description="⬆️ Passer au plan Pro")
    def upgrade_to_pro(self, request, queryset):
        queryset.update(plan="pro", messages_limit=500, images_limit=50)
        self.message_user(request, f"{queryset.count()} utilisateur(s) passé(s) en Pro.")

    @admin.action(description="🚀 Passer au plan Enterprise")
    def upgrade_to_enterprise(self, request, queryset):
        queryset.update(plan="enterprise", messages_limit=99999, images_limit=9999)
        self.message_user(request, f"{queryset.count()} utilisateur(s) passé(s) en Enterprise.")


# ─── Analytics Agent Central ─────────────────────────────────────────────────

@admin.register(CentralAgentQueryLog)
class CentralAgentQueryLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "module",
        "query_short",
        "results_count",
        "premium_results_count",
        "had_results",
        "user",
    )
    list_filter = ("module", "had_results", "created_at")
    search_fields = ("query", "response", "user__username", "session_key")
    readonly_fields = (
        "user",
        "session_key",
        "query",
        "module",
        "response",
        "results_count",
        "premium_results_count",
        "had_results",
        "created_at",
    )
    date_hierarchy = "created_at"

    def query_short(self, obj):
        return obj.query[:90]
    query_short.short_description = "Recherche"


# ─── Logs API ─────────────────────────────────────────────────────────────────

@admin.register(AILog)
class AILogAdmin(admin.ModelAdmin):
    list_display  = (
        "user", "type_badge", "model_used", "total_tokens",
        "cout_display", "success_badge", "created_at"
    )
    list_filter   = ("type_appel", "model_used", "success", "created_at")
    search_fields = ("user__username",)
    readonly_fields = ("created_at",)
    list_per_page = 50
    date_hierarchy = "created_at"

    def type_badge(self, obj):
        colors = {"chat": "#6366F1", "image": "#EC4899"}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>',
            colors.get(obj.type_appel, "#6B7280"), obj.type_appel
        )
    type_badge.short_description = "Type"

    def cout_display(self, obj):
        return f"${float(obj.cout_estime_usd):.4f}"
    cout_display.short_description = "Coût USD"

    def success_badge(self, obj):
        if obj.success:
            return format_html('<span style="color:#10B981;font-weight:bold">✓ OK</span>')
        return format_html('<span style="color:#EF4444;font-weight:bold">✗ Erreur</span>')
    success_badge.short_description = "Statut"

    def changelist_view(self, request, extra_context=None):
        """Ajoute des statistiques globales en haut de la liste."""
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = self.get_queryset(request)
            stats = qs.aggregate(
                total_tokens=Sum("total_tokens"),
                total_cout=Sum("cout_estime_usd"),
                nb_appels=Count("id"),
            )
            if extra_context is None:
                extra_context = {}
            extra_context["ai_stats"] = {
                "total_tokens": stats["total_tokens"] or 0,
                "total_cout":   f"${float(stats['total_cout'] or 0):.2f}",
                "nb_appels":    stats["nb_appels"] or 0,
            }
            response.context_data.update(extra_context)
        except Exception:
            pass
        return response
