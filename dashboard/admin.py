from django.contrib import admin
from .models import Notification, ParametrePlateforme


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("destinataire", "type_notif", "titre", "lue", "created_at")
    list_filter   = ("type_notif", "lue")
    list_editable = ("lue",)
    search_fields = ("destinataire__username", "titre", "message")
    date_hierarchy = "created_at"


@admin.register(ParametrePlateforme)
class ParametrePlateformeAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identité", {
            "fields": ("nom_site", "slogan", "logo", "favicon", "couleur_primaire", "couleur_accent")
        }),
        ("Contact", {
            "fields": ("email_contact", "telephone", "whatsapp", "adresse")
        }),
        ("Réseaux sociaux", {
            "fields": ("lien_facebook", "lien_linkedin", "lien_youtube", "lien_whatsapp")
        }),
        ("SEO", {
            "fields": ("meta_description", "og_image", "google_analytics_id")
        }),
        ("Visuels des pages", {
            "fields": ("produits_services_hero_image",),
            "classes": ("collapse",)
        }),
        ("Paiement (Mobile Money)", {
            "fields": ("mtn_api_key", "airtel_api_key"),
            "classes": ("collapse",)
        }),
        ("Modules actifs", {
            "fields": ("module_formations", "module_boutique", "module_services", "module_ai")
        }),
        ("Maintenance", {
            "fields": ("maintenance", "message_maintenance")
        }),
    )

    def has_add_permission(self, request):
        # Singleton : un seul objet de configuration
        return not ParametrePlateforme.objects.exists()
