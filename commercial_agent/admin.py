from django.contrib import admin, messages

from .models import CampagneProspection, ProspectBusiness, RelanceProspect, ScriptCommercial
from .services import CommercialAgentService


@admin.register(ProspectBusiness)
class ProspectBusinessAdmin(admin.ModelAdmin):
    list_display = ("nom", "module", "ville", "statut", "priorite", "score", "plan_recommande", "montant_potentiel_xaf", "prochain_contact")
    list_filter = ("statut", "priorite", "module", "ville", "source")
    search_fields = ("nom", "ville", "quartier", "telephone", "whatsapp", "email", "responsable")
    raw_id_fields = ("business_profile", "assigne_a", "cree_par")
    actions = ("refresh_scores", "mark_interested", "mark_paid")

    @admin.action(description="Recalculer le score IA")
    def refresh_scores(self, request, queryset):
        for prospect in queryset:
            CommercialAgentService.refresh_prospect(prospect)
        self.message_user(request, f"{queryset.count()} score(s) mis a jour.", messages.SUCCESS)

    @admin.action(description="Marquer interesse")
    def mark_interested(self, request, queryset):
        queryset.update(statut=ProspectBusiness.Statut.INTERESSE)

    @admin.action(description="Marquer paye")
    def mark_paid(self, request, queryset):
        queryset.update(statut=ProspectBusiness.Statut.PAYE)


@admin.register(CampagneProspection)
class CampagneProspectionAdmin(admin.ModelAdmin):
    list_display = ("nom", "statut", "module_cible", "ville_cible", "cree_par", "cree_le", "lance_le")
    list_filter = ("statut", "module_cible", "ville_cible")
    search_fields = ("nom", "objectif", "message_base")
    filter_horizontal = ("prospects",)


@admin.register(ScriptCommercial)
class ScriptCommercialAdmin(admin.ModelAdmin):
    list_display = ("nom", "canal", "module", "actif", "cree_le")
    list_filter = ("canal", "module", "actif")
    search_fields = ("nom", "contenu")


@admin.register(RelanceProspect)
class RelanceProspectAdmin(admin.ModelAdmin):
    list_display = ("prospect", "type_action", "resultat", "montant_xaf", "prochaine_relance", "cree_le")
    list_filter = ("type_action", "resultat", "cree_le")
    search_fields = ("prospect__nom", "message")
    raw_id_fields = ("prospect", "campagne", "effectue_par")
