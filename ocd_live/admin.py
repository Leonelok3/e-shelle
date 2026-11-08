from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Booking,
    LiveBooking,
    LivePackage,
    LiveSession,
    LiveSlot,
    OCDPackage,
    Opportunity,
    OpportunityCategory,
    Slot,
)


@admin.register(OpportunityCategory)
class OpportunityCategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "city", "country", "min_capital_display", "estimated_roi", "status", "is_featured", "created_at")
    list_filter = ("status", "category", "is_featured", "country")
    search_fields = ("title", "summary", "city", "full_description")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("status", "is_featured")

    def min_capital_display(self, obj):
        return f"{int(obj.min_capital_xaf):,} FCFA".replace(",", " ")
    min_capital_display.short_description = "Capital Min."


class SlotInline(admin.TabularInline):
    model = Slot
    extra = 1
    fields = ("title", "expert_name", "start_time", "end_time", "capacity", "booked_count", "price_xaf", "is_active")


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "speaker_name", "scheduled_at", "access_tier", "ticket_price_display", "is_live_now", "is_completed")
    list_filter = ("is_live_now", "is_completed", "access_tier", "stream_provider")
    search_fields = ("title", "subtitle", "speaker_name", "description")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_live_now", "is_completed")
    inlines = [SlotInline]

    def ticket_price_display(self, obj):
        return f"{int(obj.ticket_price_xaf):,} FCFA".replace(",", " ")
    ticket_price_display.short_description = "Prix Billet"


@admin.register(OCDPackage)
class OCDPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_display", "duration_days", "can_access_all_lives", "is_popular", "is_active", "order")
    list_filter = ("is_active", "is_popular")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_popular", "is_active", "order")

    def price_display(self, obj):
        return f"{int(obj.price_xaf):,} FCFA".replace(",", " ")
    price_display.short_description = "Prix"


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("title", "expert_name", "start_time", "end_time", "capacity", "booked_count", "price_xaf", "is_active")
    list_filter = ("is_active", "start_time")
    search_fields = ("title", "expert_name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("ticket_code", "user", "target_display", "amount_paid_display", "status_badge", "whatsapp_number", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("ticket_code", "user__username", "user__email", "whatsapp_number", "transaction_ref")
    readonly_fields = ("ticket_code", "created_at", "updated_at")

    def target_display(self, obj):
        if obj.session:
            return f"Session: {obj.session.title[:30]}"
        if obj.package:
            return f"Pass: {obj.package.name}"
        if obj.slot:
            return f"Créneau: {obj.slot.title[:30]}"
        return "Général"
    target_display.short_description = "Prestation"

    def amount_paid_display(self, obj):
        return f"{int(obj.amount_paid):,} FCFA".replace(",", " ")
    amount_paid_display.short_description = "Montant"

    def status_badge(self, obj):
        colors = {
            "CONFIRMED": "#10B981",
            "PENDING": "#F59E0B",
            "CANCELLED": "#EF4444",
        }
        return format_html(
            '<span style="background:{};color:#FFF;padding:3px 8px;border-radius:6px;font-weight:700;font-size:0.75rem">{}</span>',
            colors.get(obj.status, "#6B7280"),
            obj.get_status_display(),
        )
    status_badge.short_description = "Statut"


# ============================================================================
# ADMIN OFFICIEL DU SYSTÈME DE RÉSERVATION LIVE OCD
# ============================================================================

@admin.register(LivePackage)
class LivePackageAdmin(admin.ModelAdmin):
    list_display = ("nom", "duree_display", "prix_formate_col", "est_recommande", "actif", "ordre")
    list_filter = ("actif", "est_recommande")
    search_fields = ("nom", "description")
    prepopulated_fields = {"slug": ("nom",)}
    list_editable = ("actif", "est_recommande", "ordre")

    def prix_formate_col(self, obj):
        return obj.prix_formate
    prix_formate_col.short_description = "Prix (XAF)"


@admin.register(LiveSlot)
class LiveSlotAdmin(admin.ModelAdmin):
    list_display = ("date", "heure_debut", "heure_fin", "capacite", "disponibilite_badge", "est_bloque_admin")
    list_filter = ("est_disponible", "est_bloque_admin", "date")
    search_fields = ("date",)
    list_editable = ("est_bloque_admin",)
    actions = ["bloquer_creneaux", "debloquer_creneaux", "rendre_disponible"]

    def disponibilite_badge(self, obj):
        if obj.est_bloque_admin:
            return format_html('<span style="background:#EF4444;color:#FFF;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:700">Bloqué Admin</span>')
        if not obj.est_disponible:
            return format_html('<span style="background:#6B7280;color:#FFF;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:700">Indisponible (Réservé)</span>')
        return format_html('<span style="background:#10B981;color:#FFF;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:700">Disponible</span>')
    disponibilite_badge.short_description = "Disponibilité"

    @admin.action(description="Bloquer les créneaux sélectionnés")
    def bloquer_creneaux(self, request, queryset):
        queryset.update(est_bloque_admin=True)

    @admin.action(description="Débloquer les créneaux sélectionnés")
    def debloquer_creneaux(self, request, queryset):
        queryset.update(est_bloque_admin=False)

    @admin.action(description="Rendre disponible les créneaux sélectionnés")
    def rendre_disponible(self, request, queryset):
        queryset.update(est_disponible=True, est_bloque_admin=False)


@admin.register(LiveBooking)
class LiveBookingAdmin(admin.ModelAdmin):
    list_display = (
        "code_reservation",
        "nom_entreprise",
        "nom_complet",
        "date_choisie",
        "heure_choisie",
        "package_col",
        "prix_total_col",
        "statut_badge",
        "preuve_col",
        "date_creation",
    )
    list_filter = ("statut", "mode_paiement", "secteur_activite", "date_choisie", "package")
    search_fields = (
        "code_reservation",
        "nom_complet",
        "nom_entreprise",
        "telephone_whatsapp",
        "email",
        "titre_du_live",
        "reference_paiement",
    )
    readonly_fields = ("code_reservation", "date_creation", "date_mise_a_jour", "preuve_preview", "pdf_link")
    actions = ["valider_demandes", "refuser_demandes", "marquer_terminees"]

    fieldsets = (
        (
            "Identifiant & Statut",
            {
                "fields": ("code_reservation", "statut", "pdf_link", "message_admin"),
            },
        ),
        (
            "Informations Demandeur & Entreprise",
            {
                "fields": (
                    "nom_complet",
                    "nom_entreprise",
                    "secteur_activite",
                    "telephone_whatsapp",
                    "email",
                    "lien_site_ou_page",
                    "lien_whatsapp",
                ),
            },
        ),
        (
            "Contenu du Live (Pitch & Produits)",
            {
                "fields": ("titre_du_live", "description_activite", "produits_services"),
            },
        ),
        (
            "Créneau, Formule & Horaires",
            {
                "fields": ("package", "slot", "date_choisie", "heure_choisie", "duree_minutes", "prix_total"),
            },
        ),
        (
            "Paiement & Justificatif",
            {
                "fields": ("mode_paiement", "reference_paiement", "preuve_paiement", "preuve_preview"),
            },
        ),
        (
            "Traçabilité",
            {
                "fields": ("date_creation", "date_mise_a_jour"),
            },
        ),
    )

    def package_col(self, obj):
        return obj.package.nom if obj.package else "—"
    package_col.short_description = "Package"

    def prix_total_col(self, obj):
        return f"{int(obj.prix_total):,} XAF".replace(",", " ")
    prix_total_col.short_description = "Prix Total"

    def statut_badge(self, obj):
        color = obj.statut_badge_color
        return format_html(
            '<span style="background:{};color:#FFF;padding:4px 10px;border-radius:99px;font-weight:700;font-size:0.75rem">{}</span>',
            color,
            obj.get_statut_display(),
        )
    statut_badge.short_description = "Statut"

    def preuve_col(self, obj):
        if obj.preuve_paiement:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height:35px;width:35px;object-fit:cover;border-radius:4px;border:1px solid #CBD5E1"></a>',
                obj.preuve_paiement.url,
                obj.preuve_paiement.url,
            )
        if obj.reference_paiement:
            return format_html('<span style="color:#0284C7;font-weight:600;font-size:0.75rem">Réf: {}</span>', obj.reference_paiement)
        return format_html('<span style="color:#94A3B8;font-size:0.75rem">Aucune preuve</span>')
    preuve_col.short_description = "Preuve"

    def preuve_preview(self, obj):
        if obj.preuve_paiement:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-height:280px;border-radius:8px;border:1px solid #CBD5E1"></a><br><small>Cliquez pour agrandir</small>',
                obj.preuve_paiement.url,
                obj.preuve_paiement.url,
            )
        return "Aucun fichier téléversé."
    preuve_preview.short_description = "Aperçu de la preuve"

    def pdf_link(self, obj):
        url = reverse("ocd_live:fiche_pdf", kwargs={"code": obj.code_reservation})
        return format_html('<a href="{}" target="_blank" class="button" style="background:#16A34A;color:#FFF;padding:6px 12px;border-radius:4px;text-decoration:none;font-weight:700">📄 Télécharger Fiche PDF</a>', url)
    pdf_link.short_description = "Fiche PDF Officielle"

    @admin.action(description="✓ Valider les réservations sélectionnées (verrouille le créneau)")
    def valider_demandes(self, request, queryset):
        count = 0
        for b in queryset:
            b.statut = LiveBooking.Statut.VALIDEE_ADMIN
            if b.slot:
                b.slot.est_disponible = False
                b.slot.save(update_fields=["est_disponible"])
            b.save()
            count += 1
        self.message_user(request, f"{count} réservation(s) validée(s) avec succès.")

    @admin.action(description="✗ Refuser les réservations sélectionnées (libère le créneau)")
    def refuser_demandes(self, request, queryset):
        count = 0
        for b in queryset:
            b.statut = LiveBooking.Statut.REFUSEE
            if b.slot:
                b.slot.est_disponible = True
                b.slot.save(update_fields=["est_disponible"])
            b.save()
            count += 1
        self.message_user(request, f"{count} réservation(s) refusée(s).")

    @admin.action(description="Marquer comme Terminées")
    def marquer_terminees(self, request, queryset):
        queryset.update(statut=LiveBooking.Statut.TERMINEE)


