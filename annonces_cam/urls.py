from django.urls import path
from . import views

app_name = "annonces"

urlpatterns = [
    # Catalogue
    path("",                                       views.liste_annonces,          name="liste_annonces"),
    path("categorie/<slug:slug_categorie>/",        views.annonces_par_categorie,  name="annonces_par_categorie"),
    path("annonce/<slug:slug>/",                    views.detail_annonce,          name="detail_annonce"),

    # Profil vendeur public
    path("vendeur/<int:user_id>/",                 views.profil_vendeur_public,   name="profil_vendeur_public"),
    path("boutique/<str:username>/",               views.profil_vendeur_username, name="profil_vendeur_username"),

    # Mon compte
    path("compte/",                                views.mon_compte_annonces,     name="mon_compte"),
    path("compte/mes-annonces/",                   views.mes_annonces,            name="mes_annonces"),
    path("compte/publier/",                        views.publier_annonce,         name="publier_annonce"),
    path("compte/modifier/<slug:slug>/",           views.modifier_annonce,        name="modifier_annonce"),
    path("compte/supprimer/<slug:slug>/",          views.supprimer_annonce,       name="supprimer_annonce"),
    path("compte/marquer-vendue/<slug:slug>/",     views.marquer_vendue,          name="marquer_vendue"),
    path("compte/favoris/",                        views.mes_favoris,             name="mes_favoris"),
    path("compte/messages/",                       views.mes_messages,            name="mes_messages"),
    path("compte/messages/<int:conv_id>/",         views.detail_conversation,     name="conversation"),
    path("compte/premium/",                        views.upgrade_premium,         name="upgrade_premium"),

    # AJAX
    path("ajax/favori/<int:pk>/",                  views.toggle_favori,           name="toggle_favori"),
    path("ajax/marquer-vendue/<slug:slug>/",        views.marquer_vendue_ajax,     name="marquer_vendue_ajax"),

    # Signalement
    path("signaler/<int:annonce_id>/",             views.signaler_annonce,        name="signaler_annonce"),
]
