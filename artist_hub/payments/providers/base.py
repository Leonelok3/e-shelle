"""
artist_hub/payments/providers/base.py
Interface abstraite pour tous les fournisseurs de paiement.
Permet d'ajouter ou de basculer de passerelle sans modifier le code métier.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from django.http import HttpRequest


@dataclass
class PaymentResult:
    """Résultat de l'initiation d'un paiement."""

    success: bool
    payment_url: Optional[str] = None
    reference: Optional[str] = None
    message: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentVerificationResult:
    """Résultat de la vérification d'un paiement côté serveur."""

    is_paid: bool
    status: str
    external_reference: str = ""
    amount: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class BasePaymentProvider(ABC):
    """Classe de base abstraite pour les connecteurs de paiement."""

    name: str = "base"

    @abstractmethod
    def initiate(self, payment, return_url: Optional[str] = None) -> PaymentResult:
        """
        Initie une transaction auprès du fournisseur.
        Retourne un PaymentResult avec l'URL de redirection ou instructions.
        """
        pass

    @abstractmethod
    def verify(self, reference: str) -> PaymentVerificationResult:
        """
        Vérifie le statut réel du paiement directement auprès de l'API serveur du fournisseur.
        Ne fait JAMAIS confiance aux données envoyées par le navigateur client.
        """
        pass

    @abstractmethod
    def handle_webhook(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Traite la requête entrante du webhook (validation de signature / payload).
        Retourne un dictionnaire normalisé contenant au moins :
        {
            'reference': str,
            'is_paid': bool,
            'status': str,
            'raw_data': dict,
            'error': str (optionnel)
        }
        """
        pass
