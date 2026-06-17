from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone

from rencontres.models import ProfilRencontre, Blocage, Signalement, PhotoProfil
from rencontres.views.profile_views import profil_requis


@profil_requis
def bloquer_profil(request, profil_id):
    """Bloquer un profil."""
    mon_profil = request.user.profil_rencontre
    profil_a_bloquer = get_object_or_404(ProfilRencontre, pk=profil_id)

    if request.method == 'POST':
        Blocage.objects.get_or_create(
            bloqueur=mon_profil,
            bloque=profil_a_bloquer,
            defaults={'raison': request.POST.get('raison', '')}
        )

        # Désactiver le match s'il existe
        from django.db.models import Q
        from rencontres.models import Match
        Match.objects.filter(
            Q(profil_1=mon_profil, profil_2=profil_a_bloquer) |
            Q(profil_1=profil_a_bloquer, profil_2=mon_profil)
        ).update(est_actif=False)

        messages.success(request, f"{profil_a_bloquer.prenom_affiche} a été bloqué(e).")
        return redirect('rencontres:decouverte')

    return render(request, 'rencontres/bloquer.html', {
        'profil_cible': profil_a_bloquer,
        'mon_profil': mon_profil,
    })


@profil_requis
def signaler_profil(request, profil_id):
    """Signaler un profil."""
    mon_profil = request.user.profil_rencontre
    profil_signale = get_object_or_404(ProfilRencontre, pk=profil_id)

    if request.method == 'POST':
        raison = request.POST.get('raison', 'autre')
        description = request.POST.get('description', '')

        try:
            Signalement.objects.create(
                signaleur=mon_profil,
                signale=profil_signale,
                raison=raison,
                description=description[:500]
            )
        except Exception:
            pass  # Signalement déjà existant pour cette raison

        # Vérifier si seuil de suspension atteint (3 signalements)
        nb_signalements = Signalement.objects.filter(
            signale=profil_signale, est_traite=False
        ).count()
        if nb_signalements >= 3:
            profil_signale.est_actif = False
            profil_signale.save(update_fields=['est_actif'])

        messages.success(
            request,
            "Signalement envoyé. Notre équipe de modération va examiner ce profil."
        )
        return redirect('rencontres:decouverte')

    return render(request, 'rencontres/signaler.html', {
        'profil_signale': profil_signale,
        'raisons': Signalement.RAISON_CHOICES,
    })


@staff_member_required
def moderation_photos(request):
    """Interface de modération des photos (staff uniquement)."""
    photos_en_attente = PhotoProfil.objects.filter(
        est_approuvee=False
    ).select_related('profil__user').order_by('date_ajout')

    if request.method == 'POST':
        photo_id = request.POST.get('photo_id')
        action = request.POST.get('action')
        photo = get_object_or_404(PhotoProfil, pk=photo_id)

        if action == 'approuver':
            photo.est_approuvee = True
            photo.save()
            profil = photo.profil
            if photo.est_principale or not profil.photo_principale:
                profil.photo_principale = photo.image
            profil.est_verifie = True
            profil.badge_verifie = True
            profil.calculer_completion()
            profil.save(update_fields=[
                'photo_principale', 'est_verifie', 'badge_verifie', 'profil_complet'
            ])
            messages.success(request, "Photo approuvée.")
        elif action == 'rejeter':
            profil = photo.profil
            if profil.photo_principale == photo.image:
                profil.photo_principale = None
                profil.save(update_fields=['photo_principale'])
            photo.delete()
            messages.success(request, "Photo rejetée et supprimée.")

        return redirect('rencontres:moderation')

    signalements = Signalement.objects.filter(
        est_traite=False
    ).select_related('signaleur', 'signale').order_by('-date_signalement')[:20]

    return render(request, 'rencontres/moderation.html', {
        'photos_en_attente': photos_en_attente,
        'signalements': signalements,
    })
