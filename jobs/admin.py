from django.contrib import admin
from django.utils.html import format_html

from .models import CandidatureJob, OffreJob, SecteurJob, VilleJob, CanadaJobOffer, CanadaScholarship


@admin.register(SecteurJob)
class SecteurJobAdmin(admin.ModelAdmin):
    list_display = ("nom", "active", "ordre")
    list_editable = ("active", "ordre")
    prepopulated_fields = {"slug": ("nom",)}
    search_fields = ("nom",)


@admin.register(VilleJob)
class VilleJobAdmin(admin.ModelAdmin):
    list_display = ("nom", "region", "active", "ordre")
    list_editable = ("active", "ordre")
    prepopulated_fields = {"slug": ("nom",)}
    search_fields = ("nom", "region")


class CandidatureInline(admin.TabularInline):
    model = CandidatureJob
    extra = 0
    readonly_fields = ("nom", "telephone", "email", "ville", "message", "cv", "created_at")
    can_delete = False


@admin.register(OffreJob)
class OffreJobAdmin(admin.ModelAdmin):
    list_display = ("titre", "entreprise", "ville", "type_contrat", "statut", "is_featured", "created_at")
    list_filter = ("is_active", "is_verified", "is_featured", "type_contrat", "mode_travail", "ville", "secteur")
    list_editable = ("is_featured",)
    search_fields = ("titre", "entreprise", "description", "telephone", "email")
    prepopulated_fields = {"slug": ("titre", "entreprise")}
    date_hierarchy = "created_at"
    inlines = [CandidatureInline]
    actions = ["publier", "masquer"]

    @admin.display(description="Statut")
    def statut(self, obj):
        if obj.is_active and obj.is_verified:
            return format_html('<span style="background:#dcfce7;color:#166534;padding:3px 8px;border-radius:999px;font-weight:700">Verifiee</span>')
        if obj.is_active:
            return format_html('<span style="background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:999px;font-weight:700">Publiee</span>')
        return format_html('<span style="background:#f3f4f6;color:#6b7280;padding:3px 8px;border-radius:999px;font-weight:700">Brouillon</span>')

    @admin.action(description="Publier et verifier")
    def publier(self, request, queryset):
        updated = queryset.update(is_active=True, is_verified=True)
        self.message_user(request, f"{updated} offre(s) publiee(s).")

    @admin.action(description="Masquer")
    def masquer(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} offre(s) masquee(s).")


@admin.register(CandidatureJob)
class CandidatureJobAdmin(admin.ModelAdmin):
    list_display = ("nom", "offre", "telephone", "email", "created_at")
    search_fields = ("nom", "telephone", "email", "offre__titre", "offre__entreprise")
    list_filter = ("offre__ville", "created_at")
    readonly_fields = ("created_at",)


@admin.register(CanadaJobOffer)
class CanadaJobOfferAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "city", "province", "lmia_status", "salary", "is_active", "fetched_at")
    list_filter = ("is_active", "province", "lmia_status")
    search_fields = ("title", "company", "city", "description")
    date_hierarchy = "fetched_at"


@admin.register(CanadaScholarship)
class CanadaScholarshipAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "amount", "deadline", "is_active", "fetched_at")
    list_filter = ("is_active", "provider")
    search_fields = ("title", "provider", "description", "eligibility")
    date_hierarchy = "fetched_at"
