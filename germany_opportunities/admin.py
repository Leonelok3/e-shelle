from django.contrib import admin
from .models import AusbildungOffer, ScholarshipOpportunity, UserOpportunityBookmark


@admin.register(AusbildungOffer)
class AusbildungOfferAdmin(admin.ModelAdmin):
    list_display  = ("title", "company", "city", "sector", "language_req",
                     "start_date", "is_active", "is_new_badge", "fetched_at")
    list_filter   = ("sector", "language_req", "is_active", "region")
    search_fields = ("title", "company", "city", "ref_nr")
    ordering      = ("-fetched_at",)
    readonly_fields = ("ref_nr", "fetched_at", "last_seen")
    fieldsets = (
        ("Offre", {"fields": ("ref_nr", "title", "company", "city", "postal_code",
                               "region", "sector", "start_date", "salary_month",
                               "language_req", "duration_months", "url_apply")}),
        ("Contenu", {"fields": ("description",)}),
        ("IA", {"fields": ("ai_summary_fr", "ai_tips_fr")}),
        ("Meta", {"fields": ("is_active", "fetched_at", "last_seen")}),
    )
    actions = ["mark_inactive", "run_ai_enrichment"]

    def is_new_badge(self, obj):
        return "NEW" if obj.is_new else ""
    is_new_badge.short_description = "Statut"

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} offres desactivees.")
    mark_inactive.short_description = "Desactiver les offres selectionnees"

    def run_ai_enrichment(self, request, queryset):
        from .tasks import enrich_offers_with_ai
        enrich_offers_with_ai.delay()
        self.message_user(request, "Enrichissement IA lance en arriere-plan.")
    run_ai_enrichment.short_description = "Lancer enrichissement IA"


@admin.register(ScholarshipOpportunity)
class ScholarshipOpportunityAdmin(admin.ModelAdmin):
    list_display  = ("title", "provider", "level", "deadline", "is_active", "fetched_at")
    list_filter   = ("level", "provider", "is_active")
    search_fields = ("title", "provider", "countries")
    ordering      = ("deadline",)


@admin.register(UserOpportunityBookmark)
class UserOpportunityBookmarkAdmin(admin.ModelAdmin):
    list_display  = ("user", "offer", "scholarship", "applied", "saved_at")
    list_filter   = ("applied",)
    search_fields = ("user__username",)
