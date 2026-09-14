from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from rencontres.models import PlanPremiumRencontre, AbonnementRencontre, Like, Match
from rencontres.utils.notifications import get_stats_notifications
from rencontres.views.profile_views import profil_requis
from core.whatsapp import payment_request_url


def page_premium(request):
    """Page de présentation des plans premium."""
    profil = getattr(request.user, 'profil_rencontre', None)
    if profil:
        from rencontres.utils.access import sync_premium
        sync_premium(profil)
    notifs = get_stats_notifications(profil) if profil else {}

    plans = PlanPremiumRencontre.objects.all().order_by('duree_jours', 'prix_xaf_mensuel')

    abonnement_actif = AbonnementRencontre.objects.filter(
        profil=profil, est_actif=True, date_fin__gt=timezone.now()
    ).select_related('plan').first()

    from rencontres.utils.access import entitlements
    from payments.models import Transaction
    pending = Transaction.objects.filter(utilisateur=request.user, statut='en_attente',
        metadata__has_key='plan_rencontre').first() if request.user.is_authenticated else None
    contact = payment_request_url(service='E-Shelle Love', amount=f'{pending.montant} FCFA' if pending else '',
        user=request.user, details=f'Demande {pending.reference}' if pending else 'Informations sur les pass Love')
    return render(request, 'rencontres/premium.html', {
        'profil': profil,
        'plans': plans,
        'pending': pending, 'payment_contact': contact,
        'rights': entitlements(profil) if profil else {},
        'abonnement_actif': abonnement_actif,
        'notifs': notifs,
    })


@profil_requis
def souscrire_premium(request, plan):
    from django.db import transaction
    from rencontres.forms.payment_forms import SubscriptionRequestForm
    from rencontres.models import ProfilRencontre
    from rencontres.utils.access import active_subscription
    from payments.models import Transaction as PaymentTransaction
    profil = request.user.profil_rencontre
    plan_obj = get_object_or_404(PlanPremiumRencontre, nom=plan)
    current = active_subscription(profil)
    if current and current.plan_id != plan_obj.pk:
        messages.info(request, "Votre pass actuel reste valable. Vous pourrez changer de formule à son expiration.")
        return redirect('rencontres:premium')
    form = SubscriptionRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            ProfilRencontre.objects.select_for_update().get(pk=profil.pk)
            tx = PaymentTransaction.objects.filter(utilisateur=request.user, statut='en_attente',
                metadata__plan_rencontre=plan).first()
            if not tx:
                tx = PaymentTransaction.objects.create(utilisateur=request.user, type_tx='abonnement',
                    methode=form.cleaned_data['methode'], telephone=form.cleaned_data['telephone'],
                    montant=plan_obj.prix_xaf_mensuel, devise='XAF', statut='en_attente',
                    metadata={'plan_rencontre': plan, 'duree_jours': plan_obj.duree_jours,
                              'reference_client': form.cleaned_data['reference_client'], 'activation': 'manual_admin'})
                AbonnementRencontre.objects.create(profil=profil, plan=plan_obj, date_fin=timezone.now(),
                    est_actif=False, renouvellement_auto=False, payment_reference=tx.reference)
        messages.info(request, f"Demande {tx.reference} enregistrée. Votre pass démarre après vérification du paiement.")
        return redirect('rencontres:premium')
    return render(request, 'rencontres/souscrire.html', {'plan': plan_obj, 'profil': profil, 'form': form})


def activer_abonnement_premium(profil, plan_nom, duree_jours, payment_reference=''):
    """
    Appelé après confirmation de paiement pour activer l'abonnement.
    À connecter au webhook/signal de paiement.
    """
    from rencontres.utils.subscriptions import approve_subscription
    abo = AbonnementRencontre.objects.get(profil=profil, plan__nom=plan_nom, payment_reference=payment_reference)
    return approve_subscription(abo.pk)



@profil_requis
def activer_boost(request):
    """Activer un boost de profil (premium seulement)."""
    profil = request.user.profil_rencontre

    from rencontres.utils.access import entitlements
    from rencontres.models import ProfilRencontre
    from django.db import transaction
    quota = entitlements(profil)['boost_profil_par_semaine']
    if quota <= 0:
        messages.info(request, "Les boosts sont inclus dans les pass 10 et 30 jours.")
        return redirect('rencontres:premium')
    if request.method == 'POST':
        with transaction.atomic():
            profil = ProfilRencontre.objects.select_for_update().get(pk=profil.pk)
            now = timezone.now()
            uses = [stamp for stamp in profil.boost_utilisations if stamp > (now - timedelta(days=7)).isoformat()]
            if not profil.photos.filter(est_approuvee=True).exists():
                messages.info(request, "Ajoutez une photo approuvée avant d'activer un boost.")
            elif profil.boost_fin and profil.boost_fin > now:
                messages.info(request, "Votre boost est déjà actif.")
            elif len(uses) >= quota:
                messages.info(request, "Vos boosts des 7 derniers jours sont utilisés. Réessayez plus tard.")
            else:
                profil.boost_fin = now + timedelta(minutes=30)
                profil.boost_utilisations = uses + [now.isoformat()]
                profil.save(update_fields=['boost_fin', 'boost_utilisations'])
                messages.success(request, "Boost activé pour 30 minutes auprès des profils compatibles.")
        return redirect('rencontres:decouverte')
    return render(request, 'rencontres/boost.html', {'profil': profil, 'quota': quota})



@profil_requis
def ajax_stats_profil(request):
    """Statistiques du profil (premium uniquement)."""
    profil = request.user.profil_rencontre

    from rencontres.utils.access import entitlements
    if not entitlements(profil)['stats_profil']:
        return JsonResponse({'error': 'Premium requis'}, status=403)

    nb_likes = Like.objects.filter(recepteur=profil).count()
    nb_matchs = Match.objects.filter(
        __import__('django.db.models', fromlist=['Q']).Q(profil_1=profil) |
        __import__('django.db.models', fromlist=['Q']).Q(profil_2=profil)
    ).count()

    return JsonResponse({
        'vues_profil': profil.vues_profil,
        'nb_likes': nb_likes,
        'nb_matchs': nb_matchs,
        'taux_match': round((nb_matchs / nb_likes * 100) if nb_likes > 0 else 0, 1),
        'profil_complet': profil.profil_complet,
    })
