from django.shortcuts import render

from simplo.accounts.models import PrestataireProfile

from .services import SERVICE_ICONS, SERVICE_LABELS, build_whatsapp_url, get_available_providers


def home(request):
    """Accueil mobile-first : quatre décisions rapides, aucune friction."""

    services = [
        {
            "type": service_type,
            "label": SERVICE_LABELS[service_type],
            "icon": SERVICE_ICONS[service_type],
        }
        for service_type in [
            PrestataireProfile.ServiceType.MOTO,
            PrestataireProfile.ServiceType.LIVRAISON,
            PrestataireProfile.ServiceType.COURSES,
            PrestataireProfile.ServiceType.ENFANTS,
        ]
    ]
    return render(request, "simplo/marketplace/home.html", {"services": services})


def provider_list(request):
    """Liste filtrée par module, ville et quartier avec liens Appel/WhatsApp."""

    service_type = request.GET.get("service") or PrestataireProfile.ServiceType.MOTO
    ville = request.GET.get("ville", "").strip()
    quartier = request.GET.get("quartier", "").strip()
    providers = get_available_providers(service_type=service_type, ville=ville, quartier=quartier)

    provider_cards = [
        {
            "profile": provider,
            "whatsapp_url": build_whatsapp_url(provider, service_type=service_type, quartier=quartier),
        }
        for provider in providers
    ]

    context = {
        "provider_cards": provider_cards,
        "service_type": service_type,
        "service_label": SERVICE_LABELS.get(service_type, "Prestataires"),
        "service_icon": SERVICE_ICONS.get(service_type, "⚡"),
        "ville": ville,
        "quartier": quartier,
        "service_choices": PrestataireProfile.ServiceType.choices,
    }
    return render(request, "simplo/marketplace/provider_list.html", context)
