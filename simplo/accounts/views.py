from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PrestataireProfileForm
from .models import CustomUser, PrestataireProfile


def _style_auth_form(form):
    """Applique les classes Bootstrap au formulaire d'authentification Django."""

    form.fields["username"].widget.attrs.update(
        {"class": "form-control", "placeholder": "Ex: moto_akwa_1"}
    )
    form.fields["password"].widget.attrs.update(
        {"class": "form-control", "placeholder": "Votre mot de passe"}
    )
    return form


def login_view(request):
    """Connecte un utilisateur Simplo sans passer par l'administration Django."""

    if request.user.is_authenticated:
        if request.user.role == CustomUser.Role.PRESTATAIRE:
            return redirect("simplo_accounts:prestataire_dashboard")
        return redirect("simplo_marketplace:home")

    if request.method == "POST":
        form = _style_auth_form(AuthenticationForm(request, data=request.POST))
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Connexion réussie.")
            if user.role == CustomUser.Role.PRESTATAIRE:
                return redirect("simplo_accounts:prestataire_dashboard")
            return redirect("simplo_marketplace:home")
        messages.error(request, "Identifiants incorrects.")
    else:
        form = _style_auth_form(AuthenticationForm(request))

    return render(request, "simplo/accounts/login.html", {"form": form})


def logout_view(request):
    """Déconnecte l'utilisateur Simplo et revient à la page d'accueil."""

    logout(request)
    messages.success(request, "Vous êtes déconnecté.")
    return redirect("simplo_marketplace:home")


@login_required
def toggle_status(request):
    """Permet au prestataire connecté de passer Disponible/Occupé en un clic."""

    try:
        profile = request.user.prestataire_profile
    except PrestataireProfile.DoesNotExist:
        messages.error(request, "Aucun profil prestataire n'est associé à votre compte.")
        return redirect("simplo_marketplace:home")

    if request.method == "POST":
        profile.statut = (
            PrestataireProfile.Status.OCCUPE
            if profile.statut == PrestataireProfile.Status.DISPONIBLE
            else PrestataireProfile.Status.DISPONIBLE
        )
        profile.save(update_fields=["statut", "updated_at"])
        messages.success(request, f"Votre statut est maintenant : {profile.get_statut_display()}.")

    return redirect("simplo_accounts:prestataire_dashboard")


@login_required
def prestataire_dashboard(request):
    """Espace simple où le prestataire gère sa disponibilité et ses données terrain."""

    try:
        profile = request.user.prestataire_profile
    except PrestataireProfile.DoesNotExist:
        messages.error(request, "Votre compte n'a pas encore de profil prestataire.")
        return redirect("simplo_marketplace:home")

    if request.method == "POST":
        form = PrestataireProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil prestataire a été mis à jour.")
            return redirect("simplo_accounts:prestataire_dashboard")
        messages.error(request, "Vérifiez les informations du formulaire.")
    else:
        form = PrestataireProfileForm(instance=profile)

    return render(
        request,
        "simplo/accounts/prestataire_dashboard.html",
        {
            "form": form,
            "profile": profile,
        },
    )
