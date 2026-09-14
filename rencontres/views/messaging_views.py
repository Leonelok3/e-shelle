import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from rencontres.models import Conversation, Message, Match
from rencontres.utils.notifications import (
    get_stats_notifications, verifier_limite_messages, verifier_spam
)
from rencontres.views.profile_views import profil_requis


@profil_requis
def inbox(request):
    """Boîte de réception des messages."""
    profil = request.user.profil_rencontre
    notifs = get_stats_notifications(profil)

    conversations = Conversation.objects.filter(
        match__in=Match.objects.filter(
            Q(profil_1=profil) | Q(profil_2=profil),
            est_actif=True
        ),
        est_archivee=False
    ).select_related(
        'match__profil_1', 'match__profil_2'
    ).prefetch_related('messages').order_by('-dernier_message_at')

    convs_avec_info = []
    for conv in conversations:
        autre = conv.get_other_profil(profil)
        dernier = conv.messages.order_by('-date_envoi').first()
        convs_avec_info.append({
            'conv': conv,
            'autre': autre,
            'dernier_message': dernier,
            'nb_non_lus': conv.nb_non_lus(profil),
        })

    # Matchs récents pour la barre horizontale
    matchs_recents = Match.objects.filter(
        Q(profil_1=profil) | Q(profil_2=profil),
        est_actif=True
    ).select_related('profil_1', 'profil_2').order_by('-date_match')[:10]

    matchs_info = [
        {'profil': m.get_other_profil(profil), 'match': m}
        for m in matchs_recents
    ]

    return render(request, 'rencontres/messages/inbox.html', {
        'profil': profil,
        'conversations': convs_avec_info,
        'matchs_recents': matchs_info,
        'notifs': notifs,
    })


@profil_requis
def conversation(request, conversation_id):
    """Page de conversation avec un match."""
    profil = request.user.profil_rencontre

    conv = get_object_or_404(
        Conversation,
        pk=conversation_id,
        match__in=Match.objects.filter(
            Q(profil_1=profil) | Q(profil_2=profil), est_actif=True
        )
    )
    autre_profil = conv.get_other_profil(profil)
    from rencontres.utils.access import can_interact
    if not can_interact(profil, autre_profil):
        raise Http404
    notifs = get_stats_notifications(profil)

    # Marquer les messages comme lus
    Message.objects.filter(
        conversation=conv,
        est_lu=False
    ).exclude(expediteur=profil).update(
        est_lu=True,
        date_lecture=timezone.now()
    )

    messages_list = conv.messages.filter(
        est_supprime_expediteur=False,
        est_supprime_destinataire=False
    ).select_related('expediteur').order_by('date_envoi')

    can_write = _peut_ecrire(profil, autre_profil)
    _, msgs_restants = verifier_limite_messages(profil)

    return render(request, 'rencontres/messages/conversation.html', {
        'profil': profil,
        'autre_profil': autre_profil,
        'conversation': conv,
        'messages_list': messages_list,
        'can_write': can_write,
        'msgs_restants': msgs_restants,
        'notifs': notifs,
    })


def _peut_ecrire(expediteur, destinataire):
    """Vérifie si l'expéditeur peut écrire au destinataire selon ses paramètres."""
    from rencontres.utils.access import can_interact, sync_premium
    if not can_interact(expediteur, destinataire):
        return False
    sync_premium(expediteur)
    pref = destinataire.qui_peut_ecrire
    if pref == 'tous':
        return True
    if pref == 'matchs':
        from rencontres.models import Match
        return Match.objects.filter(
            Q(profil_1=expediteur, profil_2=destinataire) |
            Q(profil_1=destinataire, profil_2=expediteur),
            est_actif=True
        ).exists()
    if pref == 'premium':
        return expediteur.est_premium
    return True


@login_required
@require_POST
@transaction.atomic
def ajax_envoyer_message(request):
    """Endpoint AJAX pour envoyer un message."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'error': 'Profil requis'}, status=403)

    profil = request.user.profil_rencontre
    from rencontres.models import ProfilRencontre
    profil = ProfilRencontre.objects.select_for_update().get(pk=profil.pk)

    try:
        body = json.loads(request.body)
        conv_id = int(body.get('conversation_id'))
        contenu = body.get('contenu', '').strip()
    except Exception:
        return JsonResponse({'error': 'Données invalides'}, status=400)

    if not contenu:
        return JsonResponse({'error': 'Message vide'}, status=400)

    if len(contenu) > 2000:
        return JsonResponse({'error': 'Message trop long (2000 caractères max)'}, status=400)

    conv = get_object_or_404(
        Conversation,
        pk=conv_id,
        match__in=Match.objects.filter(
            Q(profil_1=profil) | Q(profil_2=profil), est_actif=True
        )
    )
    autre = conv.get_other_profil(profil)

    # Vérifications
    if not _peut_ecrire(profil, autre):
        return JsonResponse({
            'success': False,
            'error': "Ce membre n'accepte pas de messages.",
        }, status=403)

    peut_envoyer, msgs_restants = verifier_limite_messages(profil)
    if not peut_envoyer:
        return JsonResponse({
            'success': False,
            'limite_atteinte': True,
            'message': "Limite de messages atteinte. Passez en premium pour des messages illimités !",
        })

    if verifier_spam(profil, conv):
        return JsonResponse({
            'success': False,
            'error': "Trop de messages envoyés en peu de temps. Attendez quelques minutes.",
        }, status=429)

    msg = Message.objects.create(
        conversation=conv,
        expediteur=profil,
        contenu=contenu,
        type_message='texte'
    )

    # Mettre à jour le timestamp de la conversation
    conv.dernier_message_at = msg.date_envoi
    conv.save(update_fields=['dernier_message_at'])

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'contenu': msg.contenu,
            'date_envoi': msg.date_envoi.isoformat(),
            'est_moi': True,
        },
        'msgs_restants': msgs_restants - 1 if msgs_restants >= 0 else -1,
    })


@login_required
@require_POST
def ajax_marquer_lu(request, conv_id):
    """Marquer les messages d'une conversation comme lus."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'error': 'Profil requis'}, status=403)

    profil = request.user.profil_rencontre
    conv = get_object_or_404(
        Conversation,
        pk=conv_id,
        match__in=Match.objects.filter(
            Q(profil_1=profil) | Q(profil_2=profil), est_actif=True
        )
    )
    from rencontres.utils.access import can_interact
    if not can_interact(profil, conv.get_other_profil(profil)):
        raise Http404
    updated = Message.objects.filter(
        conversation=conv, est_lu=False
    ).exclude(expediteur=profil).update(
        est_lu=True, date_lecture=timezone.now()
    )
    return JsonResponse({'success': True, 'marqués': updated})


@login_required
def ajax_check_notifications(request):
    """Polling AJAX pour vérifier les nouvelles notifications."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'total': 0})

    profil = request.user.profil_rencontre
    return JsonResponse(get_stats_notifications(profil))


@profil_requis
def ajax_messages(request, conv_id):
    profil = request.user.profil_rencontre
    conv = get_object_or_404(Conversation, pk=conv_id, match__in=profil.get_matchs_actifs())
    from rencontres.utils.access import can_interact
    if not can_interact(profil, conv.get_other_profil(profil)):
        raise Http404
    try:
        since = max(0, int(request.GET.get('since', 0)))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Curseur invalide'}, status=400)
    items = conv.messages.filter(pk__gt=since).exclude(
        Q(expediteur=profil, est_supprime_expediteur=True) |
        (~Q(expediteur=profil) & Q(est_supprime_destinataire=True))
    ).order_by('pk')[:100]
    return JsonResponse({'messages': [dict(id=m.pk, contenu=m.contenu,
        date_envoi=m.date_envoi.isoformat(), est_moi=m.expediteur_id == profil.pk) for m in items]})
