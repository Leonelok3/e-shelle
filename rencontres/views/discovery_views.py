import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from rencontres.models import ProfilRencontre, Like, Match, Conversation
from rencontres.forms import FiltresRechercheForm
from rencontres.utils.matching_algo import get_profils_compatibles, calculer_score_compatibilite
from rencontres.utils.notifications import get_stats_notifications, verifier_limite_likes
from rencontres.views.profile_views import profil_requis
from rencontres.utils.access import entitlements
from django.views.decorators.csrf import ensure_csrf_cookie


@profil_requis
@ensure_csrf_cookie
def decouverte(request):
    """Page principale de découverte des profils."""
    profil = request.user.profil_rencontre
    notifs = get_stats_notifications(profil)

    # Charger les premiers profils
    profils_avec_scores = get_profils_compatibles(profil, limit=10, exclude_ids=request.session.get('profils_passes', []), filters=request.session.get('filtres_rencontre', {}))
    profils_initiaux = [
        {
            'id': p.id,
            'prenom': p.prenom_affiche,
            'age': p.age(),
            'ville': p.ville,
            'pays': p.pays,
            'profession': p.profession,
            'biographie': p.biographie[:200] if p.biographie else '',
            'religion': p.get_religion_display() if p.religion else '',
            'langues': p.langues[:3] if p.langues else [],
            'est_premium': p.est_premium,
            'badge_verifie': p.badge_verifie,
            'photo': p.photo_principale.url if p.photo_principale else '',
            'score': score,
            'distance_km': dist,
        }
        for p, score, dist in profils_avec_scores
    ]

    _, likes_restants = verifier_limite_likes(profil)
    profil_visible = profil.photos.filter(est_approuvee=True).exists()

    return render(request, 'rencontres/discovery.html', {
        'profil': profil,
        'profils_json': profils_initiaux,
        'likes_restants': likes_restants,
        'profil_visible': profil_visible,
        'notifs': notifs,
    })


@profil_requis
def filtres(request):
    """Page de filtres de recherche."""
    profil = request.user.profil_rencontre

    if request.method == 'POST':
        form = FiltresRechercheForm(request.POST)
        if form.is_valid():
            # Sauvegarder les préférences dans la session
            if not entitlements(profil)['filtre_avance']:
                form.cleaned_data['niveau_etude'] = ''
            request.session['filtres_rencontre'] = form.cleaned_data
            request.session['profils_passes'] = []
            return redirect('rencontres:decouverte')
    else:
        initial = request.session.get('filtres_rencontre', {})
        form = FiltresRechercheForm(initial=initial)

    return render(request, 'rencontres/filtres.html', {
        'form': form,
        'profil': profil,
        'est_premium': entitlements(profil)['filtre_avance'],
    })


@login_required
@require_POST
@transaction.atomic
def ajax_like(request, profil_id):
    """Endpoint AJAX pour liker un profil."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'error': 'Profil requis'}, status=403)

    mon_profil = request.user.profil_rencontre

    list(ProfilRencontre.objects.select_for_update().filter(pk__in=[mon_profil.pk, profil_id]).order_by('pk'))

    recepteur = get_object_or_404(ProfilRencontre, pk=profil_id, est_actif=True)

    from rencontres.utils.access import can_interact
    if not can_interact(mon_profil, recepteur) or not recepteur.photos.filter(est_approuvee=True).exists():
        return JsonResponse({'error': 'Action impossible'}, status=403)

    # Vérifier les blocages
    if mon_profil.a_bloque(recepteur) or mon_profil.est_bloque_par(recepteur):
        return JsonResponse({'success': False, 'error': 'Action impossible'}, status=403)

    # Parser le type de like
    try:
        body = json.loads(request.body)
        type_like = body.get('type', 'like')
    except (ValueError, AttributeError, TypeError):
        return JsonResponse({'error': 'Données invalides'}, status=400)

    if type_like not in ('like', 'super_like'):
        type_like = 'like'

    if Like.objects.filter(envoyeur=mon_profil, recepteur=recepteur).exists():
        return JsonResponse({'success': True, 'est_match': False, 'likes_restants': verifier_limite_likes(mon_profil, type_like)[1]})

    # Vérifier la limite après avoir identifié l'action demandée.
    peut_liker, likes_restants = verifier_limite_likes(mon_profil, type_like=type_like)
    if not peut_liker:
        action_label = "super likes" if type_like == "super_like" else "likes"
        return JsonResponse({
            'success': False,
            'limite_atteinte': True,
            'type_like': type_like,
            'likes_restants': likes_restants,
            'message': (
                f"Vous avez utilisé vos {action_label} gratuits aujourd'hui. "
                "Revenez demain ou consultez les limites des pass Love."
            ),
        })

    # Créer ou récupérer le like
    like, created = Like.objects.get_or_create(
        envoyeur=mon_profil,
        recepteur=recepteur,
        defaults={'type_like': type_like}
    )

    # Vérifier si c'est un match (l'autre a déjà liké)
    like_retour = Like.objects.filter(envoyeur=recepteur, recepteur=mon_profil).first()
    est_match = False
    match_id = None

    if like_retour:
        # C'est un match !
        match, _ = Match.objects.get_or_create(
            profil_1=min(mon_profil, recepteur, key=lambda p: p.id),
            profil_2=max(mon_profil, recepteur, key=lambda p: p.id),
            defaults={
                'score_compatibilite': calculer_score_compatibilite(
                    mon_profil, recepteur
                )['score_total']
            }
        )
        if not match.est_actif:
            return JsonResponse({'error': 'Ce match n’est plus actif.'}, status=403)
        # Créer la conversation automatiquement
        Conversation.objects.get_or_create(match=match)
        est_match = True
        match_id = match.id

    return JsonResponse({
        'success': True,
        'est_match': est_match,
        'match_id': match_id,
        'likes_restants': max(0, likes_restants - 1) if likes_restants >= 0 else -1,
        'profil_info': {
            'prenom': recepteur.prenom_affiche,
            'photo': recepteur.photo_principale.url if recepteur.photo_principale else '',
        } if est_match else None,
    })


@login_required
@require_POST
def ajax_passer(request, profil_id):
    """Endpoint AJAX pour passer un profil (sans liker)."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'error': 'Profil requis'}, status=403)

    from rencontres.utils.access import can_interact
    target = get_object_or_404(ProfilRencontre, pk=profil_id)
    if not can_interact(request.user.profil_rencontre, target):
        return JsonResponse({'error': 'Action impossible'}, status=403)

    # On peut juste logger le passage dans la session pour éviter de re-afficher
    session_key = 'profils_passes'
    passes = request.session.get(session_key, [])
    if profil_id not in passes:
        passes.append(profil_id)
    request.session[session_key] = passes[-200:]  # Garder les 200 derniers

    return JsonResponse({'success': True})


@login_required
def ajax_charger_profils(request):
    """Endpoint AJAX pour charger plus de profils (infinite scroll)."""
    if not hasattr(request.user, 'profil_rencontre'):
        return JsonResponse({'error': 'Profil requis'}, status=403)

    mon_profil = request.user.profil_rencontre
    profils_passes = request.session.get('profils_passes', [])

    profils_avec_scores = get_profils_compatibles(
        mon_profil,
        limit=10,
        filters=request.session.get('filtres_rencontre', {}),
        exclude_ids=profils_passes
    )

    data = [
        {
            'id': p.id,
            'prenom': p.prenom_affiche,
            'age': p.age(),
            'ville': p.ville,
            'pays': p.pays,
            'profession': p.profession,
            'biographie': p.biographie[:200] if p.biographie else '',
            'religion': p.get_religion_display() if p.religion else '',
            'langues': p.langues[:3] if p.langues else [],
            'est_premium': p.est_premium,
            'badge_verifie': p.badge_verifie,
            'photo': p.photo_principale.url if p.photo_principale else '',
            'score': score,
            'distance_km': dist,
        }
        for p, score, dist in profils_avec_scores
    ]

    return JsonResponse({'profils': data, 'total': len(data)})


@profil_requis
@require_POST
def ajax_rembobiner(request):
    from rencontres.utils.access import entitlements
    if not entitlements(request.user.profil_rencontre)['peut_rembobiner']:
        return JsonResponse({'error': 'Ce pass ne comprend pas le retour au dernier profil.'}, status=403)
    passed = request.session.get('profils_passes', [])
    if not passed:
        return JsonResponse({'error': 'Aucun profil passé à retrouver.'}, status=400)
    passed.pop()
    request.session['profils_passes'] = passed
    return JsonResponse({'success': True})
