"""
utils.py — immobilier_cameroun
Fonctions utilitaires : formatage prix, slugs, images, WhatsApp, emails
"""
import urllib.parse
from django.utils.text import slugify
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


# ─────────────────────────────────────────────────────────────────
# FORMATAGE PRIX
# ─────────────────────────────────────────────────────────────────

def formater_prix(prix, devise="XAF"):
    """Retourne '150 000 XAF', '1 200 EUR', etc."""
    try:
        montant = int(prix)
        montant_formate = f"{montant:,}".replace(",", " ")
        return f"{montant_formate} {devise}"
    except (TypeError, ValueError):
        return f"{prix} {devise}"


# ─────────────────────────────────────────────────────────────────
# GÉNÉRATION SLUG UNIQUE
# ─────────────────────────────────────────────────────────────────

def generer_slug_unique(titre, model_class, instance_pk=None):
    """Génère un slug unique en ajoutant un suffixe numérique si collision."""
    base_slug = slugify(titre, allow_unicode=True)
    if not base_slug:
        base_slug = "bien"

    slug = base_slug
    compteur = 1
    qs = model_class.objects.filter(slug=slug)
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)

    while qs.exists():
        slug = f"{base_slug}-{compteur}"
        compteur += 1
        qs = model_class.objects.filter(slug=slug)
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)

    return slug


# ─────────────────────────────────────────────────────────────────
# OPTIMISATION IMAGE
# ─────────────────────────────────────────────────────────────────

def optimiser_image(image_file, max_width=1200, qualite=85):
    """
    Redimensionne et optimise une image avec Pillow.
    Retourne le fichier modifié en place.
    """
    try:
        from PIL import Image
        import io
        from django.core.files.uploadedfile import InMemoryUploadedFile

        img = Image.open(image_file)

        # Convertit RGBA → RGB si nécessaire (JPEG ne supporte pas RGBA)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Redimensionne si trop grande
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        # Sauvegarde en buffer
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=qualite, optimize=True)
        buffer.seek(0)

        return InMemoryUploadedFile(
            buffer,
            "ImageField",
            f"{image_file.name.rsplit('.', 1)[0]}.jpg",
            "image/jpeg",
            buffer.getbuffer().nbytes,
            None,
        )
    except Exception:
        # En cas d'erreur (Pillow absent, etc.), on retourne l'image originale
        return image_file


# ─────────────────────────────────────────────────────────────────
# LIEN WHATSAPP
# ─────────────────────────────────────────────────────────────────

def generer_lien_whatsapp(bien, numero=None):
    """
    Génère un lien WhatsApp prérempli avec la description du bien.
    Si aucun numéro fourni, utilise le numéro du propriétaire (profil immo).
    """
    try:
        if numero is None:
            if hasattr(bien, "whatsapp_source_phone") and bien.whatsapp_source_phone:
                numero = bien.whatsapp_source_phone
            else:
                profil = bien.proprietaire.profil_immo
                numero = profil.whatsapp or profil.telephone
    except Exception:
        numero = getattr(settings, "IMMO_WHATSAPP_CONTACT", "")

    if not numero:
        numero = ""

    # Nettoie le numéro (supprime espaces, tirets)
    numero = numero.replace(" ", "").replace("-", "")
    if numero.startswith("0"):
        numero = "237" + numero[1:]  # Préfixe Cameroun

    try:
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
    except Exception:
        domain = "e-shelle.com"

    url_bien = f"https://{domain}{bien.get_absolute_url()}"
    message = (
        f"Bonjour, je suis intéressé(e) par votre bien :\n"
        f"*{bien.titre}*\n"
        f"📍 {bien.quartier}, {bien.ville}\n"
        f"💰 {bien.prix_formate}\n"
        f"🔗 {url_bien}"
    )
    return f"https://wa.me/{numero}?text={urllib.parse.quote(message)}"


# ─────────────────────────────────────────────────────────────────
# NOTIFICATIONS EMAIL
# ─────────────────────────────────────────────────────────────────

def envoyer_email_notification(destinataire, sujet, template_html, context):
    """Envoie un email HTML de notification."""
    try:
        html_message = render_to_string(template_html, context)
        send_mail(
            subject=sujet,
            message="",  # Version texte vide — le HTML suffit
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@e-shelle.com"),
            recipient_list=[destinataire],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception:
        pass  # On ne bloque jamais l'app sur un email raté


# ─────────────────────────────────────────────────────────────────
# STATISTIQUES BIEN
# ─────────────────────────────────────────────────────────────────

def calculer_stats_bien(bien):
    """Retourne un dict de statistiques pour un bien."""
    return {
        "vues":           bien.vues,
        "favoris_count":  bien.favoris.count(),
        "demandes_count": bien.demandes_visite.count(),
        "photos_count":   bien.photos.count(),
    }


# ─────────────────────────────────────────────────────────────────
# VALIDATION TÉLÉPHONE CAMEROUNAIS
# ─────────────────────────────────────────────────────────────────

def valider_telephone_cm(numero):
    """
    Valide un numéro camerounais.
    Accepte : 6XXXXXXXX, 2XXXXXXXX, +237XXXXXXXXX, 237XXXXXXXXX
    """
    import re
    numero_clean = re.sub(r"[\s\-\.]", "", numero)
    patterns = [
        r"^\+237[62]\d{8}$",   # Format international +237
        r"^237[62]\d{8}$",     # Format international sans +
        r"^[62]\d{8}$",        # Format local 9 chiffres
        r"^0[62]\d{8}$",       # Avec 0 devant
    ]
    return any(re.match(p, numero_clean) for p in patterns)
