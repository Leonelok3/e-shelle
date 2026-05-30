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
    path("campagne-auto/", views.create_auto_campaign, name="create_auto_campaign"),
    path("campagne-whatsapp/", views.create_whatsapp_campaign, name="create_whatsapp_campaign"),
]
