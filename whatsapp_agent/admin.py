from django.contrib import admin, messages

from .models import (
    Campagne,
    ContactWhatsApp,
    ConversationWhatsApp,
    MessageEnvoi,
    MessageWhatsApp,
    OutreachLog,
    TemplateWhatsApp,
)
from .tasks import lancer_campagne_task


@admin.register(ContactWhatsApp)
class ContactWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["nom", "numero", "ville", "groupe", "source", "consentement_confirme", "desinscrit", "cree_le"]
    list_filter = ["source", "consentement_confirme", "desinscrit", "ville", "cree_le"]
    search_fields = ["nom", "numero", "ville", "groupe", "note"]
    readonly_fields = ["cree_le", "mis_a_jour_le"]


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


@admin.register(ConversationWhatsApp)
class ConversationWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["contact", "statut", "priorite", "non_lus_count", "dernier_message_le", "assigne_a"]
    list_filter = ["statut", "priorite", "dernier_message_le"]
    search_fields = ["contact__nom", "contact__numero", "notes", "dernier_message_apercu"]
    raw_id_fields = ["contact", "commercial_prospect", "assigne_a", "derniere_campagne"]


@admin.register(MessageWhatsApp)
class MessageWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["conversation", "direction", "statut", "whatsapp_msg_id", "cree_le"]
    list_filter = ["direction", "statut", "cree_le"]
    search_fields = ["texte", "whatsapp_msg_id", "conversation__contact__numero"]
    raw_id_fields = ["conversation", "envoye_par", "campagne"]


@admin.register(TemplateWhatsApp)
class TemplateWhatsAppAdmin(admin.ModelAdmin):
    list_display = ["nom", "langue", "actif", "cree_le"]
    list_filter = ["langue", "actif"]
    search_fields = ["nom", "contenu_preview"]


@admin.register(OutreachLog)
class OutreachLogAdmin(admin.ModelAdmin):
    list_display = ["canal", "identifiant", "statut", "sujet", "envoye_le", "campagne"]
    list_filter = ["canal", "statut", "envoye_le"]
    search_fields = ["identifiant", "sujet"]
    readonly_fields = ["envoye_le"]
