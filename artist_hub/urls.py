"""
artist_hub/urls.py — URLs racines de l'application artist_hub.
Découpage modulaire et respect strict du namespace 'artist_hub'.
"""
from django.urls import path, include

app_name = "artist_hub"

urlpatterns = [
    # Module de paiement partagé
    path("payments/", include("artist_hub.payments.urls", namespace="payments")),
    # Module de casting (parcours public + dashboard staff)
    path("", include("artist_hub.casting.urls", namespace="casting")),
]
