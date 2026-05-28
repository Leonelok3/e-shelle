import json

from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify

from .models import BusinessProfile


SEO_SERVICE_MAP = {
    "restaurants": {
        "module": BusinessProfile.Module.RESTO,
        "singular": "restaurant",
        "plural": "restaurants",
        "intent": "manger, commander un plat, trouver un maquis ou un restaurant fiable",
        "faq": [
            ("Comment trouver un bon restaurant proche de moi ?", "Choisissez votre ville ou quartier, puis contactez directement les restaurants listés sur E-Shelle."),
            ("Puis-je commander sur WhatsApp ?", "Oui. Les fiches premium mettent en avant les contacts WhatsApp quand ils sont disponibles."),
        ],
    },
    "livraison-gaz": {
        "module": BusinessProfile.Module.GAZ,
        "singular": "fournisseur de gaz",
        "plural": "fournisseurs de gaz",
        "intent": "commander une bouteille de gaz, comparer les dépôts et contacter rapidement un livreur",
        "faq": [
            ("Comment commander du gaz rapidement ?", "Ouvrez une fiche fournisseur puis utilisez le bouton WhatsApp ou commande."),
            ("E-Shelle affiche-t-il les dépôts proches ?", "Oui, les pages locales priorisent la ville et les quartiers renseignés."),
        ],
    },
    "pressing": {
        "module": BusinessProfile.Module.PRESSING,
        "singular": "pressing",
        "plural": "pressings",
        "intent": "trouver un pressing, nettoyer des vêtements, demander une collecte ou livraison",
        "faq": [
            ("Comment contacter un pressing ?", "Les fiches affichent les boutons de contact, WhatsApp ou appel quand ils sont disponibles."),
            ("Puis-je chercher par quartier ?", "Oui. E-Shelle utilise les villes et quartiers des prestataires pour filtrer les résultats."),
        ],
    },
    "pharmacies": {
        "module": BusinessProfile.Module.SANTE,
        "singular": "pharmacie ou service santé",
        "plural": "pharmacies et services santé",
        "intent": "trouver une pharmacie, un produit santé ou un professionnel proche",
        "faq": [
            ("Les pharmacies peuvent-elles être contactées directement ?", "Oui, les prestataires renseignés peuvent être contactés depuis leur fiche."),
            ("Les résultats sont-ils locaux ?", "Oui, les pages sont construites par ville et peuvent être enrichies par quartier."),
        ],
    },
    "boutiques": {
        "module": BusinessProfile.Module.BOUTIQUE,
        "singular": "boutique",
        "plural": "boutiques",
        "intent": "acheter des produits, découvrir des boutiques et contacter des vendeurs",
        "faq": [
            ("Comment acheter un produit ?", "Ouvrez la fiche du vendeur ou demandez à E-Shelle AI de vous orienter."),
            ("Les boutiques premium sont-elles mises en avant ?", "Oui, les abonnements Business et Premium améliorent la visibilité."),
        ],
    },
    "agro": {
        "module": BusinessProfile.Module.AGRO,
        "singular": "acteur agro",
        "plural": "acteurs agro",
        "intent": "trouver des produits agricoles, producteurs, grossistes ou acheteurs",
        "faq": [
            ("Puis-je demander un devis agro ?", "Oui, contactez les acteurs listés ou passez par E-Shelle AI."),
            ("E-Shelle couvre-t-il le B2B ?", "Oui, la plateforme vise les usages B2B et B2C selon les secteurs."),
        ],
    },
    "immobilier": {
        "module": BusinessProfile.Module.IMMOBILIER,
        "singular": "prestataire immobilier",
        "plural": "prestataires immobiliers",
        "intent": "chercher un terrain, une maison, un appartement ou un service immobilier",
        "faq": [
            ("Comment trouver un bien immobilier ?", "Utilisez les pages locales ou demandez à E-Shelle AI avec votre ville/quartier."),
            ("Puis-je contacter directement un prestataire ?", "Oui, les fiches business affichent les actions disponibles."),
        ],
    },
    "emplois": {
        "module": BusinessProfile.Module.JOBS,
        "singular": "opportunité emploi",
        "plural": "opportunités emploi",
        "intent": "chercher un job, stage, mission ou recruteur local",
        "faq": [
            ("E-Shelle affiche-t-il les jobs locaux ?", "Oui, les fiches emploi peuvent être organisées par ville."),
            ("Comment postuler ?", "Ouvrez la fiche ou utilisez l'action proposée par le prestataire."),
        ],
    },
    "artisans": {
        "module": "services",
        "singular": "artisan ou technicien",
        "plural": "artisans et techniciens",
        "intent": "trouver un plombier, maçon, carreleur, électricien ou technicien fiable",
        "faq": [
            ("Puis-je contacter directement un artisan ?", "Oui, les profils référencés affichent des actions de contact rapide."),
            ("Les artisans Premium sont-ils priorisés ?", "Oui, les fiches Business et Premium gagnent en visibilité locale."),
        ],
    },
}


def geo_index(request):
    cities = _available_cities()
    services = SEO_SERVICE_MAP
    popular_pages = []
    for city in cities[:8]:
        for service_slug, service in services.items():
            count = _business_qs(city["slug"], service_slug).count()
            if count:
                popular_pages.append({"city": city, "service_slug": service_slug, "service": service, "count": count})
    return render(
        request,
        "business/seo_geo_index.html",
        {
            "cities": cities,
            "services": services,
            "popular_pages": popular_pages[:24],
            "schema_json": json.dumps(_website_schema(request), ensure_ascii=False),
        },
    )


def geo_landing(request, city_slug, service_slug):
    service = SEO_SERVICE_MAP.get(service_slug)
    if not service:
        raise Http404("Service SEO introuvable")

    city_name = _city_name_from_slug(city_slug)
    qs = _business_qs(city_slug, service_slug)
    districts = list(
        qs.exclude(district="")
        .values("district")
        .annotate(total=Count("id"))
        .order_by("-total", "district")[:16]
    )
    premium_businesses = qs.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM])
    related_pages = _related_pages(city_slug, service_slug)

    title = f"{service['plural'].capitalize()} à {city_name} - E-Shelle"
    description = (
        f"Trouvez les meilleurs {service['plural']} à {city_name} sur E-Shelle. "
        f"Comparez les prestataires, contactez-les rapidement et découvrez les offres Premium/Business."
    )
    schema = _local_page_schema(request, city_name, service_slug, service, qs[:12])

    return render(
        request,
        "business/seo_geo_landing.html",
        {
            "city_slug": city_slug,
            "city_name": city_name,
            "service_slug": service_slug,
            "service": service,
            "businesses": qs[:24],
            "districts": districts,
            "premium_count": premium_businesses.count(),
            "related_pages": related_pages,
            "seo_title": title,
            "seo_description": description,
            "schema_json": json.dumps(schema, ensure_ascii=False),
        },
    )


def _business_qs(city_slug, service_slug):
    service = SEO_SERVICE_MAP[service_slug]
    city_filter = Q(city__iexact=city_slug.replace("-", " ")) | Q(city__iexact=_city_name_from_slug(city_slug))
    return (
        BusinessProfile.objects.filter(is_active=True, module=service["module"])
        .filter(city_filter)
        .order_by("-plan", "-boost_expires_at", "-leads_count", "-views_count", "name")
    )


def _available_cities():
    rows = (
        BusinessProfile.objects.filter(is_active=True)
        .exclude(city="")
        .values("city")
        .annotate(total=Count("id"))
        .order_by("-total", "city")
    )
    return [{"name": row["city"], "slug": slugify(row["city"]), "total": row["total"]} for row in rows]


def _city_name_from_slug(city_slug):
    match = BusinessProfile.objects.filter(city__iexact=city_slug.replace("-", " ")).values_list("city", flat=True).first()
    return match or city_slug.replace("-", " ").title()


def _related_pages(city_slug, current_service_slug):
    pages = []
    for slug, service in SEO_SERVICE_MAP.items():
        if slug == current_service_slug:
            continue
        count = _business_qs(city_slug, slug).count()
        if count:
            pages.append({"slug": slug, "service": service, "count": count})
    return pages[:8]


def _absolute_url(request, path):
    return request.build_absolute_uri(path)


def _website_schema(request):
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "E-Shelle",
        "url": request.build_absolute_uri("/"),
        "potentialAction": {
            "@type": "SearchAction",
            "target": request.build_absolute_uri("/chat/?q={search_term_string}"),
            "query-input": "required name=search_term_string",
        },
    }


def _local_page_schema(request, city_name, service_slug, service, businesses):
    item_list = []
    for index, business in enumerate(businesses, start=1):
        item_list.append(
            {
                "@type": "ListItem",
                "position": index,
                "item": {
                    "@type": "LocalBusiness",
                    "name": business.name,
                    "description": business.description or business.promo_offer or f"{service['singular']} à {city_name}",
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": business.city or city_name,
                        "addressRegion": business.district,
                        "addressCountry": "CM",
                    },
                    "telephone": business.phone or business.whatsapp,
                    "url": _absolute_url(request, reverse("business:go_business", args=[business.id, "detail"])),
                },
            }
        )
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": f"{service['plural'].capitalize()} à {city_name}",
                "description": f"Page locale E-Shelle pour {service['intent']} à {city_name}.",
                "url": request.build_absolute_uri(),
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": request.build_absolute_uri("/")},
                    {"@type": "ListItem", "position": 2, "name": "Local", "item": _absolute_url(request, reverse("business:geo_index"))},
                    {"@type": "ListItem", "position": 3, "name": city_name, "item": request.build_absolute_uri()},
                ],
            },
            {
                "@type": "ItemList",
                "name": f"Meilleurs {service['plural']} à {city_name}",
                "itemListElement": item_list,
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {"@type": "Answer", "text": answer},
                    }
                    for question, answer in service["faq"]
                ],
            },
        ],
    }
