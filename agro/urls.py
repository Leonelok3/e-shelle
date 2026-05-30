from django.urls import path
from . import views

app_name = 'agro'

urlpatterns = [
    # ─── Accueil et catalogue ────────────────────────────────────────────────
    path('', views.accueil_agro, name='accueil'),
    path('catalogue/', views.catalogue, name='catalogue'),
    path('marketplace/', views.marketplace_agro, name='marketplace'),
    path('assistant-ia/', views.assistant_ia_agro, name='assistant_ia'),
    path('prix-marche/', views.prix_marche_agro, name='prix_marche'),
    path('dashboard-producteur/', views.dashboard_producteur_agro, name='dashboard_producteur'),
    path('commander/<int:pk>/', views.commander_produit_agro, name='commander_produit'),
    path('categorie/<slug:slug>/', views.categorie, name='categorie'),
    path('produit/<slug:slug>/', views.detail_produit, name='produit'),
    path('recherche/', views.recherche, name='recherche'),

    # ─── Acteurs ─────────────────────────────────────────────────────────────
    path('inscription/', views.inscription_acteur, name='inscription'),
    path('profil/<slug:slug>/', views.profil_public, name='profil'),
    path('mon-profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('annuaire/', views.annuaire_acteurs, name='annuaire'),
    path('annuaire/<str:type_acteur>/', views.annuaire_par_type, name='annuaire_type'),

    # ─── Mes produits ────────────────────────────────────────────────────────
    path('mes-produits/', views.mes_produits, name='mes_produits'),
    path('mes-produits/ajouter/', views.ajouter_produit, name='ajouter_produit'),
    path('mes-produits/<slug:slug>/modifier/', views.modifier_produit, name='modifier_produit'),
    path('mes-produits/<slug:slug>/supprimer/', views.supprimer_produit, name='supprimer_produit'),
    path('mes-produits/photos/<int:pk>/', views.gerer_photos_produit, name='photos_produit'),

    # ─── Offres et appels d'offre ────────────────────────────────────────────
    path('offres/', views.liste_offres, name='offres'),
    path('offres/creer/', views.creer_offre, name='creer_offre'),
    path('offres/<int:pk>/', views.detail_offre, name='detail_offre'),
    path('appels-offre/', views.liste_ao, name='appels_offre'),
    path('appels-offre/lancer/', views.lancer_ao, name='lancer_ao'),
    path('appels-offre/<int:pk>/', views.detail_ao, name='detail_ao'),
    path('appels-offre/<int:pk>/repondre/', views.repondre_ao, name='repondre_ao'),

    # ─── Devis et commandes ──────────────────────────────────────────────────
    path('devis/demander/<slug:produit_slug>/', views.demander_devis, name='demander_devis'),
    path('devis/', views.mes_devis, name='mes_devis'),
    path('devis/<str:reference>/', views.detail_devis, name='detail_devis'),
    path('devis/<str:reference>/repondre/', views.repondre_devis, name='repondre_devis'),
    path('devis/<str:reference>/accepter/', views.accepter_devis, name='accepter_devis'),
    path('commandes/', views.mes_commandes, name='mes_commandes'),
    path('commandes/<str:numero>/', views.detail_commande, name='detail_commande'),

    # ─── Dashboard ───────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/stats/', views.stats_dashboard, name='stats'),
    path('dashboard/certifications/', views.mes_certifications, name='certifications'),
    path('dashboard/avis/', views.mes_avis, name='avis'),

    # ─── Premium ─────────────────────────────────────────────────────────────
    path('premium/', views.page_premium, name='premium'),
    path('premium/souscrire/<str:plan>/', views.souscrire, name='souscrire'),

    # ─── AJAX ────────────────────────────────────────────────────────────────
    path('ajax/recherche/', views.ajax_recherche, name='ajax_recherche'),
    path('ajax/favoris/<int:produit_id>/', views.ajax_favoris, name='ajax_favoris'),
    path('ajax/contact-vendeur/<slug:slug>/', views.ajax_contact, name='ajax_contact'),
    path('ajax/convertir-prix/', views.ajax_convertir, name='ajax_convertir'),
    path('ajax/stats-produit/<slug:slug>/', views.ajax_stats_produit, name='ajax_stats'),

    # ─── Signalement ─────────────────────────────────────────────────────────
    path('signaler/produit/<int:pk>/', views.signaler_produit, name='signaler_produit'),
    path('signaler/acteur/<int:pk>/', views.signaler_acteur, name='signaler_acteur'),

    # ─── Export / Documents ──────────────────────────────────────────────────
    path('devis/<str:reference>/pdf/', views.exporter_devis_pdf, name='devis_pdf'),
    path('commande/<str:numero>/facture/', views.exporter_facture, name='facture'),
]
