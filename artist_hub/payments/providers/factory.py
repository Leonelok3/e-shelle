"""
artist_hub/payments/providers/factory.py
Usine d'instanciation des fournisseurs de paiement selon la configuration active.
"""
from typing import Optional
from .base import BasePaymentProvider
from .mock import MockProvider
from .manual_proof import ManualProofProvider
from .notchpay import NotchPayProvider
from artist_hub.conf import hub_settings

PROVIDERS_REGISTRY = {
    "mock": MockProvider,
    "manual_proof": ManualProofProvider,
    "notchpay": NotchPayProvider,
}


def get_payment_provider(provider_name: Optional[str] = None) -> BasePaymentProvider:
    """
    Retourne une instance du provider actif.
    Si non spécifié, utilise hub_settings.ACTIVE_PAYMENT_PROVIDER.
    Repli automatique sur MockProvider en cas de nom inconnu.
    """
    selected_name = (provider_name or hub_settings.ACTIVE_PAYMENT_PROVIDER or "mock").lower()
    from django.core.exceptions import ImproperlyConfigured
    if selected_name not in PROVIDERS_REGISTRY:
        raise ImproperlyConfigured("Fournisseur Artist Hub inconnu : " + selected_name)
    provider_cls = PROVIDERS_REGISTRY[selected_name]
    return provider_cls()
