from django.urls import path
from . import views

app_name = "auto"

urlpatterns = [
    # Catalogue
    path("",                              views.liste_vehicules,       name="liste_vehicules"),
    path("vehicule/<slug:slug>/",         views.detail_vehicule,       name="detail_vehicule"),
    path("vendeur/<str:username>/",       views.espace_vendeur,        name="espace_vendeur"),

    # Mon compte
    path("compte/",                       views.mon_compte_auto,       name="mon_compte"),
    path("compte/vehicules/",             views.mes_vehicules,         name="mes_vehicules"),
    path("compte/publier/",               views.publier_vehicule,      name="publier_vehicule"),
    path("compte/modifier/<slug:slug>/",  views.modifier_vehicule,     name="modifier_vehicule"),
    path("compte/supprimer/<slug:slug>/", views.supprimer_vehicule,    name="supprimer_vehicule"),
    path("compte/favoris/",              views.mes_favoris_auto,       name="mes_favoris"),
    path("compte/premium/",              views.upgrade_premium_auto,   name="upgrade_premium"),

    # AJAX
    path("ajax/favori/<int:pk>/",         views.toggle_favori_auto,    name="toggle_favori"),
    path("ajax/reserver/<slug:slug>/",    views.marquer_reserve_auto,  name="marquer_reserve"),

    # Sans compte
    path("soumettre/",                    views.soumettre_vehicule,    name="soumettre_vehicule"),
    path("signaler/<int:vehicule_id>/",   views.signaler_vehicule,     name="signaler_vehicule"),
]
