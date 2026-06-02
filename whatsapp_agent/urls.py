from django.urls import path

from . import views

app_name = "whatsapp_agent"

urlpatterns = [
    path("campagnes/", views.dashboard_campagnes, name="wa_dashboard"),
    path("contacts/", views.contacts_whatsapp, name="wa_contacts"),
    path("contacts/campagne/", views.creer_campagne_contacts, name="wa_contacts_campagne"),
    path("contacts/importer/", views.importer_contacts, name="wa_import_contacts"),
    path("campagnes/creer/", views.creer_campagne, name="wa_creer"),
    path("campagnes/<int:pk>/", views.detail_campagne, name="wa_detail"),
    path("campagnes/<int:pk>/lancer/", views.lancer_campagne, name="wa_lancer"),
    path("campagnes/<int:pk>/test/", views.envoyer_test_campagne, name="wa_test"),
    path("campagnes/<int:pk>/dupliquer/", views.dupliquer_campagne, name="wa_dupliquer"),
    path("campagnes/<int:pk>/relancer/", views.relancer_non_repondants, name="wa_relancer"),
    path("campagnes/<int:pk>/export/", views.export_csv, name="wa_export"),
    path("api/generer-message/", views.api_generer_message, name="wa_api_generer"),
    path("api/apercu-contacts/", views.api_apercu_contacts, name="wa_api_apercu"),
    path("api/import-contact/", views.api_import_contact, name="wa_api_import_contact"),
    path("webhook/", views.webhook_meta, name="wa_webhook"),
]
