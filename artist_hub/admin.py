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
        "fee_cameroon",
        "fee_international",
        "is_active",
        "is_open_badge",
        "candidates_count",
    )
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
        "payment_display",
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
        "proof_preview",
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
                    "payment",
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
            {"fields": ("admin_notes", "proof_preview", "created_at", "updated_at")},
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

    def payment_display(self, obj):
        if obj.payment:
            status_color = "#10B981" if obj.payment.status == PaymentStatus.SUCCESS else "#F59E0B"
            return format_html(
                '<span style="color:{}; font-weight:bold;">{} ({} {})</span>',
                status_color,
                obj.payment.reference,
                obj.payment.amount,
                obj.payment.currency,
            )
        return format_html('<span style="color:#EF4444;">Aucun</span>')

    payment_display.short_description = _("Paiement")

    def proof_preview(self, obj):
        if obj.payment and obj.payment.proof_file:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height:160px; border:1px solid #ccc; border-radius:6px;"/></a>',
                reverse("artist_hub:casting:staff_payment_proof", kwargs={"candidate_number": obj.candidate_number}),
                reverse("artist_hub:casting:staff_payment_proof", kwargs={"candidate_number": obj.candidate_number}),
            )
        return _("Aucune preuve téléversée")

    proof_preview.short_description = _("Aperçu de la preuve de paiement")

    @admin.action(description=_("Valider le paiement et marquer les candidats comme INSCRITS"))
    def action_mark_inscrits(self, request, queryset):
        from artist_hub.casting.views_dashboard import validate_payment
        count = 0
        for candidate in queryset:
            try:
                with transaction.atomic():
                    candidate = Candidate.objects.select_for_update().get(pk=candidate.pk)
                    validate_payment(candidate, request.user)
                count += 1
            except ValueError:
                continue
        self.message_user(request, f"{count} paiement(s) confirmé(s).")

    @admin.action(description=_("Marquer comme PRÉSÉLECTIONNÉ(S)"))
    def action_preselectionner(self, request, queryset):
        updated = queryset.filter(payment__status=PaymentStatus.SUCCESS).update(status=CandidateStatus.PRESELECTIONNE)
        self.message_user(request, f"{updated} candidat(s) présélectionné(s).")

    @admin.action(description=_("Marquer comme RETENU(S)"))
    def action_retenir(self, request, queryset):
        updated = queryset.filter(payment__status=PaymentStatus.SUCCESS).update(status=CandidateStatus.RETENU)
        self.message_user(request, f"{updated} candidat(s) retenu(s) pour la Fashion Week.")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "amount",
        "currency",
        "status_badge",
        "provider",
        "method",
        "payer_name",
        "payer_phone",
        "has_proof",
        "created_at",
        "verified_at",
    )
    list_filter = ("status", "provider", "method", "currency", "created_at")
    search_fields = (
        "reference",
        "payer_name",
        "payer_phone",
        "payer_email",
        "external_reference",
    )
    readonly_fields = (
        "id",
        "reference",
        "created_at",
        "updated_at",
        "raw_payload",
        "proof_preview",
    )
    actions = ["action_mark_success"]

    def status_badge(self, obj):
        colors = {
            PaymentStatus.PENDING: "#F59E0B",
            PaymentStatus.SUCCESS: "#10B981",
            PaymentStatus.FAILED: "#EF4444",
            PaymentStatus.CANCELLED: "#6B7280",
            PaymentStatus.EXPIRED: "#9CA3AF",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 8px; border-radius:10px; font-weight:bold; font-size:11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = _("Statut")

    def has_proof(self, obj):
        return bool(obj.proof_file)

    has_proof.boolean = True
    has_proof.short_description = _("Preuve ?")

    def proof_preview(self, obj):
        if obj.proof_file:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height:160px; border-radius:6px;" /></a>',
                reverse("artist_hub:casting:staff_payment_proof_by_payment", kwargs={"payment_id": obj.pk}),
                reverse("artist_hub:casting:staff_payment_proof_by_payment", kwargs={"payment_id": obj.pk}),
            )
        return _("Aucune preuve")

    proof_preview.short_description = _("Preuve de paiement")

    @admin.action(description=_("Valider manuellement les paiements sélectionnés (SUCCÈS)"))
    def action_mark_success(self, request, queryset):
        from artist_hub.casting.views_dashboard import validate_payment
        count = 0
        for payment in queryset:
            candidate = getattr(payment, "candidate", None)
            if not candidate:
                continue
            try:
                with transaction.atomic():
                    candidate = Candidate.objects.select_for_update().get(pk=candidate.pk)
                    validate_payment(candidate, request.user)
                count += 1
            except ValueError:
                continue
        self.message_user(request, f"{count} paiement(s) confirmé(s).")
