import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.urls import reverse
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
    for business_id in businesses.values_list("pk", flat=True).iterator():
        with transaction.atomic():
            business = businesses.select_for_update().filter(pk=business_id).first()
            if business is None:
                continue
            date = timezone.localtime(business.subscription_expires_at).strftime("%d/%m/%Y")
            title = "Ton essai se termine bientôt" if business.is_trial else "Ton abonnement arrive à échéance"
            Notification.objects.create(
                destinataire_id=business.owner_id, type_notif="systeme", titre=title,
                message=f"Échéance de {business.name} le {date}. Retrouve ton bilan et la formule de cette fiche.",
                url_action=reverse("business:business_progress", args=[business.pk]),
            )
            business.expiry_reminder_sent_at = now
            business.save(update_fields=["expiry_reminder_sent_at"])
            count += 1

    log.info(f"remind_expiring_businesses: {count} notification(s) envoyee(s).")
    return count


@shared_task
def notify_first_business_results():
    from django.db.models import Exists, OuterRef, Q
    from dashboard.models import Notification

    from .growth import _appointments, _paid
    from .models import BusinessProfile

    now = timezone.now()
    candidates = BusinessProfile.objects.filter(
        owner__isnull=False, is_active=True, growth_first_result_notice_at__isnull=True,
    ).annotate(
        first_sale=Exists(_paid(OuterRef("pk")).filter(confirmed_at__gte=now - timedelta(days=30))),
        first_booking=Exists(_appointments(OuterRef("pk")).filter(appointment__created_at__gte=now - timedelta(days=30))),
    ).filter(Q(first_sale=True) | Q(first_booking=True))
    count = 0
    for business in candidates.iterator():
        with transaction.atomic():
            if not BusinessProfile.objects.filter(pk=business.pk, growth_first_result_notice_at__isnull=True).update(growth_first_result_notice_at=now):
                continue
            Notification.objects.create(
                destinataire_id=business.owner_id, type_notif="systeme", titre="Ton premier résultat WhatsApp",
                message=f"{business.name} a enregistré une commande payée ou un rendez-vous confirmé. Retrouve les détails dans ton bilan.",
                url_action=reverse("business:business_progress", args=[business.pk]),
            )
            count += 1
    return count


@shared_task
def downgrade_expired_businesses():
    """
    Repasse en Gratuit les fiches dont l'essai ou l'abonnement paye est
    vraiment expire (date depassee), pour ne pas laisser les avantages Premium
    actifs indefiniment sans paiement.
    """
    from business.models import BusinessProfile

    from django.db.models import Q

    now = timezone.now()
    businesses = BusinessProfile.objects.filter(
        Q(plan=BusinessProfile.Plan.FREE, free_visibility_expires_at__lte=now)
        | (
            ~Q(plan=BusinessProfile.Plan.FREE)
            & (
                Q(subscription_expires_at__isnull=True)
                | Q(subscription_expires_at__lte=now)
            )
        )
    )

    count = 0
    for business_id in businesses.values_list("pk", flat=True).iterator():
        with transaction.atomic():
            business = businesses.select_for_update().filter(pk=business_id).first()
            if business:
                count += int(business.check_expiry())

    log.info(f"downgrade_expired_businesses: {count} fiche(s) retrogradee(s) en Gratuit.")
    return count
