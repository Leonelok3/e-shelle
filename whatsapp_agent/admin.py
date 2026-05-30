from django.contrib import admin, messages

from .models import Campagne, MessageEnvoi, TemplateWhatsApp
from .tasks import lancer_campagne_task


@admin.register(Campagne)
class CampagneAdmin(admin.ModelAdmin):
    list_display = ["nom", "statut", "total_destinataires", "total_envoyes", "total_livres", "total_echecs", "cree_le"]
    list_filter = ["statut", "cree_le"]
    search_fields = ["nom", "description", "message_template"]
    readonly_fields = ["total_destinataires", "total_envoyes", "total_livres", "total_lus", "total_echecs", "cree_le", "lance_le", "termine_le"]
    actions = ["lancer_campagnes_selectionnees"]

    @admin.action(description="Lancer les campagnes selectionnees")
    def lancer_campagnes_selectionnees(self, request, queryset):
        count = 0
        for campagne in queryset.filter(statut=Campagne.STATUT_VALIDEE):
            lancer_campagne_task.delay(campagne.id)
            count += 1
        self.message_user(request, f"{count} campagne(s) lancee(s).", messages.SUCCESS)


@admin.register(MessageEnvoi)
class MessageEnvoiAdmin(admin.ModelAdmin):
    list_display = ["campagne", "user", "numero_whatsapp", "statut", "envoye_le"]
    list_filter = ["statut", "campagne"]
    search_fields = ["numero_whatsapp", "user__username", "user__email", "whatsapp_message_id"]
    raw_id_fields = ["campagne", "user"]


@admin.register(TemplateWhatsApp)
class TemplateWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["nom", "langue", "actif", "cree_le"]
    list_filter = ["langue", "actif"]
    search_fields = ["nom", "contenu_preview"]
