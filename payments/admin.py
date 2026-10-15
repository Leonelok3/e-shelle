from django.contrib import admin
from django.utils.html import format_html
from .models import Transaction, Coupon, PlanPremiumApp


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ("reference", "utilisateur", "type_tx", "methode",
                      "montant_affiche", "statut_display", "created_at")
    list_filter   = ("statut", "methode", "type_tx")
    search_fields = ("reference", "utilisateur__username", "telephone", "ref_operateur")
    readonly_fields = ("reference", "created_at", "updated_at")
    date_hierarchy = "created_at"

    def montant_affiche(self, obj):
        return f"{int(obj.montant):,} {obj.devise}".replace(",", " ")
    montant_affiche.short_description = "Montant"

    def statut_display(self, obj):
        colors = {
            "succes":     "#4CAF50",
            "echec":      "#EF5350",
            "rembourse":  "#FF9800",
            "en_attente": "#FFB74D",
            "pending_awaiting_manual_validation": "#FFB74D",
            "initie":     "#9E9E9E",
            "expire":     "#616161",
        }
        return format_html('<span style="color:{};font-weight:600">{}</span>',
                           colors.get(obj.statut, "#fff"), obj.get_statut_display())
    statut_display.short_description = "Statut"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ("code", "type_coupon", "valeur", "nb_utilisations",
                      "max_utilisations", "est_valide_display", "actif")
    list_filter   = ("type_coupon", "actif")
    search_fields = ("code",)
    list_editable = ("actif",)

    def est_valide_display(self, obj):
        if obj.est_valide:
            return format_html('<span style="color:#4CAF50">✓ Valide</span>')
        return format_html('<span style="color:#EF5350">✗ Invalide</span>')
    est_valide_display.short_description = "Validité"


@admin.register(PlanPremiumApp)
class PlanPremiumAppAdmin(admin.ModelAdmin):
    list_display  = ("module_display", "nom_display", "prix_display",
                     "duree_display", "populaire", "actif", "ordre")
    list_filter   = ("module", "actif", "populaire")
    list_editable = ("actif", "populaire", "ordre")
    search_fields = ("nom", "module")
    ordering      = ("module", "ordre")

    fieldsets = (
        ("Identification", {
            "fields": ("module", "slug", "nom", "emoji", "couleur"),
            "description": "Identifie le plan. Le slug doit être unique par module (ex: starter, pro, expert)."
        }),
        ("Tarification", {
            "fields": ("prix", "duree_jours"),
        }),
        ("Contenu affiché", {
            "fields": ("description", "benefices"),
            "description": (
                'benefices = liste JSON des avantages. Exemple :<br>'
                '<code>["30 jours Premium","Annonces illimitées","Badge visible","Priorité résultats"]</code>'
            ),
        }),
        ("Affichage", {
            "fields": ("populaire", "ordre", "actif"),
        }),
    )

    def module_display(self, obj):
        return format_html('<strong>{}</strong>', obj.get_module_display())
    module_display.short_description = "Application"
    module_display.admin_order_field = "module"

    def nom_display(self, obj):
        return format_html(
            '<span style="color:{};font-weight:700">{} {}</span>',
            obj.couleur, obj.emoji, obj.nom
        )
    nom_display.short_description = "Plan"

    def prix_display(self, obj):
        return format_html('<strong>{:,} FCFA</strong>', obj.prix).replace(",", " ")
    prix_display.short_description = "Prix"
    prix_display.admin_order_field = "prix"

    def duree_display(self, obj):
        if obj.duree_jours >= 365:
            return f"1 an"
        if obj.duree_jours >= 30:
            return f"{obj.duree_jours // 30} mois"
        return f"{obj.duree_jours} jours"
    duree_display.short_description = "Durée"
