"""
Configuration centralisée et portable pour artist_hub.
Lit settings.ARTIST_HUB avec valeurs par défaut et support des variables d'environnement.
Aucune dépendance dure envers e_shelle.
"""
import os
from django.conf import settings

DEFAULTS = {
    # Identité & Marque
    "ARTIST_NAME": os.getenv("ARTIST_HUB_ARTIST_NAME", "GROUP OPUS"),
    "BRAND_NAME": os.getenv("ARTIST_HUB_BRAND_NAME", "OPLUS"),
    "EVENT_TITLE": os.getenv("ARTIST_HUB_EVENT_TITLE", "Douala Fashion Week 2026"),
    "EVENT_SUBTITLE": os.getenv(
        "ARTIST_HUB_EVENT_SUBTITLE",
        "Samedi 26 Décembre 2026 — Hôtel Krystal Palace Douala",
    ),
    "SLOGAN": os.getenv(
        "ARTIST_HUB_SLOGAN",
        "Recrutement officiel de mannequins pour la Fashion Week Douala",
    ),
    "LOGO_URL": os.getenv("ARTIST_HUB_LOGO_URL", ""),
    # Charte graphique (Variables CSS)
    "PRIMARY_COLOR": os.getenv("ARTIST_HUB_PRIMARY_COLOR", "#D4AF37"),  # Or luxe
    "SECONDARY_COLOR": os.getenv("ARTIST_HUB_SECONDARY_COLOR", "#0B0C10"),  # Noir profond
    "ACCENT_COLOR": os.getenv("ARTIST_HUB_ACCENT_COLOR", "#E11D48"),  # Rouge glamour
    "BG_CARD": os.getenv("ARTIST_HUB_BG_CARD", "#16181F"),
    "TEXT_LIGHT": os.getenv("ARTIST_HUB_TEXT_LIGHT", "#F3F4F6"),
    "TEXT_MUTED": os.getenv("ARTIST_HUB_TEXT_MUTED", "#9CA3AF"),
    # Monnaie & Tarifs par défaut
    "CURRENCY": os.getenv("ARTIST_HUB_CURRENCY", "XAF"),
    "FEE_CAMEROON": int(os.getenv("ARTIST_HUB_FEE_CAMEROON", "0")),
    "FEE_INTERNATIONAL": int(os.getenv("ARTIST_HUB_FEE_INTERNATIONAL", "0")),
    # Coordonnées officielles de paiement manuel / WhatsApp
    "ORANGE_MONEY_NUMBER": os.getenv("ARTIST_HUB_ORANGE_MONEY", "+237 695 487 796"),
    "MTN_MOMO_NUMBER": os.getenv("ARTIST_HUB_MTN_MOMO", "+237 675 293 836"),
    "ECOBANK_RIB": os.getenv("ARTIST_HUB_ECOBANK_RIB", "4020789949967166"),
    "CONTACT_EMAIL": os.getenv("ARTIST_HUB_CONTACT_EMAIL", "oplusproduction9@gmail.com"),
    "CONTACT_WHATSAPP": os.getenv("ARTIST_HUB_CONTACT_WHATSAPP", "+237675293836"),
    # Modules activés
    "ENABLED_MODULES": ["casting", "payments"],
    # Fournisseur de paiement actif : 'manual_proof', 'mock', 'notchpay', 'cinetpay'
    "ACTIVE_PAYMENT_PROVIDER": os.getenv("ARTIST_HUB_PAYMENT_PROVIDER", "manual_proof"),
    # Clés API Notch Pay (si activé)
    "NOTCHPAY_PUBLIC_KEY": os.getenv("NOTCHPAY_PUBLIC_KEY", ""),
    "NOTCHPAY_PRIVATE_KEY": os.getenv("NOTCHPAY_PRIVATE_KEY", ""),
    "NOTCHPAY_HASH_KEY": os.getenv("NOTCHPAY_HASH_KEY", ""),
    "NOTCHPAY_BASE_URL": os.getenv("NOTCHPAY_BASE_URL", "https://api.notchpay.co"),
    # Clés API CinetPay (si activé)
    "CINETPAY_API_KEY": os.getenv("CINETPAY_API_KEY", ""),
    "CINETPAY_SITE_ID": os.getenv("CINETPAY_SITE_ID", ""),
    "CINETPAY_SECRET_KEY": os.getenv("CINETPAY_SECRET_KEY", ""),
    # Uploads & Sécurité
    "MAX_UPLOAD_SIZE_MB": int(os.getenv("ARTIST_HUB_MAX_UPLOAD_MB", "5")),
    "MAX_PHOTOS_PER_CANDIDATE": int(os.getenv("ARTIST_HUB_MAX_PHOTOS", "4")),
    "MIN_HEIGHT_MALE": int(os.getenv("ARTIST_HUB_MIN_HEIGHT_MALE", "183")),
    "MIN_HEIGHT_FEMALE": int(os.getenv("ARTIST_HUB_MIN_HEIGHT_FEMALE", "175")),
}


def get_setting(key, default=None):
    """
    Récupère un paramètre depuis settings.ARTIST_HUB,
    puis depuis os.environ, puis depuis les valeurs DEFAULTS.
    """
    user_settings = getattr(settings, "ARTIST_HUB", {})
    if key in user_settings:
        return user_settings[key]
    env_key = f"ARTIST_HUB_{key}"
    if env_key in os.environ:
        return os.environ[env_key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    return default


class ArtistHubSettings:
    """Accès dynamique aux paramètres artist_hub."""

    def __getattr__(self, name):
        return get_setting(name)


hub_settings = ArtistHubSettings()
