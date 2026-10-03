"""
Package des connecteurs de paiement pour artist_hub.
Fournit l'abstraction BasePaymentProvider et les implémentations concrètes.
"""
from .base import BasePaymentProvider, PaymentResult, PaymentVerificationResult
from .mock import MockProvider
from .manual_proof import ManualProofProvider
from .notchpay import NotchPayProvider
from .factory import get_payment_provider

__all__ = [
    "BasePaymentProvider",
    "PaymentResult",
    "PaymentVerificationResult",
    "MockProvider",
    "ManualProofProvider",
    "NotchPayProvider",
    "get_payment_provider",
]
