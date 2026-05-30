from django.urls import path

from . import views

app_name = "whatsapp_agent"

urlpatterns = [
    path("campagnes/", views.dashboard_campagnes, name="wa_dashboard"),
    path("campagnes/creer/", views.creer_campagne, name="wa_creer"),
    path("campagnes/<int:pk>/", views.detail_campagne, name="wa_detail"),
    path("campagnes/<int:pk>/lancer/", views.lancer_campagne, name="wa_lancer"),
    path("campagnes/<int:pk>/export/", views.export_csv, name="wa_export"),
    path("api/generer-message/", views.api_generer_message, name="wa_api_generer"),
    path("api/apercu-contacts/", views.api_apercu_contacts, name="wa_api_apercu"),
    path("webhook/", views.webhook_meta, name="wa_webhook"),
]
