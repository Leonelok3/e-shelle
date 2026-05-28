from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DemandeTravauxForm, ProfilArtisanForm, RechercheArtisanForm
from .models import DemandeTravaux, MetierArtisan, ProfilArtisan, VilleArtisan


def accueil(request):
    form = RechercheArtisanForm(request.GET or None)
    artisans = (
        ProfilArtisan.objects.filter(is_active=True)
        .select_related("ville", "user")
        .prefetch_related("metiers", "realisations")
    )
    if form.is_valid():
        data = form.cleaned_data
        if data.get("q"):
            q = data["q"]
            artisans = artisans.filter(
                Q(nom_public__icontains=q)
                | Q(description__icontains=q)
                | Q(quartier__icontains=q)
                | Q(metiers__nom__icontains=q)
            ).distinct()
        if data.get("ville"):
            artisans = artisans.filter(ville=data["ville"])
        if data.get("metier"):
            artisans = artisans.filter(metiers=data["metier"])
        if data.get("urgence"):
            artisans = artisans.filter(disponible_urgence=True)

    metiers = MetierArtisan.objects.filter(active=True)
    villes = VilleArtisan.objects.filter(active=True)
    stats = {
        "artisans": ProfilArtisan.objects.filter(is_active=True).count(),
        "metiers": metiers.count(),
        "villes": villes.count(),
        "urgences": ProfilArtisan.objects.filter(is_active=True, disponible_urgence=True).count(),
    }
    return render(request, "artisans/accueil.html", {
        "form": form,
        "artisans": artisans,
        "metiers": metiers,
        "villes": villes,
        "stats": stats,
    })


def detail_artisan(request, slug):
    artisan = get_object_or_404(
        ProfilArtisan.objects.select_related("ville", "user").prefetch_related("metiers", "realisations"),
        slug=slug,
        is_active=True,
    )
    ProfilArtisan.objects.filter(pk=artisan.pk).update(vues=artisan.vues + 1)
    similaires = (
        ProfilArtisan.objects.filter(is_active=True, ville=artisan.ville, metiers__in=artisan.metiers.all())
        .exclude(pk=artisan.pk)
        .distinct()
        .select_related("ville")
        .prefetch_related("metiers")[:4]
    )
    return render(request, "artisans/detail.html", {
        "artisan": artisan,
        "realisations": artisan.realisations.all(),
        "similaires": similaires,
    })


def demande_travaux(request):
    form = DemandeTravauxForm(request.POST or None)
    demandes = DemandeTravaux.objects.filter(is_active=True).select_related("ville", "metier")[:8]
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Votre demande a été publiée. Les prestataires peuvent vous contacter.")
        return redirect("artisans:demande_travaux")
    return render(request, "artisans/demande.html", {"form": form, "demandes": demandes})


@login_required
def espace_artisan(request):
    profil = ProfilArtisan.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = ProfilArtisanForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            profil = form.save(commit=False)
            profil.user = request.user
            profil.is_active = True
            profil.save()
            form.save_m2m()
            messages.success(request, "Votre profil artisan est à jour.")
            return redirect("artisans:espace_artisan")
    else:
        form = ProfilArtisanForm(instance=profil)
    return render(request, "artisans/espace.html", {"form": form, "profil": profil})
