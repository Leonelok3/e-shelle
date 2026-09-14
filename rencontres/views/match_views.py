from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q

from rencontres.models import Match, Like
from rencontres.utils.notifications import get_stats_notifications
from rencontres.views.profile_views import profil_requis


@profil_requis
def liste_matchs(request):
    """Liste de tous les matchs actifs."""
    profil = request.user.profil_rencontre
    notifs = get_stats_notifications(profil)

    matchs = Match.objects.filter(
        Q(profil_1=profil) | Q(profil_2=profil),
        est_actif=True
    ).select_related(
        'profil_1', 'profil_2',
        'conversation'
    ).order_by('-date_match')

    matchs_avec_info = []
    for m in matchs:
        autre = m.get_other_profil(profil)
        dernier_msg = None
        nb_non_lus = 0
        if hasattr(m, 'conversation'):
            conv = m.conversation
            dernier_msg = conv.messages.order_by('-date_envoi').first()
            nb_non_lus = conv.nb_non_lus(profil)

        matchs_avec_info.append({
            'match': m,
            'autre_profil': autre,
            'dernier_message': dernier_msg,
            'nb_non_lus': nb_non_lus,
        })

    return render(request, 'rencontres/matches.html', {
        'matchs': matchs_avec_info,
        'profil': profil,
        'notifs': notifs,
    })


@profil_requis
def detail_match(request, match_id):
    """Détail d'un match spécifique."""
    profil = request.user.profil_rencontre
    match = get_object_or_404(
        Match,
        Q(profil_1=profil) | Q(profil_2=profil),
        pk=match_id,
        est_actif=True
    )
    autre_profil = match.get_other_profil(profil)
    return render(request, 'rencontres/match_detail.html', {
        'match': match,
        'autre_profil': autre_profil,
        'profil': profil,
    })


@profil_requis
def popup_nouveau_match(request, match_id):
    """Retourne les infos du match pour la popup JavaScript."""
    profil = request.user.profil_rencontre
    match = get_object_or_404(
        Match,
        Q(profil_1=profil) | Q(profil_2=profil),
        pk=match_id
    )
    autre = match.get_other_profil(profil)
    return JsonResponse({
        'prenom': autre.prenom_affiche,
        'age': autre.age(),
        'photo': autre.photo_principale.url if autre.photo_principale else '',
        'conversation_url': f'/rencontres/messages/{match.conversation.id}/' if hasattr(match, 'conversation') else '',
        'profil_url': f'/rencontres/profil/{autre.id}/',
    })


@profil_requis
def qui_maime(request):
    """Voir qui a liké le profil (premium uniquement pour le détail)."""
    profil = request.user.profil_rencontre
    notifs = get_stats_notifications(profil)

    from rencontres.utils.access import entitlements
    can_see = entitlements(profil)['peut_voir_qui_a_like']
    from rencontres.models import Blocage
    blocked = set()
    for pair in Blocage.objects.filter(Q(bloqueur=profil) | Q(bloque=profil)).values_list('bloqueur_id', 'bloque_id'):
        blocked.update(pair)
    if can_see:
        likes_recus = Like.objects.filter(
            recepteur=profil
        ).filter(envoyeur__est_actif=True, envoyeur__user__is_active=True).exclude(envoyeur_id__in=blocked).select_related('envoyeur').order_by('-date_like')
        # Marquer comme lus
        likes_recus.filter(est_lu=False).update(est_lu=True)
    else:
        # Juste le nombre, pas les détails
        likes_recus = None

    nb_likes = Like.objects.filter(recepteur=profil, envoyeur__est_actif=True).exclude(envoyeur_id__in=blocked).count()

    return render(request, 'rencontres/qui_maime.html', {
        'profil': profil,
        'likes_recus': likes_recus,
        'nb_likes': nb_likes,
        'est_premium': can_see,
        'notifs': notifs,
    })
