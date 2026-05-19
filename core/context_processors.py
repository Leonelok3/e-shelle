from django.conf import settings


def eshelle_public_urls(request):
    """Expose les URLs publiques des modules externes dans les templates."""
    return {
        "FORMATIONS_PUBLIC_URL": getattr(settings, "FORMATIONS_PUBLIC_URL", "/formations/"),
        "BOUTIQUE_PUBLIC_URL": getattr(settings, "BOUTIQUE_PUBLIC_URL", "/boutique/"),
        "SERVICES_PUBLIC_URL": getattr(settings, "SERVICES_PUBLIC_URL", "/services/"),
        "MATHS_PUBLIC_URL": getattr(settings, "MATHS_PUBLIC_URL", "/maths/"),
        "LANGUES_PUBLIC_URL": getattr(settings, "LANGUES_PUBLIC_URL", "/langues/"),
        "ANGLAIS_PUBLIC_URL": getattr(settings, "ANGLAIS_PUBLIC_URL", "/anglais/"),
        "ALLEMAND_PUBLIC_URL": getattr(settings, "ALLEMAND_PUBLIC_URL", "/allemand/"),
        "ITALIEN_PUBLIC_URL": getattr(settings, "ITALIEN_PUBLIC_URL", "/italien/"),
        "PREP_PUBLIC_URL": getattr(settings, "PREP_PUBLIC_URL", "/prep/"),
        "IMMOBILIER_PUBLIC_URL": getattr(settings, "IMMOBILIER_PUBLIC_URL", "/immobilier/"),
        "AUTO_PUBLIC_URL": getattr(settings, "AUTO_PUBLIC_URL", "/auto/"),
        "ANNONCES_PUBLIC_URL": getattr(settings, "ANNONCES_PUBLIC_URL", "/annonces/"),
        "MARKET_PUBLIC_URL": getattr(settings, "MARKET_PUBLIC_URL", getattr(settings, "ANNONCES_PUBLIC_URL", "/annonces/")),
        "LOVE_PUBLIC_URL": getattr(settings, "LOVE_PUBLIC_URL", "/rencontres/"),
        "AGRO_PUBLIC_URL": getattr(settings, "AGRO_PUBLIC_URL", "/agro/"),
        "RESTO_PUBLIC_URL": getattr(settings, "RESTO_PUBLIC_URL", "/resto/"),
        "NJANGI_PUBLIC_URL": getattr(settings, "NJANGI_PUBLIC_URL", "/njangi/"),
        "ADGEN_PUBLIC_URL": getattr(settings, "ADGEN_PUBLIC_URL", "/pub/"),
        "GAZ_PUBLIC_URL": getattr(settings, "GAZ_PUBLIC_URL", "/gaz/"),
        "PHARMA_PUBLIC_URL": getattr(settings, "PHARMA_PUBLIC_URL", "/pharma/"),
        "PRESSING_PUBLIC_URL": getattr(settings, "PRESSING_PUBLIC_URL", "/pressing/"),
        "AI_PUBLIC_URL": getattr(settings, "AI_PUBLIC_URL", "/ai/"),
        "JOBS_PUBLIC_URL": getattr(settings, "JOBS_PUBLIC_URL", "/jobs/"),
        "TRANSPORT_PUBLIC_URL": getattr(settings, "TRANSPORT_PUBLIC_URL", "/transport/"),
        "SANTE_PUBLIC_URL": getattr(settings, "SANTE_PUBLIC_URL", "/sante/"),
        "TCHASLUCPAY_PUBLIC_URL": getattr(settings, "TCHASLUCPAY_PUBLIC_URL", "http://127.0.0.1:8001/"),
        "SIMPLO_PUBLIC_URL": getattr(settings, "SIMPLO_PUBLIC_URL", "http://127.0.0.1:8020/"),
        "MAPEX_PUBLIC_URL": getattr(settings, "MAPEX_PUBLIC_URL", "/edu/"),
    }
