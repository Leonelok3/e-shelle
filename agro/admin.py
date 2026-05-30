from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    ActeurAgro, CategorieAgro, ProduitAgro, PhotoProduit,
    ModerationProduit, OffreCommerciale, AppelOffre,
    ReponseAppelOffre, DemandeDevis, CommandeAgro,
    CertificationAgro, AvisActeur, ZoneLivraison,
    PrixMarche, QuestionAgentIA, StockProducteur,
)


# ─── Inlines ─────────────────────────────────────────────────────────────────

class PhotoProduitInline(admin.TabularInline):
    model = PhotoProduit
    extra = 1
    fields = ['image', 'legende', 'est_principale', 'ordre']


class CertificationInline(admin.TabularInline):
    model = CertificationAgro
    extra = 0
    fields = ['type_certification', 'nom', 'organisme', 'date_expiration', 'est_verifie_admin']


class ModerationInline(admin.StackedInline):
    model = ModerationProduit
    extra = 0
    fields = ['statut', 'motif_rejet', 'date_moderation']


# ─── ActeurAgro ──────────────────────────────────────────────────────────────

@admin.register(ActeurAgro)
class ActeurAgroAdmin(admin.ModelAdmin):
    list_display  = ['nom_entreprise', 'type_acteur', 'pays', 'ville',
                     'plan_premium', 'est_verifie', 'est_actif', 'score_confiance',
                     'nb_produits', 'date_inscription']
    list_filter   = ['type_acteur', 'pays', 'plan_premium', 'est_verifie',
                     'est_actif', 'vend_internationalement']
    search_fields = ['nom_entreprise', 'email_pro', 'telephone', 'ville', 'user__username']
    readonly_fields = ['slug', 'date_inscription', 'derniere_activite',
                       'nb_vues', 'nb_produits', 'nb_commandes', 'score_confiance']
    list_editable   = ['est_verifie', 'est_actif', 'plan_premium']
    ordering        = ['-date_inscription']
    inlines         = [CertificationInline]

    fieldsets = (
        ('Identité', {
            'fields': ('user', 'type_acteur', 'nom_entreprise', 'nom_contact',
                       'poste_contact', 'logo', 'photo_couverture', 'description',
                       'annee_creation', 'nb_employes')
        }),
        ('Localisation', {
            'fields': ('pays', 'region', 'ville', 'adresse',
                       'latitude', 'longitude', 'code_postal')
        }),
        ('Contact', {
            'fields': ('telephone', 'telephone2', 'whatsapp', 'email_pro', 'site_web')
        }),
        ('Capacités commerciales', {
            'fields': ('superficie_ha', 'capacite_stockage_tonnes', 'volume_annuel_tonnes',
                       'devises_acceptees', 'modes_paiement', 'langues_travail'),
            'classes': ('collapse',)
        }),
        ('Zones de vente', {
            'fields': ('vend_localement', 'vend_nationalement',
                       'vend_internationalement', 'zones_export'),
            'classes': ('collapse',)
        }),
        ('Statut & Plan', {
            'fields': ('est_verifie', 'est_premium', 'plan_premium', 'plan_expiry',
                       'est_actif', 'est_en_ligne', 'profil_complet', 'score_confiance')
        }),
        ('Statistiques', {
            'fields': ('nb_vues', 'nb_produits', 'nb_commandes', 'nb_avis', 'note_moyenne'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('slug', 'date_inscription', 'derniere_activite'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ─── CategorieAgro ───────────────────────────────────────────────────────────

@admin.register(CategorieAgro)
class CategorieAgroAdmin(admin.ModelAdmin):
    list_display  = ['icone', 'nom', 'parent', 'ordre', 'est_active', 'nb_produits_actifs']
    list_filter   = ['est_active', 'parent']
    search_fields = ['nom', 'description']
    list_editable = ['ordre', 'est_active']
    prepopulated_fields = {'slug': ('nom',)}

    def nb_produits_actifs(self, obj):
        return obj.produits.filter(statut='publie').count()
    nb_produits_actifs.short_description = 'Produits publiés'


# ─── ProduitAgro ─────────────────────────────────────────────────────────────

@admin.register(ProduitAgro)
class ProduitAgroAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'acteur_link', 'categorie', 'statut', 'prix_unitaire',
                     'devise', 'disponibilite', 'est_mis_en_avant', 'nb_vues', 'date_creation']
    list_filter   = ['statut', 'categorie', 'disponibilite', 'est_bio',
                     'est_equitable', 'peut_exporter', 'est_mis_en_avant']
    search_fields = ['nom', 'nom_local', 'reference', 'acteur__nom_entreprise', 'tags']
    readonly_fields  = ['reference', 'slug', 'nb_vues', 'nb_demandes',
                        'nb_favoris', 'date_creation', 'date_mise_a_jour']
    list_editable    = ['statut', 'est_mis_en_avant']
    inlines          = [PhotoProduitInline, ModerationInline]
    date_hierarchy   = 'date_creation'
    ordering         = ['-date_creation']

    fieldsets = (
        ('Identification', {
            'fields': ('acteur', 'categorie', 'nom', 'nom_local', 'slug',
                       'reference', 'code_hs')
        }),
        ('Description', {
            'fields': ('description', 'caracteristiques',
                       'origine_geographique', 'tags')
        }),
        ('Prix', {
            'fields': ('prix_unitaire', 'devise', 'prix_negociable', 'prix_degressif')
        }),
        ('Quantités', {
            'fields': ('unite_mesure', 'quantite_stock', 'quantite_min_commande',
                       'quantite_max_commande', 'conditionnement')
        }),
        ('Disponibilité', {
            'fields': ('disponibilite', 'delai_livraison_jours',
                       'saison_disponible', 'production_annuelle_tonnes')
        }),
        ('Qualité', {
            'fields': ('normes_qualite', 'est_bio', 'est_equitable',
                       'taux_humidite', 'granulometrie', 'autres_specs')
        }),
        ('Export', {
            'fields': ('peut_exporter', 'incoterms_disponibles', 'port_embarquement',
                       'pays_export_autorises', 'documents_export_disponibles'),
            'classes': ('collapse',)
        }),
        ('Médias & SEO', {
            'fields': ('image_principale', 'video_url',
                       'meta_titre', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('statut', 'est_mis_en_avant', 'nb_vues', 'nb_demandes',
                       'nb_favoris', 'note_moyenne', 'date_creation', 'date_mise_a_jour')
        }),
    )

    def acteur_link(self, obj):
        return format_html(
            '<a href="/admin/agro/acteuragro/{}/change/">{}</a>',
            obj.acteur.pk, obj.acteur.nom_entreprise
        )
    acteur_link.short_description = 'Acteur'

    actions = ['publier_produits', 'suspendre_produits']

    def publier_produits(self, request, queryset):
        queryset.update(statut='publie')
        self.message_user(request, f"{queryset.count()} produit(s) publié(s).")
    publier_produits.short_description = "Publier les produits sélectionnés"

    def suspendre_produits(self, request, queryset):
        queryset.update(statut='suspendu')
        self.message_user(request, f"{queryset.count()} produit(s) suspendu(s).")
    suspendre_produits.short_description = "Suspendre les produits sélectionnés"


# ─── Offres ──────────────────────────────────────────────────────────────────

@admin.register(OffreCommerciale)
class OffreCommercialeAdmin(admin.ModelAdmin):
    list_display = ['titre', 'acteur', 'type_offre', 'quantite', 'unite_mesure',
                    'prix_propose', 'devise', 'est_urgente', 'est_active', 'date_publication']
    list_filter  = ['type_offre', 'est_urgente', 'est_active', 'devise']
    search_fields = ['titre', 'acteur__nom_entreprise']
    list_editable = ['est_urgente', 'est_active']


@admin.register(AppelOffre)
class AppelOffreAdmin(admin.ModelAdmin):
    list_display  = ['titre', 'acheteur', 'categorie', 'quantite_min',
                     'unite_mesure', 'budget_max', 'devise', 'est_urgent',
                     'est_publie', 'nb_reponses', 'date_creation']
    list_filter   = ['est_urgent', 'est_publie', 'categorie']
    search_fields = ['titre', 'acheteur__nom_entreprise']
    list_editable = ['est_urgent', 'est_publie']


# ─── Commandes / Devis ───────────────────────────────────────────────────────

@admin.register(DemandeDevis)
class DemandeDevisAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'acheteur', 'vendeur', 'quantite',
                     'unite_mesure', 'destination', 'statut', 'date_creation']
    list_filter   = ['statut', 'unite_mesure']
    search_fields = ['reference', 'acheteur__nom_entreprise', 'vendeur__nom_entreprise']
    readonly_fields = ['reference', 'date_creation', 'date_mise_a_jour']
    ordering       = ['-date_creation']


@admin.register(CommandeAgro)
class CommandeAgroAdmin(admin.ModelAdmin):
    list_display  = ['numero_commande', 'acheteur', 'vendeur', 'montant_total',
                     'devise', 'statut', 'paiement_statut', 'date_creation']
    list_filter   = ['statut', 'paiement_statut', 'devise']
    search_fields = ['numero_commande', 'acheteur__nom_entreprise', 'vendeur__nom_entreprise']
    readonly_fields = ['numero_commande', 'date_creation', 'date_mise_a_jour']
    list_editable   = ['statut', 'paiement_statut']
    ordering        = ['-date_creation']


# ─── Intelligence agro ───────────────────────────────────────────────────────

@admin.register(PrixMarche)
class PrixMarcheAdmin(admin.ModelAdmin):
    list_display = ['produit', 'ville', 'prix_moyen', 'unite', 'tendance', 'date_releve']
    list_filter = ['ville', 'tendance', 'date_releve']
    search_fields = ['produit', 'ville']


@admin.register(QuestionAgentIA)
class QuestionAgentIAAdmin(admin.ModelAdmin):
    list_display = ['agent_type', 'utilisateur', 'question', 'date_creation']
    list_filter = ['agent_type', 'date_creation']
    search_fields = ['question', 'reponse', 'utilisateur__username']
    readonly_fields = ['date_creation']


@admin.register(StockProducteur)
class StockProducteurAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'produit', 'quantite', 'seuil_alerte', 'date_mise_a_jour']
    list_filter = ['date_mise_a_jour']
    search_fields = ['utilisateur__username', 'produit__nom']


# ─── Certifications ──────────────────────────────────────────────────────────

@admin.register(CertificationAgro)
class CertificationAgroAdmin(admin.ModelAdmin):
    list_display = ['nom', 'acteur', 'type_certification', 'organisme',
                    'date_expiration', 'est_verifie_admin', 'est_valide']
    list_filter  = ['type_certification', 'est_verifie_admin', 'est_valide']
    search_fields = ['nom', 'organisme', 'acteur__nom_entreprise']
    list_editable = ['est_verifie_admin', 'est_valide']

    actions = ['verifier_certifications']

    def verifier_certifications(self, request, queryset):
        queryset.update(est_verifie_admin=True)
        self.message_user(request, f"{queryset.count()} certification(s) vérifiée(s).")
    verifier_certifications.short_description = "Marquer comme vérifiées"


# ─── Avis ────────────────────────────────────────────────────────────────────

@admin.register(AvisActeur)
class AvisActeurAdmin(admin.ModelAdmin):
    list_display  = ['evaluateur', 'evalue', 'note_globale', 'est_publie',
                     'est_verifie', 'date_avis']
    list_filter   = ['note_globale', 'est_publie', 'est_verifie']
    search_fields = ['evaluateur__nom_entreprise', 'evalue__nom_entreprise', 'commentaire']
    list_editable = ['est_publie', 'est_verifie']
    readonly_fields = ['date_avis']
