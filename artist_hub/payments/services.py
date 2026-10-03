"""
artist_hub/payments/services.py
Logique métier du module de paiement :
- Génération de références uniques
- Création sécurisée et atomique des transactions
- Traitement IDEMPOTENT des succès et échecs
- Émission des signaux Django
- Journalisation structurée
"""
import logging
import string
import random
from typing import Optional, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import Payment, PaymentStatus, PaymentMethod
from .signals import payment_succeeded, payment_failed
from .providers.factory import get_payment_provider
from .providers.base import PaymentVerificationResult

logger = logging.getLogger("artist_hub.payments")


def generate_payment_reference(prefix: str = "PAY") -> str:
    """
    Génère une référence unique formatée : PAY-YYYYMMDD-XXXXXX
    """
    now_str = timezone.now().strftime("%Y%m%d")
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    random_suffix = "".join(random.choices(chars, k=6))
    return f"{prefix}-{now_str}-{random_suffix}"


@transaction.atomic
def create_payment(
    amount,
    currency: str = "XAF",
    payer_name: str = "",
    payer_phone: str = "",
    payer_email: str = "",
    content_object: Optional[Any] = None,
    method: str = PaymentMethod.MTN_MOMO,
    provider_name: Optional[str] = None,
    proof_file=None,
    proof_notes: str = "",
) -> Payment:
    """
    Crée une instance de Payment liée à un objet métier via GenericForeignKey.
    """
    reference = generate_payment_reference()
    while Payment.objects.filter(reference=reference).exists():
        reference = generate_payment_reference()

    content_type = None
    object_id = None
    if content_object is not None:
        content_type = ContentType.objects.get_for_model(content_object)
        object_id = str(content_object.pk)

    from artist_hub.conf import hub_settings
    provider = provider_name or hub_settings.ACTIVE_PAYMENT_PROVIDER

    payment = Payment.objects.create(
        reference=reference,
        amount=amount,
        currency=currency,
        status=PaymentStatus.PENDING,
        provider=provider,
        method=method,
        payer_name=payer_name,
        payer_phone=payer_phone,
        payer_email=payer_email,
        content_type=content_type,
        object_id=object_id,
        proof_file=proof_file,
        proof_notes=proof_notes,
    )

    logger.info(
        "PAYMENT_CREATED: Ref=%s, Montant=%s %s, Provider=%s, Payer=%s (%s)",
        payment.reference,
        payment.amount,
        payment.currency,
        payment.provider,
        payment.payer_name,
        payment.payer_phone,
    )
    return payment


@transaction.atomic
def handle_payment_success(
    payment: Payment,
    raw_data: Optional[dict] = None,
    verified_by_user=None,
) -> bool:
    """
    Valide un paiement de manière strictement IDEMPOTENTE.
    Si le paiement a déjà été validé, l'opération est ignorée sans double effet.
    """
    locked = Payment.objects.select_for_update().get(pk=payment.pk)
    if locked.status == PaymentStatus.SUCCESS:
        payment.status = locked.status
        return False
    payment.status = locked.status
    if payment.status == PaymentStatus.SUCCESS:
        logger.warning(
            "PAYMENT_IDEMPOTENT_SKIP: Le paiement %s est déjà à SUCCESS.",
            payment.reference,
        )
        return False

    # Marquer comme succès dans le modèle
    payment.mark_as_success(raw_data=raw_data, verified_by_user=verified_by_user)

    logger.info(
        "PAYMENT_SUCCESS: Ref=%s validé avec succès. Montant=%s %s, VerifiedBy=%s",
        payment.reference,
        payment.amount,
        payment.currency,
        getattr(verified_by_user, "username", "SYSTEM/WEBHOOK"),
    )

    # Émission du signal que les autres modules (casting, ticketing) écoutent
    payment_succeeded.send(
        sender=payment.__class__,
        payment=payment,
        target_object=payment.content_object,
        raw_data=raw_data or {},
    )
    return True


@transaction.atomic
def handle_payment_failure(
    payment: Payment,
    reason: str = "",
    raw_data: Optional[dict] = None,
) -> bool:
    """
    Enregistre l'échec d'un paiement de façon idempotente.
    """
    if payment.status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED):
        return False

    payment.status = PaymentStatus.FAILED
    if raw_data:
        payment.raw_payload = raw_data
    if reason:
        payment.proof_notes = f"{payment.proof_notes}\n[Échec]: {reason}".strip()
    payment.save(update_fields=["status", "raw_payload", "proof_notes", "updated_at"])

    logger.warning(
        "PAYMENT_FAILED: Ref=%s a échoué. Raison : %s",
        payment.reference,
        reason,
    )

    payment_failed.send(
        sender=payment.__class__,
        payment=payment,
        target_object=payment.content_object,
        reason=reason,
    )
    return True


def verify_and_update_payment(reference: str, provider_name: Optional[str] = None) -> PaymentVerificationResult:
    """
    Exécute la vérification côté serveur auprès du provider et met à jour le modèle.
    Ne fait JAMAIS confiance au client navigateur.
    """
    payment = Payment.objects.filter(reference=reference).first()
    if not payment:
        return PaymentVerificationResult(
            is_paid=False,
            status="NOT_FOUND",
            error_message=f"Paiement {reference} non trouvé",
        )

    provider = get_payment_provider(provider_name or payment.provider)
    result = provider.verify(payment.reference)

    if result.is_paid:
        handle_payment_success(payment, raw_data=result.raw_data)
    elif result.status in ("FAILED", "CANCELLED", "EXPIRED"):
        handle_payment_failure(payment, reason=result.error_message, raw_data=result.raw_data)

    return result
