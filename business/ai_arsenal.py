import urllib.parse

from django.db import models
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils import timezone

from .models import BusinessLeadEvent, BusinessProfile, UnmetSearchRequest


def arsenal_agents():
    """Catalogue operationnel des agents IA E-Shelle."""

    return [
        {
            "name": "Agent IA Central",
            "status": "operationnel",
            "level": "core",
            "url": "/chat/",
            "role": "Comprendre la recherche client, router vers le bon module et proposer une action.",
            "missing": "Encore plus de scoring automatique par intention et zone.",
        },
        {
            "name": "Agent Prospection",
            "status": "operationnel",
            "level": "sales",
            "url": "/commercial-agent/",
            "role": "Qualifier les prospects, calculer un score, recommander un plan et preparer les relances.",
            "missing": "Connexion automatique plus forte avec les demandes non satisfaites.",
        },
        {
            "name": "Agent Marketing AdGen",
            "status": "operationnel",
            "level": "marketing",
            "url": "/pub/",
            "role": "Generer titres, descriptions, posts sociaux, scripts TikTok, messages WhatsApp et reponses chatbot.",
            "missing": "Campagnes creees automatiquement depuis une fiche ou une demande client.",
        },
        {
            "name": "Agent WhatsApp",
            "status": "operationnel local",
            "level": "messaging",
            "url": "/whatsapp/campagnes/",
            "role": "Importer contacts, creer campagnes, personnaliser les messages et simuler/envoyer via Meta.",
            "missing": "Brancher Meta en production si WHATSAPP_DRY_RUN doit etre desactive.",
        },
        {
            "name": "Agent Facebook",
            "status": "pret a configurer",
            "level": "social",
            "url": "/facebook-agent/",
            "role": "Planifier, generer, publier et suivre les posts Facebook par section E-Shelle.",
            "missing": "Configurer page Meta, token permanent et validation des posts.",
        },
        {
            "name": "Agent SEO Local",
            "status": "operationnel",
            "level": "seo",
            "url": "/seo/",
            "role": "Auditer les pages, proposer pages locales, schema.org, CTA et idees d'articles.",
            "missing": "Creation automatique de pages depuis les categories les plus demandees.",
        },
        {
            "name": "Agent Audio Studio",
            "status": "prototype local",
            "level": "video",
            "url": "/audio-studio/",
            "role": "Creer voix-off de test, profils voix et musiques simples pour videos.",
            "missing": "Brancher un vrai fournisseur de clonage vocal autorise.",
        },
        {
            "name": "Agent Import Shopify",
            "status": "operationnel local",
            "level": "commerce",
            "url": "/lebelage-importer/",
            "role": "Exporter fournisseurs, comparer Shopify, calculer marge et importer en brouillon.",
            "missing": "Ajouter d'autres fournisseurs et presets par type de boutique.",
        },
        {
            "name": "Agent Livraison Client",
            "status": "operationnel",
            "level": "delivery",
            "url": "/business/dashboard/",
            "role": "Preparer un kit client: chatbot, site, SEO, contenus, WhatsApp, video et automatisations.",
            "missing": "Bouton plus visible dans chaque fiche prestataire partenaire.",
        },
        {
            "name": "Agent Fidelisation",
            "status": "ajoute",
            "level": "retention",
            "url": reverse("business:ai_arsenal") + "#agent-fidelisation",
            "role": "Detecter les clients/prestataires a relancer et proposer les messages de fidelisation.",
            "missing": "Historique client detaille par achat pour personnaliser encore plus.",
        },
        {
            "name": "Agent Opportunites",
            "status": "ajoute",
            "level": "opportunity",
            "url": reverse("business:ai_arsenal") + "#agent-opportunites",
            "role": "Transformer les demandes non satisfaites en missions de recrutement et de vente.",
            "missing": "Notification automatique partenaires/prestataires selon categorie et zone.",
        },
    ]


def arsenal_stats(days=7):
    since = timezone.now() - timezone.timedelta(days=days)
    open_statuses = [
        UnmetSearchRequest.Status.NEW,
        UnmetSearchRequest.Status.NOTIFIED,
        UnmetSearchRequest.Status.IN_PROGRESS,
        UnmetSearchRequest.Status.CONTACTED,
        UnmetSearchRequest.Status.PROVIDER_FOUND,
    ]
    return {
        "agents": len(arsenal_agents()),
        "businesses": BusinessProfile.objects.filter(is_active=True).count(),
        "premium": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "open_requests": UnmetSearchRequest.objects.filter(status__in=open_statuses).count(),
        "hot_requests": UnmetSearchRequest.objects.filter(status__in=open_statuses, lead_score__gte=80).count(),
        "recent_contacts": BusinessLeadEvent.objects.filter(
            created_at__gte=since,
            event_type__in=[
                BusinessLeadEvent.EventType.WHATSAPP,
                BusinessLeadEvent.EventType.PHONE,
                BusinessLeadEvent.EventType.ORDER,
            ],
        ).count(),
    }


def fidelisation_agent(days=14, limit=12):
    """Repere les fiches a relancer pour transformer trafic et contacts en ventes recurrentes."""

    since = timezone.now() - timezone.timedelta(days=days)
    contacted = (
        BusinessProfile.objects.filter(
            is_active=True,
            lead_events__created_at__gte=since,
            lead_events__event_type__in=[
                BusinessLeadEvent.EventType.WHATSAPP,
                BusinessLeadEvent.EventType.PHONE,
                BusinessLeadEvent.EventType.ORDER,
            ],
        )
        .annotate(
            contacts=Count("lead_events", filter=models.Q(lead_events__created_at__gte=since)),
            orders=Count("lead_events", filter=models.Q(lead_events__event_type=BusinessLeadEvent.EventType.ORDER)),
        )
        .order_by("-contacts", "-orders", "name")[:limit]
    )
    rows = []
    for business in contacted:
        rows.append(
            {
                "business": business,
                "contacts": business.contacts,
                "orders": business.orders,
                "priority": "haute" if business.contacts >= 5 else "moyenne",
                "message": (
                    f"Bonjour {business.name}, E-Shelle a detecte des contacts recents sur votre fiche. "
                    "Publiez une offre simple cette semaine et relancez les clients par WhatsApp pour transformer ces demandes."
                ),
                "action_url": business.get_absolute_url(),
                "adgen_url": _adgen_url(
                    business.name,
                    business.description or business.promo_offer or f"Offre locale {business.get_module_display()} a promouvoir.",
                    business.city,
                    "Clients locaux et anciens contacts",
                ),
            }
        )
    return rows


def opportunites_agent(limit=12):
    """Repere les zones/categories ou E-Shelle doit recruter vite."""

    open_statuses = [
        UnmetSearchRequest.Status.NEW,
        UnmetSearchRequest.Status.NOTIFIED,
        UnmetSearchRequest.Status.IN_PROGRESS,
        UnmetSearchRequest.Status.CONTACTED,
        UnmetSearchRequest.Status.PROVIDER_FOUND,
    ]
    rows = (
        UnmetSearchRequest.objects.filter(status__in=open_statuses)
        .values("module", "city", "district")
        .annotate(
            total=Count("id"),
            hot=Count("id", filter=models.Q(lead_score__gte=80)),
            value=Sum("estimated_value_xaf"),
            max_score=models.Max("lead_score"),
        )
        .order_by("-hot", "-total", "-value")[:limit]
    )
    module_labels = dict(BusinessProfile.Module.choices)
    opportunities = []
    for row in rows:
        provider_qs = BusinessProfile.objects.filter(is_active=True, module=row["module"])
        if row["city"]:
            provider_qs = provider_qs.filter(city__iexact=row["city"])
        if row["district"]:
            district_qs = provider_qs.filter(district__icontains=row["district"])
            if district_qs.exists():
                provider_qs = district_qs
        providers = provider_qs.count()
        opportunities.append(
            {
                "label": module_labels.get(row["module"], row["module"]),
                "module": row["module"],
                "city": row["city"] or "Toutes zones",
                "district": row["district"] or "",
                "total": row["total"],
                "hot": row["hot"],
                "value": row["value"] or 0,
                "max_score": row["max_score"] or 0,
                "providers": providers,
                "mission": _opportunity_mission(module_labels.get(row["module"], row["module"]), row["city"], row["district"], providers),
                "adgen_url": _adgen_url(
                    f"{module_labels.get(row['module'], row['module'])} {row['city'] or 'Cameroun'}",
                    f"Campagne pour repondre aux demandes clients: {row['total']} demande(s), zone {row['district'] or row['city'] or 'Cameroun'}.",
                    row["city"],
                    "Clients qui cherchent une solution locale",
                ),
            }
        )
    return opportunities


def _opportunity_mission(label, city, district, providers):
    zone = " / ".join(part for part in [district, city] if part) or "la zone demandee"
    if providers:
        return f"Verifier les {providers} prestataire(s) {label} a {zone}, puis les pousser a contacter les clients."
    return f"Recruter rapidement 3 a 5 prestataires {label} a {zone}, puis creer leurs fiches E-Shelle."


def _adgen_url(name, description, city="", target="Clients locaux"):
    params = {
        "nom_produit": name,
        "description": description,
        "prix": "A confirmer",
        "cible": target,
        "ville": (city or "").lower().replace("é", "e").replace("è", "e"),
        "source": "arsenal_ia",
    }
    return f"/pub/create/?{urllib.parse.urlencode(params)}"
