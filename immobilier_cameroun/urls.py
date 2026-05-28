"""
urls.py — immobilier_cameroun
"""
from django.urls import path
from . import views

app_name = "immobilier"

urlpatterns = [
    # ── Catalogue public ──────────────────────────────────────────
    path("",                    views.liste_biens,    name="liste_biens"),
    path("bien/<slug:slug>/",   views.detail_bien,    name="detail_bien"),
    path("agent/<str:username>/", views.espace_agent, name="espace_agent"),
    path("recherche/",          views.recherche_biens, name="recherche_biens"),

    # ── Compte utilisateur ────────────────────────────────────────
    path("inscription/",                        views.inscription,   name="inscription"),
    path("mon-compte/",                         views.mon_compte,    name="mon_compte"),
    path("mon-compte/biens/",                   views.mes_biens,     name="mes_biens"),
    path("mon-compte/publier/",                 views.publier_bien,  name="publier_bien"),
    path("mon-compte/modifier/<slug:slug>/",    views.modifier_bien, name="modifier_bien"),
    path("mon-compte/supprimer/<slug:slug>/",   views.supprimer_bien, name="supprimer_bien"),
    path("mon-compte/favoris/",                 views.mes_favoris,   name="mes_favoris"),
    path("mon-compte/premium/",                 views.upgrade_premium, name="upgrade_premium"),

    # ── Actions AJAX ──────────────────────────────────────────────
    path("ajax/toggle-favori/<int:bien_id>/",   views.toggle_favori,    name="toggle_favori"),
    path("ajax/marquer-reserve/<slug:slug>/",   views.marquer_reserve,  name="marquer_reserve"),
    path("ajax/incrementer-vue/<int:bien_id>/", views.incrementer_vue,  name="incrementer_vue"),

    # ── Formulaires publics ───────────────────────────────────────
    path("demande-visite/<slug:slug>/", views.demande_visite, name="demande_visite"),
    path("soumettre-bien/",             views.soumettre_bien, name="soumettre_bien"),
    path("signaler/<int:bien_id>/",     views.signaler_bien,  name="signaler_bien"),
]
