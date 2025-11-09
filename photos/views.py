from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from .forms import UploadPhotoForm
from .models import Photo
# Service d’accès (code 24h / 30j)
from billing.services import has_active_access

# code ajouteeerrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr
# photos/views.py (extrait)
from django.shortcuts import render, redirect
from django.http import FileResponse, Http404
from .permissions import require_access_or_redirect

def upload(request):
    # ... traitement upload, validation, correction ...
    # Stocke le chemin de l'aperçu dans la session (ex: request.session["last_preview_path"])
    return render(request, "photos/preview.html", {
        "preview_url": "/media/tmp/preview_123.jpg",   # exemple
        "watermarked": True,                           # info pour le template
    })

@require_access_or_redirect
def download_hd(request):
    # Récupère la version HD (post-traitement)
    path = request.session.get("last_hd_path")
    if not path:
        # fallback si rien en session
        raise Http404("Aucune photo prête pour le téléchargement.")
    return FileResponse(open(path, "rb"), as_attachment=True, filename="dv_photo_600x600.jpg")





# code ajouteeerrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr









def index(request):
    """
    Page d’accueil du module (formulaire d’upload).
    """
    form = UploadPhotoForm()
    return render(request, "photos/index.html", {"form": form})


def submit(request):
    """
    Réception du POST: crée un objet Photo, applique un traitement minimal (fallback),
    puis redirige VERS LA PAGE RESULT (pas la home).
    """
    if request.method != "POST":
        return redirect(reverse("photos:index"))

    form = UploadPhotoForm(request.POST, request.FILES)
    if not form.is_valid():
        # Réaffiche le formulaire avec les erreurs
        return render(request, "photos/index.html", {"form": form})

    photo_type = form.cleaned_data["photo_type"]
    image_file: UploadedFile = form.cleaned_data["image"]

    # 1) Créer l’objet Photo
    # Si ton modèle n’a PAS de champ 'user', on retente sans.
    try:
        photo = Photo.objects.create(
            user=request.user if request.user.is_authenticated else None,
            photo_type=photo_type,
            image=image_file,
        )
    except TypeError:
        photo = Photo.objects.create(
            photo_type=photo_type,
            image=image_file,
        )

    # 2) Traitement minimal:
    # - si 'processed_image' existe, au moins dupliquer l’original (en attendant ta vraie pipeline)
    # - width/height si présents
    try:
        if hasattr(photo, "processed_image"):
            orig_data = photo.image.read()
            photo.processed_image.save(
                photo.image.name, ContentFile(orig_data), save=False
            )

        if hasattr(photo, "width") and hasattr(photo, "height"):
            try:
                from PIL import Image
                photo.image.seek(0)
                im = Image.open(photo.image)
                photo.width, photo.height = im.size
            except Exception:
                pass

        photo.save()
    except Exception as e:
        messages.warning(request, f"Traitement simplifié appliqué (raison : {e}).")
        try:
            photo.save()
        except Exception:
            pass

    # ✅ REDIRECTION VERS LA PAGE RESULT
    return redirect(reverse("photos:result", args=[photo.pk]))


#@login_required
def result(request, pk):
    """
    Page d’aperçu AVANT/APRÈS. Affiche le filigrane tant que l’accès n’est pas actif.
    """
    photo = get_object_or_404(Photo, pk=pk)

    # Sécuriser si le champ 'user' existe
    if hasattr(photo, "user") and photo.user and photo.user != request.user:
        messages.error(request, "Accès non autorisé à cette photo.")
        return redirect(reverse("photos:index"))

    user_has_access = has_active_access(request.user)  # True si pass 24h/30j actif
    # Compat avec ton template qui teste 'has_access' et 'photo.is_paid'
    photo.is_paid = user_has_access
    ctx = {
        "photo": photo,
        "has_access": user_has_access,
    }
    return render(request, "photos/result.html", ctx)


@login_required
def download(request, pk):
    """
    Page de téléchargement — PROTÉGÉE par l’accès (code).
    """
    photo = get_object_or_404(Photo, pk=pk)

    if hasattr(photo, "user") and photo.user and photo.user != request.user:
        messages.error(request, "Accès non autorisé à cette photo.")
        return redirect(reverse("photos:index"))

    if not has_active_access(request.user):
        messages.error(request, "Accès requis pour télécharger. Achetez ou validez un code d’accès.")
        return redirect(reverse("billing:buy"))  # ou 'billing:redeem' selon ton flow

    return render(request, "photos/download.html", {"photo": photo})


def result(request, pk):
    """
    Page d’aperçu AVANT/APRÈS. Affiche le filigrane tant que l’accès n’est pas actif.
    """
    photo = get_object_or_404(Photo, pk=pk)

    # Sécuriser si le champ 'user' existe
    if hasattr(photo, "user") and photo.user and photo.user != request.user:
        messages.error(request, "Accès non autorisé à cette photo.")
        return redirect(reverse("photos:index"))

    # Vérification de l'accès de l'utilisateur
    user_has_access = has_active_access(request.user)  # True si pass 24h/30j actif
    photo.is_paid = user_has_access  # Mise à jour de l'accès à la photo

    # Si l'accès est valide, l'utilisateur peut télécharger la photo
    if user_has_access:
        messages.success(request, "✅ Accès validé. Vous pouvez télécharger votre photo.")
    
    ctx = {
        "photo": photo,
        "has_access": user_has_access,
    }
    return render(request, "photos/result.html", ctx)


@login_required
def download(request, pk):
    """
    Page de téléchargement — PROTÉGÉE par l’accès (code).
    """
    photo = get_object_or_404(Photo, pk=pk)

    if hasattr(photo, "user") and photo.user and photo.user != request.user:
        messages.error(request, "Accès non autorisé à cette photo.")
        return redirect(reverse("photos:index"))

    if not has_active_access(request.user):
        messages.error(request, "Accès requis pour télécharger. Achetez ou validez un code d’accès.")
        return redirect(reverse("billing:buy"))  # ou 'billing:redeem' selon ton flow

    return render(request, "photos/download.html", {"photo": photo})
