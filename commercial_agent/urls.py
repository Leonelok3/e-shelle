from django.urls import path

from . import views

app_name = "commercial_agent"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("prospects/", views.prospect_list, name="prospect_list"),
    path("prospects/<int:pk>/", views.prospect_detail, name="prospect_detail"),
    path("prospects/<int:pk>/message/", views.generate_message, name="generate_message"),
    path("prospects/<int:pk>/relance/", views.create_relance, name="create_relance"),
    path("prospects/<int:pk>/statut/", views.update_status, name="update_status"),
    path("sync-business/", views.sync_business, name="sync_business"),
    path("sync-whatsapp-contacts/", views.sync_whatsapp_contacts, name="sync_whatsapp_contacts"),
    path("campagne-auto/", views.create_auto_campaign, name="create_auto_campaign"),
    path("campagne-whatsapp/", views.create_whatsapp_campaign, name="create_whatsapp_campaign"),
    path("sourcing/", views.sourcing_hub, name="sourcing_hub"),
    path("sourcing/import-lead/", views.import_sourcing_lead, name="import_sourcing_lead"),
    path("sourcing/import-bulk/", views.import_sourcing_bulk, name="import_sourcing_bulk"),
    path("sourcing/create-resto-draft/", views.create_resto_draft_view, name="create_resto_draft"),
    path("sourcing/export-csv/", views.export_sourcing_csv, name="export_sourcing_csv"),
]
