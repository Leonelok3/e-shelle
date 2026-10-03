from django.contrib import admin
from django.urls import reverse
from django.db import transaction
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from artist_hub.models import (
    CastingSession,
    Candidate,
    CandidatePhoto,
    Payment,
    PaymentStatus,
    CandidateStatus,
)


class CandidatePhotoInline(admin.TabularInline):
    model = CandidatePhoto
    extra = 0
    fields = ("photo_type", "order", "image_preview", "image")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 80px; border-radius: 4px;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = _("Aperçu")


@admin.register(CastingSession)
class CastingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_date",
        "event_location",
        "is_active",
        "is_open_badge",
        "candidates_count",
    )
    exclude = ("fee_cameroon", "fee_international", "currency")
    list_filter = ("is_active", "event_date")
    search_fields = ("title", "subtitle", "event_location")
    prepopulated_fields = {"slug": ("title",)}

    def is_open_badge(self, obj):
        if obj.is_open:
            return format_html(
                '<span style="background:#10B981; color:#fff; padding:3px 8px; border-radius:10px; font-size:11px;">OUVERT</span>'
            )
        return format_html(
            '<span style="background:#EF4444; color:#fff; padding:3px 8px; border-radius:10px; font-size:11px;">FERMÉ</span>'
        )

    is_open_badge.short_description = _("Inscriptions")

    def candidates_count(self, obj):
        return obj.candidates.count()

    candidates_count.short_description = _("Candidats")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "candidate_number",
        "access_code",
        "full_name",
        "gender",
        "age_display",
        "height_cm",
        "city",
        "country",
        "status_badge",
        "created_at",
    )
    list_filter = ("session", "status", "gender", "country", "is_minor", "created_at")
    search_fields = (
        "candidate_number",
        "access_code",
        "first_name",
        "last_name",
        "phone",
        "email",
        "city",
    )
    readonly_fields = (
        "candidate_number",
        "access_code",
        "is_minor",
        "created_at",
        "updated_at",
    )
    inlines = [CandidatePhotoInline]
    actions = ["action_mark_inscrits", "action_preselectionner", "action_retenir"]

    fieldsets = (
        (
            _("Session & Identifiants"),
            {
                "fields": (
                    "session",
                    "candidate_number",
                    "access_code",
                    "status",
                )
            },
        ),
        (
            _("Informations Personnelles"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "birth_date",
                    "gender",
                    "height_cm",
                    "weight_kg",
                    "measurements",
                    "city",
                    "country",
                    "is_international",
                )
            },
        ),
        (
            _("Contacts"),
            {"fields": ("phone", "email", "social_links")},
        ),
        (
            _("Expérience & Vidéo"),
            {"fields": ("experience", "video_url", "video_file")},
        ),
        (
            _("Mineurs & Tuteur"),
            {
                "fields": (
                    "is_minor",
                    "guardian_name",
                    "guardian_phone",
                    "parental_consent",
                )
            },
        ),
        (
            _("Consentements & Décharge"),
            {
                "fields": (
                    "gdpr_consent",
                    "selection_disclaimer_accepted",
                )
            },
        ),
        (
            _("Notes Staff"),
            {"fields": ("admin_notes", "created_at", "updated_at")},
        ),
    )

    def age_display(self, obj):
        return f"{obj.age} ans"

    age_display.short_description = _("Âge")

    def status_badge(self, obj):
        colors = {
            CandidateStatus.EN_ATTENTE_PAIEMENT: "#F59E0B",
            CandidateStatus.EN_ATTENTE_VALIDATION: "#3B82F6",
            CandidateStatus.INSCRIT: "#10B981",
            CandidateStatus.PRESELECTIONNE: "#8B5CF6",
            CandidateStatus.RETENU: "#059669",
            CandidateStatus.REFUSE: "#EF4444",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 8px; border-radius:10px; font-weight:bold; font-size:11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = _("Statut")

    @admin.action(description=_("Confirmer les inscriptions gratuites"))
    def action_mark_inscrits(self, request, queryset):
        from artist_hub.casting.services import finalize_candidate_registration
        count = 0
        for candidate in queryset:
            try:
                with transaction.atomic():
                    candidate = Candidate.objects.select_for_update().get(pk=candidate.pk)
                    finalize_candidate_registration(candidate)
                count += 1
            except ValueError:
                continue
        self.message_user(request, f"{count} inscription(s) confirmée(s).")

    @admin.action(description=_("Marquer comme PRÉSÉLECTIONNÉ(S)"))
    def action_preselectionner(self, request, queryset):
        updated = queryset.update(status=CandidateStatus.PRESELECTIONNE)
        self.message_user(request, f"{updated} candidat(s) présélectionné(s).")

    @admin.action(description=_("Marquer comme RETENU(S)"))
    def action_retenir(self, request, queryset):
        updated = queryset.update(status=CandidateStatus.RETENU)
        self.message_user(request, f"{updated} candidat(s) retenu(s) pour la Fashion Week.")
