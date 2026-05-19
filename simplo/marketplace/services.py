from urllib.parse import quote

from simplo.accounts.models import PrestataireProfile


SERVICE_LABELS = {
    PrestataireProfile.ServiceType.MOTO: "Prendre une Moto",
    PrestataireProfile.ServiceType.LIVRAISON: "Faire une Livraison",
    PrestataireProfile.ServiceType.COURSES: "Faire mes Courses",
    PrestataireProfile.ServiceType.ENFANTS: "Récupérer les enfants",
}


SERVICE_ICONS = {
    PrestataireProfile.ServiceType.MOTO: "🏍️",
    PrestataireProfile.ServiceType.LIVRAISON: "📦",
    PrestataireProfile.ServiceType.COURSES: "🛒",
    PrestataireProfile.ServiceType.ENFANTS: "🏫",
}


def get_available_providers(service_type=None, ville=None, quartier=None):
    """Retourne uniquement les prestataires actifs et disponibles, filtrés par contexte."""

    queryset = PrestataireProfile.objects.filter(
        is_active=True,
        statut=PrestataireProfile.Status.DISPONIBLE,
    ).select_related("user")

    if service_type:
        queryset = queryset.filter(type_service=service_type)
    if ville:
        queryset = queryset.filter(ville__iexact=ville.strip())
    if quartier:
        queryset = queryset.filter(quartier_base__icontains=quartier.strip())

    return queryset.order_by("-is_verified", "-note", "quartier_base", "nom")


def build_whatsapp_message(provider, service_type=None, quartier=None):
    """Génère le texte WhatsApp contextuel qui déclenche l'action directe."""

    label = SERVICE_LABELS.get(service_type or provider.type_service, provider.get_type_service_display())
    quartier_ref = quartier or provider.quartier_base

    if service_type == PrestataireProfile.ServiceType.LIVRAISON:
        message = (
            f"Bonjour {provider.nom}, je viens de voir que vous êtes disponible sur Simplo "
            f"pour une livraison au quartier {quartier_ref}. Êtes-vous libre ?"
        )
    elif service_type == PrestataireProfile.ServiceType.COURSES:
        message = (
            f"Bonjour {provider.nom}, je vous contacte depuis Simplo pour faire des courses "
            f"au quartier {quartier_ref}. Êtes-vous disponible ?"
        )
    elif service_type == PrestataireProfile.ServiceType.ENFANTS:
        message = (
            f"Bonjour {provider.nom}, je vous contacte depuis Simplo pour récupérer les enfants "
            f"au quartier {quartier_ref}. Êtes-vous disponible ?"
        )
    else:
        message = (
            f"Bonjour {provider.nom}, je viens de voir que vous êtes disponible sur Simplo "
            f"pour {label.lower()} au quartier {quartier_ref}. Êtes-vous libre ?"
        )

    return message


def build_whatsapp_url(provider, service_type=None, quartier=None):
    """Construit l'URL WhatsApp sans exposer de logique de formatage dans le template."""

    return f"https://wa.me/{provider.telephone_whatsapp}?text={quote(build_whatsapp_message(provider, service_type, quartier))}"
