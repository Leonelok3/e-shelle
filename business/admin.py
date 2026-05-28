from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AICreditLedger,
    BoostCampaign,
    BusinessLeadEvent,
    BusinessProfile,
    HomeAdSlide,
    PaymentRequest,
    PremiumSectorCampaign,
    ProviderPlan,
)


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name", "module", "plan", "subscription_status", "boost_status",
        "ai_credits", "views_count", "whatsapp_clicks", "phone_clicks", "leads_count",
        "is_active", "is_verified",
    )
    list_filter = ("module", "plan", "is_active", "is_verified")
    search_fields = ("name", "city", "district", "phone", "whatsapp", "promo_headline")
    fieldsets = (
        (None, {
            "fields": (
                "owner", "module", "name", "slug", "city", "district",
                "phone", "whatsapp", "description", "is_active", "is_verified",
            )
        }),
        ("Publicite page d'accueil", {
            "fields": ("promo_headline", "promo_offer", "promo_image", "promo_url"),
            "description": "Ces champs alimentent le hero et les blocs Premium/Business de la page d'accueil.",
        }),
        ("Abonnement et performance", {
            "fields": (
                "plan", "subscription_expires_at", "boost_expires_at", "ai_credits",
                "views_count", "whatsapp_clicks", "phone_clicks", "detail_clicks",
                "leads_count", "economic_score",
            )
        }),
        ("Lien technique", {
            "fields": ("content_type", "object_id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = (
        "views_count", "whatsapp_clicks", "phone_clicks", "detail_clicks",
        "leads_count", "economic_score", "created_at", "updated_at",
    )
    actions = ("activate_pro_30_days", "activate_business_30_days", "activate_premium_30_days", "boost_7_days")

    @admin.display(description="Abonnement")
    def subscription_status(self, obj):
        return "Actif" if obj.subscription_active else "Expire/Gratuit"

    @admin.display(description="Boost")
    def boost_status(self, obj):
        return "Actif" if obj.boost_active else "-"

    @admin.action(description="Activer Pro 30 jours")
    def activate_pro_30_days(self, request, queryset):
        for profile in queryset:
            profile.activate_plan(BusinessProfile.Plan.PRO, 30)

    @admin.action(description="Activer Business 30 jours")
    def activate_business_30_days(self, request, queryset):
        for profile in queryset:
            profile.activate_plan(BusinessProfile.Plan.BUSINESS, 30)

    @admin.action(description="Activer Premium 30 jours")
    def activate_premium_30_days(self, request, queryset):
        for profile in queryset:
            profile.activate_plan(BusinessProfile.Plan.PREMIUM, 30)

    @admin.action(description="Booster 7 jours")
    def boost_7_days(self, request, queryset):
        for profile in queryset:
            profile.activate_boost(7)


@admin.register(ProviderPlan)
class ProviderPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "plan_level", "monthly_price_xaf", "duration_days", "included_boost_days", "included_ai_credits", "is_active")
    list_filter = ("plan_level", "is_active")
    search_fields = ("name", "code")
    list_editable = ("is_active",)


@admin.register(HomeAdSlide)
class HomeAdSlideAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "title",
        "business",
        "badge",
        "city",
        "order",
        "is_active",
        "impressions_count",
        "clicks_count",
        "ctr_display",
        "starts_at",
        "ends_at",
        "updated_at",
    )
    list_filter = ("is_active", "badge", "business__module", "business__plan")
    search_fields = ("title", "subtitle", "business__name", "city")
    list_editable = ("order", "is_active")
    autocomplete_fields = ("business",)
    readonly_fields = ("preview", "impressions_count", "clicks_count", "ctr_display", "created_at", "updated_at")
    fieldsets = (
        ("Contenu du slide", {
            "fields": ("business", "title", "subtitle", "image", "badge", "city"),
            "description": "Ajoutez ici le montage publicitaire: plat de restaurant, pressing, produit vedette, offre speciale.",
        }),
        ("Action client", {
            "fields": ("cta_label", "cta_url"),
            "description": "Si le lien est vide, le bouton utilisera WhatsApp du business ou E-Shelle IA.",
        }),
        ("Publication", {
            "fields": ("is_active", "order", "starts_at", "ends_at", "impressions_count", "clicks_count", "ctr_display", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Aperçu")
    def preview(self, obj):
        if not obj.image:
            return "-"
        return format_html('<img src="{}" style="width:74px;height:48px;object-fit:cover;border-radius:8px" />', obj.image.url)

    @admin.display(description="CTR")
    def ctr_display(self, obj):
        if not obj.impressions_count:
            return "0%"
        return f"{(obj.clicks_count / obj.impressions_count) * 100:.1f}%"


@admin.register(BoostCampaign)
class BoostCampaignAdmin(admin.ModelAdmin):
    list_display = ("business", "starts_at", "ends_at", "amount_xaf", "source", "is_paid")
    list_filter = ("is_paid", "source")
    search_fields = ("business__name",)


@admin.register(PremiumSectorCampaign)
class PremiumSectorCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "city", "status", "target_businesses", "budget_xaf", "starts_at", "ends_at", "is_live")
    list_filter = ("status", "module", "city")
    search_fields = ("name", "goal", "pitch", "city")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at", "is_live")
    fieldsets = (
        ("Campagne", {"fields": ("name", "module", "city", "status", "goal", "pitch")}),
        ("Objectifs", {"fields": ("target_businesses", "budget_xaf")}),
        ("Calendrier", {"fields": ("starts_at", "ends_at", "is_live", "created_at", "updated_at")}),
    )


@admin.register(AICreditLedger)
class AICreditLedgerAdmin(admin.ModelAdmin):
    list_display = ("business", "movement", "quantity", "reason", "created_at")
    list_filter = ("movement",)
    search_fields = ("business__name", "reason")


@admin.register(BusinessLeadEvent)
class BusinessLeadEventAdmin(admin.ModelAdmin):
    list_display = ("business", "event_type", "source", "created_at", "target_url")
    list_filter = ("event_type", "source", "created_at")
    search_fields = ("business__name", "target_url")
    readonly_fields = ("public_id", "created_at")


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "requested_by", "method", "amount_xaf", "status", "phone", "whatsapp_contact", "created_at", "confirmed_at")
    list_filter = ("status", "method", "plan")
    search_fields = ("business__name", "requested_by__username", "phone")
    readonly_fields = ("created_at", "confirmed_at")
    actions = ("confirm_requests", "cancel_requests")

    @admin.display(description="WhatsApp")
    def whatsapp_contact(self, obj):
        number = (obj.phone or obj.business.whatsapp or obj.business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if not number:
            return "-"
        if not number.startswith("237"):
            number = f"237{number}"
        text = (
            f"Bonjour, votre demande E-Shelle #{obj.pk} pour {obj.business.name} "
            f"({obj.plan.name}, {obj.amount_xaf} FCFA) a ete recue."
        )
        import urllib.parse
        return format_html('<a href="https://wa.me/{}?text={}" target="_blank">Contacter</a>', number, urllib.parse.quote(text))

    @admin.action(description="Confirmer et activer les abonnements")
    def confirm_requests(self, request, queryset):
        count = 0
        for payment_request in queryset.select_related("business", "plan", "requested_by"):
            if payment_request.status != PaymentRequest.Status.CONFIRMED:
                payment_request.confirm()
                count += 1
        self.message_user(request, f"{count} demande(s) confirmee(s).")

    @admin.action(description="Annuler les demandes")
    def cancel_requests(self, request, queryset):
        count = queryset.exclude(status=PaymentRequest.Status.CONFIRMED).update(status=PaymentRequest.Status.CANCELED)
        self.message_user(request, f"{count} demande(s) annulee(s).")

# Register your models here.
