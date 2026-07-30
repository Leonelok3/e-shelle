import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

log = logging.getLogger(__name__)


@shared_task
def remind_expiring_businesses():
    """
    Notifie (dans l'app) les prestataires dont l'essai ou l'abonnement
    expire dans les 3 prochains jours, pour les inciter a payer avant la coupure.
    """
    from business.models import BusinessProfile
    from dashboard.models import Notification

    now = timezone.now()
    soon = now + timedelta(days=3)

    businesses = BusinessProfile.objects.filter(
        owner__isnull=False,
        subscription_expires_at__isnull=False,
        subscription_expires_at__gt=now,
        subscription_expires_at__lte=soon,
        expiry_reminder_sent_at__isnull=True,
    )

    count = 0
    for business in businesses:
        if business.is_trial:
            titre = "Votre essai gratuit se termine bientot"
            message = (
                f"L'essai Business gratuit de \"{business.name}\" se termine le "
                f"{business.subscription_expires_at.strftime('%d/%m/%Y')}. "
                "Passez Premium des maintenant pour garder votre visibilite renforcee !"
            )
        else:
            titre = "Votre abonnement expire bientot"
            message = (
                f"L'abonnement {business.get_plan_display()} de \"{business.name}\" expire le "
                f"{business.subscription_expires_at.strftime('%d/%m/%Y')}. "
                "Renouvelez pour ne pas perdre vos avantages Premium."
            )

        Notification.objects.create(
            destinataire=business.owner,
            type_notif="systeme",
            titre=titre,
            message=message,
            url_action="/business/plans/",
        )
        business.expiry_reminder_sent_at = now
        business.save(update_fields=["expiry_reminder_sent_at"])
        count += 1

    log.info(f"remind_expiring_businesses: {count} notification(s) envoyee(s).")
    return count


@shared_task
def downgrade_expired_businesses():
    """
    Repasse en Gratuit les fiches dont l'essai ou l'abonnement paye est
    vraiment expire (date depassee), pour ne pas laisser les avantages Premium
    actifs indefiniment sans paiement.
    """
    from business.models import BusinessProfile

    now = timezone.now()
    businesses = BusinessProfile.objects.filter(
        subscription_expires_at__isnull=False,
        subscription_expires_at__lte=now,
    ).exclude(plan=BusinessProfile.Plan.FREE)

    count = 0
    for business in businesses:
        business.plan = BusinessProfile.Plan.FREE
        business.activation_status = BusinessProfile.ActivationStatus.DEMO
        business.is_verified = False
        business.is_trial = False
        business.save(update_fields=["plan", "activation_status", "is_verified", "is_trial", "updated_at"])
        count += 1

    log.info(f"downgrade_expired_businesses: {count} fiche(s) retrogradee(s) en Gratuit.")
    return count
