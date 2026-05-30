from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    CustomUser, UserProfile, StudentProfile,
    AppPlan, AppSubscription, PaymentHistory, GlobalAccessCode,
)


# ─── Utilisateurs ────────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ("username", "email", "role", "whatsapp", "ville", "is_staff", "is_active", "date_joined")
    list_filter   = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "whatsapp", "ville")
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle E-Shelle", {"fields": ("role",)}),
        ("Contact WhatsApp", {"fields": ("whatsapp", "ville")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "level", "plan", "pays", "created_at")
    search_fields = ("user__username", "user__email")
    list_filter   = ("plan", "level")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "class_level")
    search_fields = ("user__username",)


# ─── Plans d'application ─────────────────────────────────────────

@admin.register(AppPlan)
class AppPlanAdmin(admin.ModelAdmin):
    list_display  = ("name", "app_key", "level", "price_xaf_badge", "duration_days", "is_free", "is_popular", "is_active", "order")
    list_filter   = ("app_key", "level", "is_free", "is_popular", "is_active")
    search_fields = ("name", "slug")
    list_editable = ("order", "is_active", "is_popular")
    list_display_links = ("name",)
    prepopulated_fields = {"slug": ("app_key", "name")}
    ordering = ("app_key", "order")

    fieldsets = (
        ("Identité", {
            "fields": ("app_key", "slug", "name", "level", "description")
        }),
        ("Tarification", {
            "fields": ("price_xaf", "price_eur", "duration_days", "is_free")
        }),
        ("Fonctionnalités", {
            "fields": ("features",)
        }),
        ("Affichage", {
            "fields": ("is_popular", "is_active", "order")
        }),
    )

    @admin.display(description="Prix")
    def price_xaf_badge(self, obj):
        if obj.price_xaf == 0:
            return format_html('<span style="color:#10b981;font-weight:bold">Gratuit</span>')
        return format_html('<strong>{} FCFA</strong>', f"{obj.price_xaf:,}".replace(",", " "))


# ─── Abonnements ─────────────────────────────────────────────────

@admin.register(AppSubscription)
class AppSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ("user", "plan", "status_badge", "started_at", "expires_at", "days_remaining_display", "auto_renew")
    list_filter   = ("status", "plan__app_key", "plan__level", "auto_renew")
    search_fields = ("user__username", "user__email", "plan__name", "payment_ref")
    raw_id_fields = ("user",)
    list_display_links = ("user",)
    date_hierarchy = "started_at"
    ordering = ("-started_at",)

    fieldsets = (
        ("Utilisateur & Plan", {
            "fields": ("user", "plan", "status")
        }),
        ("Dates", {
            "fields": ("started_at", "expires_at", "auto_renew")
        }),
        ("Paiement", {
            "fields": ("payment_ref", "notes")
        }),
    )
    readonly_fields = ("started_at",)

    @admin.display(description="Statut")
    def status_badge(self, obj):
        colors = {
            "active":    "#10b981",
            "trial":     "#3b82f6",
            "expired":   "#ef4444",
            "cancelled": "#6b7280",
            "pending":   "#f59e0b",
        }
        color = colors.get(obj.status, "#6b7280")
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:.78rem;font-weight:600">{}</span>',
            color, label
        )

    @admin.display(description="Jours restants")
    def days_remaining_display(self, obj):
        r = obj.days_remaining
        if r is None:
            return "∞ Illimité"
        if r == 0:
            return format_html('<span style="color:#ef4444">Expiré</span>')
        if r <= 7:
            return format_html('<span style="color:#f59e0b">{} j</span>', r)
        return f"{r} j"


# ─── Historique paiements ────────────────────────────────────────

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display  = ("user", "amount_badge", "method", "status_badge", "description_short", "created_at")
    list_filter   = ("status", "method")
    search_fields = ("user__username", "user__email", "reference", "description")
    raw_id_fields = ("user",)
    list_display_links = ("user",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    @admin.display(description="Montant")
    def amount_badge(self, obj):
        if obj.amount_xaf == 0:
            return format_html('<span style="color:#10b981">Gratuit</span>')
        return format_html('<strong>{}</strong>', obj.amount_formatted)

    @admin.display(description="Statut")
    def status_badge(self, obj):
        colors = {"pending": "#f59e0b", "success": "#10b981", "failed": "#ef4444", "refunded": "#8b5cf6"}
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:.78rem;font-weight:600">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="Description")
    def description_short(self, obj):
        return obj.description[:60] + "…" if len(obj.description) > 60 else obj.description


# ─── Codes d'accès globaux ───────────────────────────────────────

@admin.register(GlobalAccessCode)
class GlobalAccessCodeAdmin(admin.ModelAdmin):
    list_display  = (
        "code_badge", "label", "apps_display_short", "duration_days",
        "price_badge", "payment_method", "client_name",
        "status_badge", "created_at",
    )
    list_filter   = ("is_used", "is_active", "payment_method", "duration_days")
    search_fields = ("code", "label", "client_name", "client_phone", "payment_ref")
    list_display_links = ("code_badge",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("code", "is_used", "activated_by", "activated_at", "expires_at", "created_at")

    fieldsets = (
        ("CODE GÉNÉRÉ AUTOMATIQUEMENT", {
            "fields": ("code", "label"),
            "description": "Le code est généré automatiquement. Envoyez-le au client par WhatsApp."
        }),
        ("CE QUE LE CODE DÉBLOQUE", {
            "fields": ("apps", "duration_days"),
            "description": (
                'Exemples d\'apps : ["adgen", "njangi"] ou ["all"] pour toutes les apps. '
                'App keys : adgen, resto, rencontres, njangi, edu, formations, boutique, agro'
            )
        }),
        ("PAIEMENT REÇU", {
            "fields": ("price_xaf", "payment_method", "payment_ref", "client_name", "client_phone")
        }),
        ("NOTES INTERNES", {
            "fields": ("notes", "is_active")
        }),
        ("UTILISATION (lecture seule)", {
            "fields": ("is_used", "activated_by", "activated_at", "expires_at", "created_at"),
            "classes": ("collapse",)
        }),
    )

    # ── Actions rapides ──────────────────────────────────────────
    actions = ["desactiver_codes", "reactiver_codes"]

    @admin.action(description="Désactiver les codes sélectionnés")
    def desactiver_codes(self, request, queryset):
        updated = queryset.filter(is_used=False).update(is_active=False)
        self.message_user(request, f"{updated} code(s) désactivé(s).")

    @admin.action(description="Réactiver les codes sélectionnés")
    def reactiver_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} code(s) réactivé(s).")

    # ── Badges affichage ─────────────────────────────────────────
    @admin.display(description="Code")
    def code_badge(self, obj):
        color = "#6b7280" if obj.is_used else "#1B6534"
        return format_html(
            '<code style="background:#f0fdf4;color:{};font-size:.85rem;'
            'padding:3px 8px;border-radius:6px;font-weight:700">{}</code>',
            color, obj.code
        )

    @admin.display(description="Statut")
    def status_badge(self, obj):
        if not obj.is_active:
            return format_html('<span style="background:#f3f4f6;color:#6b7280;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:700">Désactivé</span>')
        if obj.is_used:
            return format_html('<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:700">Utilisé ✓</span>')
        return format_html('<span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:700">Disponible</span>')

    @admin.display(description="Prix")
    def price_badge(self, obj):
        if obj.price_xaf == 0:
            return format_html('<span style="color:#10b981;font-weight:600">Offert</span>')
        return format_html('<strong style="color:#1B6534">{}</strong>', obj.price_formatted)

    @admin.display(description="Applications")
    def apps_display_short(self, obj):
        if "all" in obj.apps:
            return format_html('<span style="color:#7c3aed;font-weight:600">Toutes les apps</span>')
        return ", ".join(obj.apps[:3]) + ("…" if len(obj.apps) > 3 else "")
