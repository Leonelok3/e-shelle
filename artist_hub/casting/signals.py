"""
artist_hub/casting/signals.py
Écouteurs de signaux pour le module casting.
Réagit notamment à payment_succeeded pour passer le candidat à l'état INSCRIT.
"""
import logging
from django.dispatch import receiver
from artist_hub.payments.signals import payment_succeeded, payment_failed
from artist_hub.casting.models import Candidate, CandidateStatus

logger = logging.getLogger("artist_hub.casting")


@receiver(payment_succeeded)
def on_payment_succeeded(sender, payment, target_object=None, **kwargs):
    """
    Déclenché lorsque le paiement d'une candidature est validé avec succès.
    """
    candidate = None
    if isinstance(target_object, Candidate):
        candidate = target_object
    elif hasattr(payment, "candidate"):
        candidate = payment.candidate

    if not candidate:
        return

    logger.info(
        "CASTING_PAYMENT_SUCCESS: Validation candidature %s pour %s",
        candidate.candidate_number,
        candidate.full_name,
    )

    # Importer localement pour éviter tout cycle d'import
    from artist_hub.casting.services import finalize_candidate_registration
    finalize_candidate_registration(candidate)


@receiver(payment_failed)
def on_payment_failed(sender, payment, target_object=None, reason="", **kwargs):
    """
    Déclenché en cas d'échec du paiement.
    """
    candidate = getattr(payment, "candidate", None) or (target_object if isinstance(target_object, Candidate) else None)
    if candidate:
        logger.warning(
            "CASTING_PAYMENT_FAILED: Candidature %s - Échec paiement (%s)",
            candidate.candidate_number,
            reason,
        )
