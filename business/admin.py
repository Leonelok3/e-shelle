import urllib.parse

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    AICreditLedger,
    AppCommission,
    AppPromotionSlide,
    BoostCampaign,
    BusinessKeyAccount,
    BusinessKeyPaymentRequest,
    BusinessActivationCode,
    BusinessCatalogItem,
    BusinessCatalogItemImage,
    BusinessLeadEvent,
    BusinessProfile,
    BusinessReview,
    ClientAIKit,
    HomeAdSlide,
    PartnerCRMLead,
    PartnerLevel,
    PaymentRequest,
    PremiumSectorCampaign,
    PresentationSlide,
    ProviderPlan,
    UnmetSearchRequest,
    UnmetSearchResponse,
)


class BusinessCatalogItemInline(admin.TabularInline):
    model = BusinessCatalogItem
    extra = 1
    fields = ("title", "item_type", "price_label", "order", "is_active")


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    inlines = (BusinessCatalogItemInline,)
    list_display = (
        "name", "module", "public_slug", "plan", "subscription_status", "days_left",
        "boost_status", "ai_credits", "views_count", "whatsapp_clicks", "phone_clicks",
        "leads_count", "is_active", "is_verified", "whatsapp_contact",
    )
    list_filter = ("module", "plan", "is_active", "is_verified")
    search_fields = ("name", "slug", "public_slug", "city", "district", "phone", "whatsapp", "promo_headline")
    fieldsets = (
        (None, {
            "fields": (
                "owner", "module", "name", "slug", "public_slug", "city", "district",
                "phone", "whatsapp", "description", "logo", "is_active", "is_verified",
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

    @admin.display(description="Jours restants")
    def days_left(self, obj):
        if not obj.subscription_expires_at:
            return "-"
        delta = obj.subscription_expires_at - timezone.now()
        if delta.days < 0:
            return "Expire"
        label = "Essai" if obj.is_trial else "Abo"
        return f"{delta.days}j ({label})"

    @admin.display(description="WhatsApp")
    def whatsapp_contact(self, obj):
        number = (obj.whatsapp or obj.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if not number:
            return "-"
        if not number.startswith("237"):
            number = f"237{number}"
        text = f"Bonjour, ici E-Shelle au sujet de votre fiche {obj.name}."
        return format_html(
            '<a href="https://wa.me/{}?text={}" target="_blank">Contacter</a>',
            number, urllib.parse.quote(text),
        )

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


class BusinessCatalogItemImageInline(admin.TabularInline):
    model = BusinessCatalogItemImage
    extra = 1


@admin.register(BusinessCatalogItem)
class BusinessCatalogItemAdmin(admin.ModelAdmin):
    inlines = (BusinessCatalogItemImageInline,)
    list_display = (
        "title", "business", "item_type", "price_label",
        "views_count", "is_active", "order", "updated_at",
    )
    list_filter = ("item_type", "is_active", "business__module")
    search_fields = ("title", "description", "business__name", "price_label")
    list_editable = ("is_active", "order")
    autocomplete_fields = ("business",)


@admin.register(BusinessReview)
class BusinessReviewAdmin(admin.ModelAdmin):
    list_display = ("business", "author_name", "rating", "is_approved", "created_at")
    list_filter = ("rating", "is_approved", "business__module")
    search_fields = ("author_name", "comment", "business__name")
    list_editable = ("is_approved",)
    autocomplete_fields = ("business",)


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
        "media_type",
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
    list_filter = ("is_active", "media_type", "badge", "business__module", "business__plan")
    search_fields = ("title", "subtitle", "business__name", "city")
    list_editable = ("order", "is_active")
    autocomplete_fields = ("business",)
    readonly_fields = ("preview", "impressions_count", "clicks_count", "ctr_display", "created_at", "updated_at")
    fieldsets = (
        ("Contenu du slide", {
            "fields": ("business", "title", "subtitle", "media_type", "image", "video", "video_url", "badge", "city"),
            "description": "Ajoutez ici le montage publicitaire: flyer, plat de restaurant, ecole, produit vedette, offre speciale ou video.",
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
        if obj.media_type == HomeAdSlide.MediaType.VIDEO and obj.video:
            return format_html('<span style="font-weight:700;color:#16a34a">Video</span>')
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


@admin.register(BusinessActivationCode)
class BusinessActivationCodeAdmin(admin.ModelAdmin):
    """
    Cree un code apres avoir reçu le paiement d'un client par WhatsApp : choisis
    sa fiche (business), le plan paye, et le montant/moyen de paiement. Le code
    est genere automatiquement — transmets-le ensuite au client sur WhatsApp.
    """
    list_display = (
        "code", "business", "plan", "amount_paid_xaf", "payment_method",
        "is_used", "used_at", "expires_at", "whatsapp_send", "created_at",
    )
    list_filter = ("is_used", "payment_method", "plan")
    search_fields = ("code", "business__name")
    autocomplete_fields = ("business", "plan")
    readonly_fields = ("code", "is_used", "used_at", "used_by", "created_by", "created_at")
    fields = (
        "business", "plan", "amount_paid_xaf", "payment_method", "notes",
        "expires_at", "code", "is_used", "used_at", "used_by", "created_by", "created_at",
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Envoyer sur WhatsApp")
    def whatsapp_send(self, obj):
        number = (obj.business.whatsapp or obj.business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if not number:
            return "-"
        if not number.startswith("237"):
            number = f"237{number}"
        text = (
            f"Bonjour {obj.business.name}, votre paiement E-Shelle a bien ete recu. "
            f"Voici votre code d'activation du plan {obj.plan.name} : {obj.code}. "
            "Entrez-le dans votre tableau de bord E-Shelle (section \"Activer avec un code\") pour activer votre fiche."
        )
        return format_html('<a href="https://wa.me/{}?text={}" target="_blank">Envoyer</a>', number, urllib.parse.quote(text))


@admin.register(BusinessKeyAccount)
class BusinessKeyAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "activated_at", "expires_at", "created_at")
    list_filter = ("tier",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BusinessKeyPaymentRequest)
class BusinessKeyPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "amount_xaf", "momo_number", "status", "created_at", "confirmed_at")
    list_filter = ("tier", "status", "created_at")
    search_fields = ("user__username", "user__email", "momo_number", "note")
    readonly_fields = ("created_at", "confirmed_at")
    actions = ("confirm_business_key", "cancel_business_key")

    @admin.action(description="Confirmer et activer la Business Key")
    def confirm_business_key(self, request, queryset):
        count = 0
        for payment_request in queryset.select_related("user"):
            if payment_request.status != BusinessKeyPaymentRequest.Status.CONFIRMED:
                payment_request.confirm()
                count += 1
        self.message_user(request, f"{count} Business Key activee(s).")

    @admin.action(description="Annuler les demandes Business Key")
    def cancel_business_key(self, request, queryset):
        count = queryset.exclude(status=BusinessKeyPaymentRequest.Status.CONFIRMED).update(status=BusinessKeyPaymentRequest.Status.CANCELED)
        self.message_user(request, f"{count} demande(s) annulee(s).")


@admin.register(PartnerCRMLead)
class PartnerCRMLeadAdmin(admin.ModelAdmin):
    list_display = ("business_name", "partner", "sector", "status", "city", "preferred_phone", "potential_xaf", "next_follow_up_at", "updated_at")
    list_filter = ("status", "sector", "city", "created_at")
    search_fields = ("business_name", "contact_name", "phone", "whatsapp", "partner__username", "city", "district")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ClientAIKit)
class ClientAIKitAdmin(admin.ModelAdmin):
    list_display = ("business", "status", "generated_at", "updated_at", "created_by")
    list_filter = ("status", "business__module", "business__plan", "generated_at")
    search_fields = ("business__name", "business__city", "chatbot_prompt", "notes")
    autocomplete_fields = ("business", "created_by")
    readonly_fields = ("generated_at", "created_at", "updated_at")
    fieldsets = (
        ("Client", {"fields": ("business", "status", "created_by", "notes")}),
        ("Brief et agents", {"fields": ("client_brief", "recommended_agents")}),
        ("Livrables", {
            "fields": (
                "chatbot_prompt",
                "website_plan",
                "content_pack",
                "whatsapp_scripts",
                "seo_plan",
                "video_plan",
                "automation_plan",
                "qa_checklist",
            )
        }),
        ("Dates", {"fields": ("generated_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(AppCommission)
class AppCommissionAdmin(admin.ModelAdmin):
    list_display = ("label", "app_name", "commission_rate", "commission_fixe", "is_recurring", "is_active", "priority")
    list_editable = ("commission_rate", "commission_fixe", "is_active", "priority")
    search_fields = ("label", "app_name", "description", "script_vente")
    list_filter = ("is_active", "is_recurring")
    ordering = ("priority", "app_name")


@admin.register(PartnerLevel)
class PartnerLevelAdmin(admin.ModelAdmin):
    list_display = ("label", "level", "prix_fcfa", "is_active")
    list_filter = ("is_active", "level")
    search_fields = ("label", "description", "bonus_description")
    filter_horizontal = ("apps_accessibles",)


class UnmetSearchResponseInline(admin.TabularInline):
    model = UnmetSearchResponse
    extra = 0
    fields = ("business", "responded_by", "status", "note", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("business", "responded_by")


@admin.register(UnmetSearchRequest)
class UnmetSearchRequestAdmin(admin.ModelAdmin):
    inlines = (UnmetSearchResponseInline,)
    list_display = ("query", "module", "city", "district", "preferred_contact", "status", "ai_priority", "lead_score", "assigned_partner", "notified_count", "created_at")
    list_filter = ("status", "module", "ai_priority", "assigned_partner", "city", "consent_share_contact", "consent_promotions", "created_at")
    search_fields = ("query", "customer_name", "whatsapp", "email", "city", "district", "notes", "assigned_partner__username")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("assigned_partner",)


@admin.register(UnmetSearchResponse)
class UnmetSearchResponseAdmin(admin.ModelAdmin):
    list_display = ("request", "business", "responded_by", "status", "created_at")
    list_filter = ("status", "created_at", "business__module")
    search_fields = ("request__query", "business__name", "responded_by__username", "note")
    autocomplete_fields = ("request", "business", "responded_by")


@admin.register(PresentationSlide)
class PresentationSlideAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "badge", "mockup_type", "order", "is_active", "created_at")
    list_filter = ("is_active", "mockup_type", "badge")
    search_fields = ("title", "subtitle", "badge", "tech_stack")
    list_editable = ("order", "is_active")
    readonly_fields = ("preview", "created_at", "updated_at")

    @admin.display(description="Aperçu")
    def preview(self, obj):
        if not obj.image:
            return "-"
        try:
            return format_html('<img src="{}" style="width:74px;height:48px;object-fit:cover;border-radius:8px" />', obj.image.url)
        except Exception:
            return "-"


@admin.register(AppPromotionSlide)
class AppPromotionSlideAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "cta_label", "cta_url", "order", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "cta_label", "cta_url")
    list_editable = ("order", "is_active")
    readonly_fields = ("preview", "created_at")

    @admin.display(description="Aperçu")
    def preview(self, obj):
        if not obj.image:
            return "-"
        try:
            return format_html('<img src="{}" style="width:100px;height:33px;object-fit:cover;border-radius:4px" />', obj.image.url)
        except Exception:
            return "-"

