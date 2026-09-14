from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db.models import Q
from django.db.models import F
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.utils import timezone

from rencontres.models import (
    AbonnementRencontre, Conversation, ProfilRencontre, PhotoProfil, Like, Match
)
from rencontres.forms import ProfilRencontreForm, PhotoProfilForm
from rencontres.utils.matching_algo import get_profils_compatibles
from rencontres.utils.notifications import get_stats_notifications


def profil_requis(vue):
    """Décorateur : redirige vers creer_profil si pas de profil rencontre."""
    from functools import wraps

    @wraps(vue)
    @never_cache
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profil_rencontre'):
            messages.info(request, "Créez votre profil de rencontre pour continuer.")
            return redirect('rencontres:creer_profil')
        from rencontres.utils.access import sync_premium
        profil = request.user.profil_rencontre
        sync_premium(profil)
        if profil.age() < 18:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("E-Shelle Love est réservé aux personnes majeures.")
        if not profil.est_actif and request.resolver_match.url_name not in ('parametres', 'desactiver'):
            messages.info(request, "Votre profil est désactivé. Contactez l'assistance pour le réactiver.")
            return redirect('rencontres:parametres')
        return vue(request, *args, **kwargs)
    return wrapper


def accueil_rencontre(request):
    """Page d'entrée opérationnelle de l'app rencontres."""
    if not hasattr(request.user, 'profil_rencontre'):
        return render(request, 'rencontres/accueil.html')

    profil = request.user.profil_rencontre
    from rencontres.utils.access import sync_premium
    sync_premium(profil)
    if not profil.est_actif or profil.age() < 18:
        return redirect('rencontres:parametres')
    notifs = get_stats_notifications(profil)

    profils_avec_scores = get_profils_compatibles(profil, limit=6, filters=request.session.get('filtres_rencontre', {}))
    suggestions = [
        {
            'profil': p,
            'score': score,
            'distance_km': dist,
        }
        for p, score, dist in profils_avec_scores
    ]

    matchs = Match.objects.filter(
        Q(profil_1=profil) | Q(profil_2=profil),
        est_actif=True
    ).select_related('profil_1', 'profil_2').order_by('-date_match')[:6]

    matchs_recents = []
    for match in matchs:
        autre = match.get_other_profil(profil)
        conversation = getattr(match, 'conversation', None)
        dernier_message = None
        nb_non_lus = 0
        if conversation:
            dernier_message = conversation.messages.order_by('-date_envoi').first()
            nb_non_lus = conversation.nb_non_lus(profil)
        matchs_recents.append({
            'match': match,
            'autre': autre,
            'conversation': conversation,
            'dernier_message': dernier_message,
            'nb_non_lus': nb_non_lus,
        })

    abonnement_actif = AbonnementRencontre.objects.filter(
        profil=profil,
        est_actif=True,
        date_fin__gt=timezone.now()
    ).select_related('plan').first()

    abonnement_en_attente = AbonnementRencontre.objects.filter(
        profil=profil,
        est_actif=False,
        date_fin__lte=timezone.now()
    ).select_related('plan').order_by('-date_debut').first()

    conversations_count = Conversation.objects.filter(
        match__in=Match.objects.filter(
            Q(profil_1=profil) | Q(profil_2=profil),
            est_actif=True
        )
    ).count()

    return render(request, 'rencontres/accueil.html', {
        'profil': profil,
        'notifs': notifs,
        'suggestions': suggestions,
        'matchs_recents': matchs_recents,
        'abonnement_actif': abonnement_actif,
        'abonnement_en_attente': abonnement_en_attente,
        'stats': {
            'suggestions': len(suggestions),
            'matchs': matchs.count(),
            'conversations': conversations_count,
            'vues': profil.vues_profil,
        },
    })


@login_required
def creer_profil(request):
    """Création du profil de rencontre."""
    if hasattr(request.user, 'profil_rencontre'):
        return redirect('rencontres:decouverte')

    if request.method == 'POST':
        form = ProfilRencontreForm(request.POST, request.FILES)
        if form.is_valid():
            profil = form.save(commit=False)
            profil.user = request.user
            profil.save()
            profil.calculer_completion()
            messages.success(request, "Votre profil a été créé ! Bienvenue sur E-Shelle Love.")
            return redirect('rencontres:decouverte')
    else:
        # Pré-remplir avec les données du profil existant
        initial = {}
        if hasattr(request.user, 'profile'):
            p = request.user.profile
            initial['ville'] = p.ville
            initial['pays'] = p.pays
        form = ProfilRencontreForm(initial=initial)

    return render(request, 'rencontres/profile_edit.html', {
        'form': form,
        'titre': 'Créer mon profil',
        'est_creation': True,
    })


@profil_requis
def modifier_profil(request):
    """Modification du profil de rencontre."""
    profil = request.user.profil_rencontre

    if request.method == 'POST':
        form = ProfilRencontreForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            form.save()
            profil.calculer_completion()
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect('rencontres:detail_profil', pk=profil.pk)
    else:
        form = ProfilRencontreForm(instance=profil)

    return render(request, 'rencontres/profile_edit.html', {
        'form': form,
        'profil': profil,
        'titre': 'Modifier mon profil',
        'est_creation': False,
    })


@profil_requis
@ensure_csrf_cookie
def detail_profil(request, pk):
    """Détail d'un profil de rencontre."""
    mon_profil = request.user.profil_rencontre

    if pk == mon_profil.pk:
        profil = mon_profil
        est_mon_profil = True
    else:
        profil = get_object_or_404(ProfilRencontre, pk=pk, est_actif=True)
        est_mon_profil = False

        # Vérifier les blocages
        from rencontres.utils.access import can_interact
        if not can_interact(mon_profil, profil):
            raise Http404

        # Incrémenter les vues
        ProfilRencontre.objects.filter(pk=pk).update(
            vues_profil=F('vues_profil') + 1
        )

    # Statut du like
    a_like = False
    est_match = False
    if not est_mon_profil:
        a_like = Like.objects.filter(envoyeur=mon_profil, recepteur=profil).exists()
        est_match = Match.objects.filter(
            Q(profil_1=mon_profil, profil_2=profil) |
            Q(profil_1=profil, profil_2=mon_profil),
            est_actif=True
        ).exists()

    photos = profil.photos.filter(est_approuvee=True).order_by('ordre')
    photos_en_attente = profil.photos.filter(est_approuvee=False).count() if est_mon_profil else 0
    notifs = get_stats_notifications(mon_profil)
    from rencontres.utils.access import entitlements
    profile_stats = None
    if est_mon_profil and entitlements(mon_profil)['stats_profil']:
        profile_stats = {'vues': profil.vues_profil, 'likes': profil.likes_recus.count(), 'matchs': profil.get_matchs_actifs().count()}

    return render(request, 'rencontres/profile_detail.html', {
        'profil': profil,
        'est_mon_profil': est_mon_profil,
        'a_like': a_like,
        'est_match': est_match,
        'photos': photos,
        'photos_en_attente': photos_en_attente,
        'notifs': notifs,
        'profile_stats': profile_stats,
    })


@profil_requis
def gerer_photos(request):
    """Gérer les photos du profil."""
    profil = request.user.profil_rencontre
    from rencontres.utils.access import entitlements
    photos_max = entitlements(profil)['photos_max']

    if request.method == 'POST':
        if 'principale' in request.POST:
            photo = get_object_or_404(PhotoProfil, pk=request.POST.get('photo_id'), profil=profil, est_approuvee=True)
            photo.est_principale = True
            photo.save()
            return redirect('rencontres:gerer_photos')
        if 'supprimer' in request.POST:
            photo_id = request.POST.get('photo_id')
            PhotoProfil.objects.filter(pk=photo_id, profil=profil).delete()
            messages.success(request, "Photo supprimée.")
            return redirect('rencontres:gerer_photos')

        form = PhotoProfilForm(request.POST, request.FILES)
        if form.is_valid():
            nb_photos = profil.photos.count()
            if nb_photos >= photos_max:
                messages.error(
                    request,
                    f"Vous avez atteint la limite de {photos_max} photos. "
                    f"{'Passez en premium pour en ajouter plus.' if not profil.est_premium else ''}"
                )
            else:
                photo = form.save(commit=False)
                photo.profil = profil
                photo.ordre = nb_photos
                photo.est_approuvee = False
                photo.est_principale = nb_photos == 0 or form.cleaned_data.get('est_principale')
                photo.save()
                messages.success(
                    request,
                    "Photo envoyée. Elle sera visible après validation par l'administration."
                )
                profil.calculer_completion()
            return redirect('rencontres:gerer_photos')
    else:
        form = PhotoProfilForm()

    photos = profil.photos.filter(est_approuvee=True).order_by('ordre')
    photos_en_attente = profil.photos.filter(est_approuvee=False).order_by('ordre')
    return render(request, 'rencontres/gerer_photos.html', {
        'form': form,
        'photos': photos,
        'photos_en_attente': photos_en_attente,
        'profil': profil,
        'photos_max': photos_max,
        'photos_total': profil.photos.count(),
        'peut_ajouter': profil.photos.count() < photos_max,
    })


@profil_requis
def parametres_rencontre(request):
    """Paramètres de confidentialité et préférences."""
    profil = request.user.profil_rencontre

    if request.method == 'POST':
        profil.afficher_en_ligne = 'afficher_en_ligne' in request.POST
        profil.afficher_distance = 'afficher_distance' in request.POST
        profil.qui_peut_ecrire = request.POST.get('qui_peut_ecrire', 'matchs')
        if profil.qui_peut_ecrire not in ('tous', 'matchs', 'premium'):
            profil.qui_peut_ecrire = 'matchs'
        from rencontres.utils.access import entitlements
        profil.incognito = entitlements(profil)['mode_incognito'] and 'incognito' in request.POST
        profil.save(update_fields=['afficher_en_ligne', 'afficher_distance', 'qui_peut_ecrire', 'incognito'])
        messages.success(request, "Paramètres sauvegardés.")
        return redirect('rencontres:parametres')

    return render(request, 'rencontres/parametres.html', {'profil': profil})


@profil_requis
def desactiver_compte_rencontre(request):
    """Désactiver (masquer) le compte de rencontre."""
    profil = request.user.profil_rencontre

    if request.method == 'POST':
        profil.est_actif = False
        profil.save(update_fields=['est_actif'])
        messages.success(request, "Votre profil de rencontre a été désactivé.")
        return redirect('rencontres:accueil')

    return render(request, 'rencontres/desactiver.html', {'profil': profil})
