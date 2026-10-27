"""
admin.py — immobilier_cameroun
Interface d'administration Django professionnelle pour la marketplace immobilière
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import (
    ProfilImmo, Bien, PhotoBien, EquipementBien,
    DemandeVisite, FavorisBien, SignalementBien, DemandeSoumissionBien,
    StatutBien, TypeCompte,
)


# ─────────────────────────────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────────────────────────────

class PhotoBienInline(admin.TabularInline):
    model       = PhotoBien
    extra       = 3
    fields      = ["image", "legende", "est_photo_principale", "ordre", "apercu"]
    readonly_fields = ["apercu"]

    def apercu(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:6px;object-fit:cover;" />',
                obj.image.url
            )
        return "—"
    apercu.short_description = "Aperçu"


class EquipementBienInline(admin.TabularInline):
    model  = EquipementBien
    extra  = 3
    fields = ["nom"]


# ─────────────────────────────────────────────────────────────────
# BIEN ADMIN
# ─────────────────────────────────────────────────────────────────

@admin.register(Bien)
class BienAdmin(admin.ModelAdmin):
    # — Affichage liste —
    list_display = [
        "titre_avec_badge", "type_bien", "type_transaction",
        "ville", "quartier", "prix_formate_display", "statut_badge",
        "est_mis_en_avant", "est_coup_de_coeur",
        "proprietaire", "publie_par_admin", "vues", "created_at",
    ]
    list_filter = [
        "statut", "type_bien", "type_transaction", "ville",
        "est_mis_en_avant", "est_coup_de_coeur", "publie_par_admin", "devise",
    ]
    search_fields = [
        "titre", "quartier", "ville", "description",
        "proprietaire__email", "proprietaire__username",
    ]
    list_editable   = ["est_mis_en_avant", "est_coup_de_coeur"]
    readonly_fields = [
        "vues", "created_at", "updated_at", "date_publication",
        "apercu_photo_principale",
    ]
    prepopulated_fields = {"slug": ("titre",)}
    inlines             = [PhotoBienInline, EquipementBienInline]
    date_hierarchy      = "created_at"
    ordering            = ["-created_at"]

    fieldsets = (
        ("📋 Informations générales", {
            "fields": ("titre", "slug", "type_bien", "type_transaction", "description"),
        }),
        ("📍 Localisation", {
            "fields": ("ville", "quartier", "adresse_complete", "latitude", "longitude"),
        }),
        ("🏠 Détails du bien", {
            "fields": (
                "surface", "nombre_pieces", "nombre_chambres", "nombre_salles_bain",
                "etage", "nombre_etages_immeuble",
            ),
        }),
        ("💰 Tarification", {
            "fields": ("prix", "devise", "periode_prix", "date_disponibilite"),
        }),
        ("🚀 Publication & Mise en avant", {
            "fields": (
                "statut", "est_mis_en_avant", "est_coup_de_coeur",
                "publie_par_admin", "proprietaire", "note_admin",
            ),
        }),
        ("🔍 SEO", {
            "fields": ("meta_description", "meta_keywords"),
            "classes": ("collapse",),
        }),
        ("📊 Statistiques", {
            "fields": ("vues", "created_at", "updated_at", "date_publication"),
            "classes": ("collapse",),
        }),
    )

    # — Actions personnalisées —
    actions = [
        "action_publier",
        "action_mettre_en_avant",
        "action_marquer_reserve",
        "action_archiver",
        "action_coup_de_coeur",
    ]

    @admin.action(description="✅ Publier les biens sélectionnés")
    def action_publier(self, request, queryset):
        count = queryset.update(
            statut=StatutBien.PUBLIE,
            publie_par_admin=True,
            date_publication=timezone.now(),
        )
        self.message_user(request, f"{count} bien(s) publié(s) avec succès.")

    @admin.action(description="⭐ Mettre en avant (Premium)")
    def action_mettre_en_avant(self, request, queryset):
        count = queryset.update(est_mis_en_avant=True)
        self.message_user(request, f"{count} bien(s) mis en avant.")

    @admin.action(description="🔒 Marquer comme Réservé")
    def action_marquer_reserve(self, request, queryset):
        count = queryset.update(statut=StatutBien.RESERVE)
        self.message_user(request, f"{count} bien(s) marqué(s) comme Réservé.")

    @admin.action(description="📦 Archiver les biens sélectionnés")
    def action_archiver(self, request, queryset):
        count = queryset.update(statut=StatutBien.ARCHIVE)
        self.message_user(request, f"{count} bien(s) archivé(s).")

    @admin.action(description="❤️ Marquer comme Coup de cœur")
    def action_coup_de_coeur(self, request, queryset):
        count = queryset.update(est_coup_de_coeur=True)
        self.message_user(request, f"{count} bien(s) marqué(s) Coup de cœur.")

    # — save_model : admin qui publie directement —
    def save_model(self, request, obj, form, change):
        if obj.statut == StatutBien.PUBLIE:
            obj.publie_par_admin = True
            if not obj.date_publication:
                obj.date_publication = timezone.now()
        super().save_model(request, obj, form, change)

    # — Colonnes personnalisées —

    def titre_avec_badge(self, obj):
        badges = ""
        if obj.est_coup_de_coeur:
            badges += ' <span style="background:#F4A261;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">❤️ Coup de cœur</span>'
        if obj.est_mis_en_avant:
            badges += ' <span style="background:#2D6A4F;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">⭐ En avant</span>'
        return format_html("{}{}", obj.titre, mark_safe(badges))
    titre_avec_badge.short_description = "Titre"

    def prix_formate_display(self, obj):
        return obj.prix_formate
    prix_formate_display.short_description = "Prix"

    STATUT_COULEURS = {
        "PUBLIE":                ("#2D6A4F", "#fff"),
        "EN_ATTENTE_VALIDATION": ("#F4A261", "#fff"),
        "RESERVE":               ("#457B9D", "#fff"),
        "LOUE_VENDU":            ("#6c757d", "#fff"),
        "REFUSE":                ("#e63946", "#fff"),
        "ARCHIVE":               ("#adb5bd", "#333"),
        "BROUILLON":             ("#dee2e6", "#333"),
    }

    def statut_badge(self, obj):
        bg, fg = self.STATUT_COULEURS.get(obj.statut, ("#dee2e6", "#333"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">{}</span>',
            bg, fg, obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"

    def apercu_photo_principale(self, obj):
        photo = obj.photo_principale
        if photo and photo.image:
            return format_html(
                '<img src="{}" style="max-width:300px;border-radius:8px;" />',
                photo.image.url
            )
        return "Aucune photo"
    apercu_photo_principale.short_description = "Aperçu photo principale"


# ─────────────────────────────────────────────────────────────────
# PROFIL IMMO ADMIN
# ─────────────────────────────────────────────────────────────────

@admin.register(ProfilImmo)
class ProfilImmoAdmin(admin.ModelAdmin):
    list_display  = ["user", "role", "compte_type", "ville", "est_verifie", "date_expiration_premium", "created_at"]
    list_filter   = ["role", "compte_type", "est_verifie", "ville"]
    list_editable = ["compte_type", "est_verifie"]
    search_fields = ["user__username", "user__email", "telephone", "ville"]
    readonly_fields = ["created_at", "updated_at"]


# ─────────────────────────────────────────────────────────────────
# DEMANDE DE VISITE ADMIN
# ─────────────────────────────────────────────────────────────────

@admin.register(DemandeVisite)
class DemandeVisiteAdmin(admin.ModelAdmin):
    list_display  = ["nom_complet", "telephone", "bien", "date_souhaitee", "statut", "created_at"]
    list_filter   = ["statut", "created_at"]
    search_fields = ["nom_complet", "telephone", "email", "bien__titre"]
    list_editable = ["statut"]
    readonly_fields = ["created_at"]
    actions = ["action_confirmer", "action_annuler"]

    @admin.action(description="✅ Confirmer les visites sélectionnées")
    def action_confirmer(self, request, queryset):
        queryset.update(statut="CONFIRME")
        self.message_user(request, "Visites confirmées.")

    @admin.action(description="❌ Annuler les visites sélectionnées")
    def action_annuler(self, request, queryset):
        queryset.update(statut="ANNULE")
        self.message_user(request, "Visites annulées.")


# ─────────────────────────────────────────────────────────────────
# SIGNALEMENT ADMIN
# ─────────────────────────────────────────────────────────────────

@admin.register(SignalementBien)
class SignalementBienAdmin(admin.ModelAdmin):
    list_display  = ["bien", "motif", "user", "traite", "created_at"]
    list_filter   = ["motif", "traite"]
    list_editable = ["traite"]
    readonly_fields = ["created_at"]


# ─────────────────────────────────────────────────────────────────
# SOUMISSION DE BIEN ADMIN
# ─────────────────────────────────────────────────────────────────

@admin.register(DemandeSoumissionBien)
class DemandeSoumissionBienAdmin(admin.ModelAdmin):
    list_display  = ["nom_complet", "telephone", "type_bien_display", "ville", "statut_badge_soumission", "created_at"]
    list_filter   = ["statut", "type_bien", "ville"]
    search_fields = ["nom_complet", "telephone", "email", "ville", "quartier"]
    readonly_fields = ["created_at"]
    actions = ["action_creer_bien", "action_rejeter"]

    STATUT_COULEURS = {
        "RECU":          ("#F4A261", "#fff"),
        "EN_TRAITEMENT": ("#457B9D", "#fff"),
        "PUBLIE":        ("#2D6A4F", "#fff"),
        "REJETE":        ("#e63946", "#fff"),
    }

    def type_bien_display(self, obj):
        return obj.get_type_bien_display()
    type_bien_display.short_description = "Type de bien"

    def statut_badge_soumission(self, obj):
        bg, fg = self.STATUT_COULEURS.get(obj.statut, ("#dee2e6", "#333"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">{}</span>',
            bg, fg, obj.get_statut_display()
        )
    statut_badge_soumission.short_description = "Statut"

    @admin.action(description="🏠 Créer un bien à partir de cette soumission")
    def action_creer_bien(self, request, queryset):
        """Redirige vers le formulaire admin de création de Bien prérempli."""
        soumission = queryset.first()
        if not soumission:
            return
        # Marquer en traitement
        queryset.update(statut="EN_TRAITEMENT")
        # Redirection vers l'ajout de bien avec paramètres préremplis
        url = (
            reverse("admin:immobilier_cameroun_bien_add")
            + f"?type_bien={soumission.type_bien}"
            + f"&ville={soumission.ville}"
            + f"&quartier={soumission.quartier}"
        )
        return HttpResponseRedirect(url)

    @admin.action(description="❌ Rejeter les soumissions sélectionnées")
    def action_rejeter(self, request, queryset):
        queryset.update(statut="REJETE")
        self.message_user(request, "Soumissions rejetées.")


# ─────────────────────────────────────────────────────────────────
# FAVORIS ADMIN (lecture seule, pour stats)
# ─────────────────────────────────────────────────────────────────

@admin.register(FavorisBien)
class FavorisBienAdmin(admin.ModelAdmin):
    list_display = ["user", "bien", "created_at"]
    readonly_fields = ["user", "bien", "created_at"]
    list_filter = ["created_at"]


# ─────────────────────────────────────────────────────────────────
# BROUILLONS WHATSAPP ADMIN
# ─────────────────────────────────────────────────────────────────

from .models_whatsapp_draft import WhatsappImmoDraft

@admin.register(WhatsappImmoDraft)
class WhatsappImmoDraftAdmin(admin.ModelAdmin):
    list_display = [
        "parsed_titre", "status_badge", "parsed_prix_display",
        "parsed_quartier", "parsed_ville", "source_name", "source_phone",
        "photos_count_display", "ai_quality_badge", "created_at"
    ]
    list_filter = ["status", "parsed_ville", "parsed_type_bien", "whatsapp_group_name"]
    search_fields = ["parsed_titre", "parsed_quartier", "source_name", "source_phone", "raw_text"]
    readonly_fields = [
        "uuid", "created_at", "updated_at", "ai_quality_score",
        "facebook_post_id", "created_bien"
    ]
    actions = ["action_valider_et_publier", "action_rejeter"]

    STATUS_COLORS = {
        "PENDING":  ("#F4A261", "#ffffff"),
        "APPROVED": ("#2D6A4F", "#ffffff"),
        "REJECTED": ("#E63946", "#ffffff"),
    }

    def status_badge(self, obj):
        bg, fg = self.STATUS_COLORS.get(obj.status, ("#adb5bd", "#ffffff"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;">{}</span>',
            bg, fg, obj.get_status_display()
        )
    status_badge.short_description = "Statut"

    def parsed_prix_display(self, obj):
        if obj.parsed_prix:
            return f"{int(obj.parsed_prix):,} XAF".replace(",", " ")
        return "—"
    parsed_prix_display.short_description = "Prix"

    def photos_count_display(self, obj):
        return format_html("📸 <strong>{}</strong> (5 retenues)", obj.total_images_count)
    photos_count_display.short_description = "Photos"

    def ai_quality_badge(self, obj):
        color = "#2D6A4F" if obj.ai_quality_score >= 70 else "#E76F51"
        return format_html(
            '<span style="color:{};font-weight:700;">{:.0f}/100</span>',
            color, obj.ai_quality_score
        )
    ai_quality_badge.short_description = "Score IA"

    @admin.action(description="🚀 Valider et publier le bien sélectionné (+ Facebook)")
    def action_valider_et_publier(self, request, queryset):
        from .views.whatsapp_import import execute_draft_validation
        count = 0
        for draft in queryset.filter(status=WhatsappImmoDraft.Status.PENDING):
            bien = execute_draft_validation(draft, user=request.user)
            if bien:
                count += 1
        self.message_user(request, f"{count} bien(s) validé(s) et publié(s) avec succès sur E-Shelle & Facebook.")

    @admin.action(description="❌ Rejeter les brouillons sélectionnés")
    def action_rejeter(self, request, queryset):
        updated = queryset.update(status=WhatsappImmoDraft.Status.REJECTED)
        self.message_user(request, f"{updated} brouillon(s) rejeté(s).")

