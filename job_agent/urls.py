from django.urls import path
from . import views
from . import api_views
from .api_views import indeed_autofill_token
app_name = "job_agent"

urlpatterns = [

    # =========================
    # DASHBOARD
    # =========================
    path("", views.dashboard, name="dashboard"),

    # =========================
    # PROFIL & DOCUMENTS
    # =========================
    path("profil/", views.profile_edit, name="profile_edit"),
    path("documents/", views.documents_edit, name="documents_edit"),

    # =========================
    # RECHERCHE
    # =========================
    path("recherche/nouvelle/", views.search_create, name="search_create"),

    # =========================
    # OFFRES UTILISATEUR
    # =========================
    path("offres/", views.lead_list, name="lead_list"),
    path("offres/ajouter/", views.lead_add, name="lead_add"),
    path("offres/ajout-masse/", views.lead_bulk_add, name="lead_bulk_add"),

    path("offres/<int:lead_id>/", views.lead_detail, name="lead_detail"),
    path("offres/<int:lead_id>/pack/", views.pack_detail, name="pack_detail"),

    # =========================
    # OFFRES PUBLIQUES (ADMIN)
    # =========================
    path("offres-publiques/", views.public_offers, name="public_offers"),
    path("apply/<int:lead_id>/", views.apply_wizard, name="apply_wizard"),
    path("offres/<int:lead_id>/postuler/", views.apply_wizard, name="apply_wizard"),


    path(
        "offres-publiques/<int:offer_id>/importer/",
        views.import_public_offer,
        name="import_public_offer",
    ),

    # =========================
    # KANBAN (SUIVI RAPIDE)
    # =========================
    path("kanban/", views.kanban, name="kanban"),
    
    path("kanban/<int:lead_id>/move/", views.kanban_move, name="kanban_move"),
    path("api/indeed/autofill/<int:lead_id>/", api_views.indeed_autofill, name="indeed_autofill"),
    path("api/indeed/autoill/<int:lead_id>/", views.indeed_autofill_api, name="indeed_afutofill_api"),
    path("api/indeed/autofill-token/<int:lead_id>/", indeed_autofill_token, name="indeed_autofill_token"),


]
