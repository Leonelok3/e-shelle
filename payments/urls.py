"""payments/urls.py"""
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("payer/<int:commande_id>/",     views.initier,       name="initier"),
    path("payer/<int:commande_id>/campay/", views.payer_commande_campay, name="campay_order"),
    path("immigration97/plan/<int:plan_id>/campay/", views.payer_immigration_plan_campay, name="campay_immigration_plan"),
    path("confirmation/<int:tx_id>/",    views.confirmation,  name="confirmation"),
    path("historique/",                  views.historique,    name="historique"),
    path("webhook/",                     views.webhook,       name="webhook"),
    path("campay/webhook/",              views.campay_webhook, name="campay_webhook"),
    path("campay/return/",               views.campay_return, name="campay_return"),
    path("formation/<int:formation_id>/", views.payer_formation, name="payer_formation"),
    path("formation/<int:formation_id>/campay/", views.payer_formation_campay, name="campay_formation"),

    # Packs Premium Marketplace
    path("premium/<str:module>/",                    views.premium_marketplace, name="premium_marketplace"),
    path("premium/<str:module>/<str:plan_slug>/campay/", views.payer_premium_campay, name="campay_premium"),
    path("premium/<str:module>/<str:plan_slug>/",    views.payer_premium,       name="payer_premium"),
    path("premium/confirmation/<int:tx_id>/",        views.confirmation_premium, name="confirmation_premium"),

    # Boost annonce individuelle
    path("boost/annonce/<int:annonce_id>/<str:type_boost>/", views.booster_annonce, name="booster_annonce"),
]
