"""Manual payment approval, serialized and safe to retry."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rencontres.models import AbonnementRencontre, ProfilRencontre


@transaction.atomic
def approve_subscription(subscription_id):
    initial = AbonnementRencontre.objects.get(pk=subscription_id)
    profil = ProfilRencontre.objects.select_for_update().get(pk=initial.profil_id)
    abo = AbonnementRencontre.objects.select_for_update().select_related('plan').get(pk=subscription_id)
    from payments.models import Transaction
    payment = Transaction.objects.select_for_update().filter(reference=abo.payment_reference,
        utilisateur_id=profil.user_id, devise='XAF', type_tx='abonnement').first()
    if payment is None:
        raise ValueError('Aucun paiement correspondant à cette demande.')
    if payment.statut == 'succes':
        return abo
    if payment.statut not in ('initie', 'en_attente'):
        raise ValueError('Ce paiement ne peut plus être activé.')
    if payment.metadata.get('plan_rencontre') != abo.plan.nom or payment.montant <= 0:
        raise ValueError('Le paiement ne correspond pas à ce pass.')
    duration = int(payment.metadata.get('duree_jours', abo.plan.duree_jours))
    if not 1 <= duration <= 366:
        raise ValueError('Durée de pass invalide.')
    active = profil.abonnements.filter(est_actif=True, date_fin__gt=timezone.now()).exclude(pk=abo.pk).first()
    if active and active.plan_id != abo.plan_id:
        raise ValueError('Un autre pass est encore actif. Attendre son expiration avant de changer de formule.')
    end = active.date_fin if active else timezone.now()
    profil.abonnements.filter(est_actif=True).exclude(pk=abo.pk).update(est_actif=False)
    abo.est_actif = True
    abo.date_fin = end + timedelta(days=duration)
    abo.renouvellement_auto = False
    abo.save(update_fields=['est_actif', 'date_fin', 'renouvellement_auto'])
    payment.statut = 'succes'
    payment.save(update_fields=['statut', 'updated_at'])
    return abo
