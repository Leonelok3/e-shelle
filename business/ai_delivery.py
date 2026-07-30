import urllib.parse

from django.utils import timezone

from .models import BusinessCatalogItem, BusinessProfile, ClientAIKit


MODULE_VALUE = {
    BusinessProfile.Module.RESTO: {
        "audience": "clients qui veulent commander ou réserver vite",
        "primary_action": "Commander sur WhatsApp",
        "proof": "menu clair, prix visibles, contact direct",
    },
    BusinessProfile.Module.GAZ: {
        "audience": "familles et commerces qui veulent du gaz rapidement",
        "primary_action": "Commander du gaz",
        "proof": "zone de livraison, prix, numéro fiable",
    },
    BusinessProfile.Module.PRESSING: {
        "audience": "travailleurs, familles et étudiants qui veulent gagner du temps",
        "primary_action": "Demander collecte ou livraison",
        "proof": "services, délais, prix, quartier",
    },
    BusinessProfile.Module.SANTE: {
        "audience": "clients qui cherchent un contact santé fiable",
        "primary_action": "Contacter un professionnel",
        "proof": "informations claires, contact, prudence médicale",
    },
    BusinessProfile.Module.PHARMA: {
        "audience": "clients qui cherchent un produit ou une pharmacie proche",
        "primary_action": "Demander la disponibilité",
        "proof": "stock, prix, quartier, contact",
    },
    BusinessProfile.Module.IMMOBILIER: {
        "audience": "locataires, acheteurs et investisseurs",
        "primary_action": "Planifier une visite",
        "proof": "photos, localisation, prix, statut du bien",
    },
    BusinessProfile.Module.AUTO: {
        "audience": "acheteurs qui veulent comparer avant de contacter",
        "primary_action": "Contacter le vendeur",
        "proof": "photos, prix, état, kilométrage",
    },
    BusinessProfile.Module.AGRO: {
        "audience": "acheteurs, grossistes et producteurs",
        "primary_action": "Demander un devis",
        "proof": "stock, prix, origine, livraison",
    },
    BusinessProfile.Module.SERVICES: {
        "audience": "clients qui cherchent un prestataire sérieux",
        "primary_action": "Demander un devis",
        "proof": "réalisations, zone, disponibilité",
    },
}

# Libellés reconnus dans la note du prestataire (une info par ligne, "Label: valeur").
_NOTE_LABELS = {
    "cible": "cible",
    "audience": "cible",
    "ton": "ton",
    "offre": "offre",
    "offre speciale": "offre",
    "offre spéciale": "offre",
    "contrainte": "contrainte",
    "contraintes": "contrainte",
}


def _parse_brief_note(extra_brief: str) -> dict:
    """
    Extrait cible/ton/offre/contrainte d'une note structurée du prestataire
    (une ligne "Label: valeur" par info). Les lignes non reconnues sont ignorées
    ici mais restent visibles telles quelles dans le brief (note_client).
    """
    hints = {"cible": "", "ton": "", "offre": "", "contrainte": ""}
    if not extra_brief:
        return hints
    for line in extra_brief.splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        key = _NOTE_LABELS.get(label.strip().lower())
        if key and value.strip():
            hints[key] = value.strip()
    return hints


def generate_client_ai_kit(business: BusinessProfile, user=None, extra_brief: str = "") -> ClientAIKit:
    """Crée ou met à jour un kit de livraison IA pour un client E-Shelle."""

    kit, _ = ClientAIKit.objects.get_or_create(
        business=business,
        defaults={"created_by": user if getattr(user, "is_authenticated", False) else None},
    )
    items = list(
        BusinessCatalogItem.objects.filter(business=business, is_active=True).order_by("order", "-created_at")[:8]
    )
    context = _context(business, items, extra_brief)

    kit.client_brief = _client_brief(context)
    kit.recommended_agents = _recommended_agents(context)
    kit.chatbot_prompt = _chatbot_prompt(context)
    kit.website_plan = _website_plan(context)
    kit.content_pack = _content_pack(context)
    kit.whatsapp_scripts = _whatsapp_scripts(context)
    kit.seo_plan = _seo_plan(context)
    kit.video_plan = _video_plan(context)
    kit.automation_plan = _automation_plan(context)
    kit.qa_checklist = _qa_checklist(context)
    kit.status = ClientAIKit.Status.READY
    kit.generated_at = timezone.now()
    kit.save(
        update_fields=[
            "client_brief",
            "recommended_agents",
            "chatbot_prompt",
            "website_plan",
            "content_pack",
            "whatsapp_scripts",
            "seo_plan",
            "video_plan",
            "automation_plan",
            "qa_checklist",
            "status",
            "generated_at",
            "updated_at",
        ]
    )
    return kit


def kit_summary_for_whatsapp(kit: ClientAIKit) -> str:
    business = kit.business
    public_url = business.get_absolute_url()
    return (
        f"Kit IA E-Shelle prêt pour {business.name}.\n"
        f"Offre: {business.promo_offer or business.description[:90] or 'vitrine IA + chatbot + WhatsApp'}\n"
        f"Livrables: chatbot, mini-site, contenus, WhatsApp, SEO, vidéo, automatisation.\n"
        f"Lien: {public_url}"
    )


def _context(business, items, extra_brief):
    module_info = MODULE_VALUE.get(
        business.module,
        {
            "audience": "clients locaux et prospects professionnels",
            "primary_action": "Contacter le business",
            "proof": "offre claire, lien public, WhatsApp",
        },
    )
    hints = _parse_brief_note(extra_brief)
    location = ", ".join(part for part in [business.city, business.district] if part) or "Cameroun"
    offer = (
        hints["offre"]
        or business.promo_offer
        or business.promo_headline
        or business.description[:140]
        or "une offre professionnelle"
    )
    tone = hints["ton"] or "professionnel, direct, chaleureux, adapté au Cameroun"
    catalog = [
        {
            "title": item.title,
            "type": item.get_item_type_display(),
            "price": item.formatted_price,
            "description": item.description[:160],
        }
        for item in items
    ]
    top_products = [entry["title"] for entry in catalog[:3]]
    return {
        "business": business,
        "name": business.name,
        "module": business.module,
        "module_label": business.get_module_display(),
        "location": location,
        "phone": business.phone,
        "whatsapp": business.whatsapp or business.phone,
        "offer": offer,
        "description": business.description,
        "catalog": catalog,
        "top_products": top_products,
        "extra_brief": extra_brief.strip(),
        "tone": tone,
        "constraint": hints["contrainte"],
        "audience": hints["cible"] or module_info["audience"],
        "primary_action": module_info["primary_action"],
        "proof": module_info["proof"],
    }


def _client_brief(ctx):
    return {
        "business": ctx["name"],
        "secteur": ctx["module_label"],
        "zone": ctx["location"],
        "cible": ctx["audience"],
        "promesse": ctx["offer"],
        "ton": ctx["tone"],
        "contrainte": ctx["constraint"] or "Aucune contrainte particulière renseignée.",
        "preuve": ctx["proof"],
        "action_principale": ctx["primary_action"],
        "catalogue": ctx["catalog"],
        "note_client": ctx["extra_brief"],
    }


def _recommended_agents(ctx):
    return [
        {
            "agent": "Agent Onboarding Client",
            "role": "Transformer la fiche business en brief, FAQ, scripts et plan de livraison.",
            "source": "business.ai_delivery.generate_client_ai_kit",
        },
        {
            "agent": "CentralAgentService",
            "role": "Brancher le chatbot et orienter les clients vers la fiche, WhatsApp et le catalogue.",
            "source": "e_shelle_ai.services.central_agent",
        },
        {
            "agent": "ContentWriter / AdGen",
            "role": "Produire posts, descriptions, FAQ, scripts commerciaux et scripts vidéo.",
            "source": "e_shelle_ai.services.tools.content_writer + adgen",
        },
        {
            "agent": "WhatsAppAgent",
            "role": "Préparer campagnes, relances et messages courts personnalisés.",
            "source": "whatsapp_agent",
        },
        {
            "agent": "SEOAgent",
            "role": "Produire mots-clés locaux, CTA, pages GEO et checklist référencement.",
            "source": "seo_agent",
        },
        {
            "agent": "CommercialAgent",
            "role": "Gérer prospection, scoring, relances et suivi des conversions.",
            "source": "commercial_agent",
        },
    ]


def _chatbot_prompt(ctx):
    catalog_lines = "\n".join(
        f"- {item['title']} ({item['type']}): {item['price']} - {item['description']}"
        for item in ctx["catalog"]
    ) or "- Aucun produit/service renseigné: demander le besoin puis orienter vers WhatsApp."
    constraint_line = (
        f"\n6. Contrainte du prestataire à respecter strictement: {ctx['constraint']}."
        if ctx["constraint"] else ""
    )
    return f"""Tu es le chatbot officiel de {ctx['name']} sur E-Shelle.
Secteur: {ctx['module_label']}.
Zone: {ctx['location']}.
Public cible: {ctx['audience']}.
Promesse commerciale: {ctx['offer']}.
Preuves à mettre en avant: {ctx['proof']}.

Objectifs:
1. Comprendre le besoin du client en 1 ou 2 questions maximum.
2. Recommander le produit/service le plus pertinent.
3. Donner une réponse courte, rassurante et commerciale.
4. Toujours proposer l'action suivante: {ctx['primary_action']} via WhatsApp.
5. Ne jamais inventer un prix, une disponibilité ou une condition absente du brief.{constraint_line}

Catalogue connu:
{catalog_lines}

Ton: {ctx['tone']}.
Si le client demande autre chose, collecte nom, besoin, ville/quartier et renvoie vers WhatsApp: {ctx['whatsapp']}."""


def _website_plan(ctx):
    products = ctx["top_products"]
    products_section = (
        f"Produits ou services prioritaires: {', '.join(products)}"
        if products else "Produits ou services prioritaires"
    )
    return {
        "page_type": "Mini-site IA / vitrine E-Shelle",
        "hero": {
            "h1": ctx["name"],
            "subtitle": ctx["offer"],
            "cta_primary": ctx["primary_action"],
            "cta_secondary": "Voir les produits/services",
        },
        "sections": [
            "Hero avec offre claire et bouton WhatsApp",
            products_section,
            "Pourquoi choisir ce prestataire",
            "Zone desservie et horaires",
            "FAQ rapide",
            "CTA final WhatsApp + partage",
        ],
        "assets_needed": [
            "Logo ou photo principale",
            "3 à 8 photos produits/services",
            "Numéro WhatsApp actif",
            "Prix ou fourchettes si disponibles",
        ],
        "tracking": ["vue fiche", "clic WhatsApp", "appel", "demande", "partage"],
    }


def _content_pack(ctx):
    name = ctx["name"]
    offer = ctx["offer"]
    products = ctx["top_products"]
    products_line = f" Parmi nos produits: {', '.join(products)}." if products else ""
    return {
        "facebook_post": (
            f"{name} est disponible à {ctx['location']}. {offer}.{products_line} "
            f"Contactez directement sur WhatsApp pour {ctx['primary_action'].lower()}."
        ),
        "instagram_caption": (
            f"{offer}\nDisponible: {ctx['location']}"
            + (f"\nProduits phares: {', '.join(products)}" if products else "")
            + f"\nAction rapide: {ctx['primary_action']}."
        ),
        "whatsapp_status": f"{name} - {offer}. Écrivez maintenant pour {ctx['primary_action'].lower()}.",
        "product_description_template": (
            "Mettez le besoin client en premier, puis le bénéfice, le prix si disponible, "
            "la zone et un CTA WhatsApp simple."
        ),
        "image_prompt": (
            f"Professional advertising visual for {name}, {ctx['module_label']}, Cameroon market, "
            f"showing {offer}"
            + (f", featuring {products[0]}" if products else "")
            + ", clean modern layout, premium but local, high conversion."
        ),
        "adgen_modules": ["titres", "description", "social", "tiktok", "chatbot"],
    }


def _whatsapp_scripts(ctx):
    name = ctx["name"]
    return [
        {
            "label": "Premier contact",
            "text": (
                f"Bonjour, bienvenue chez {name}. Dites-nous votre besoin et votre quartier, "
                f"on vous aide rapidement pour {ctx['primary_action'].lower()}."
            ),
        },
        {
            "label": "Relance prospect",
            "text": (
                f"Bonjour, je reviens vers vous pour {name}. {ctx['offer']}. "
                "Souhaitez-vous qu'on vous confirme les détails maintenant ?"
            ),
        },
        {
            "label": "Après demande",
            "text": (
                "Merci pour votre message. Pour finaliser, envoyez votre nom, quartier, "
                "besoin exact et heure souhaitée."
            ),
        },
        {
            "label": "Demande d'avis",
            "text": (
                f"Merci d'avoir choisi {name}. Votre avis aide d'autres clients à nous faire confiance. "
                "Pouvez-vous partager un court retour ?"
            ),
        },
    ]


def _seo_plan(ctx):
    service_slug = urllib.parse.quote(ctx["module_label"].lower().replace(" ", "-"))
    city = ctx["location"].split(",")[0].strip() or "Douala"
    products = ctx["top_products"]
    keywords = [
        f"{ctx['module_label']} {city}",
        f"{ctx['name']} {city}",
        f"{ctx['primary_action']} {city}",
        "E-Shelle Cameroun",
        "WhatsApp Business Cameroun",
    ]
    if products:
        keywords.insert(2, f"{products[0]} {city}")
    return {
        "title": f"{ctx['name']} - {ctx['module_label']} à {city}",
        "meta_description": (
            f"Découvrez {ctx['name']} sur E-Shelle: {ctx['offer']} à {ctx['location']}. "
            f"Contact rapide WhatsApp."
        )[:155],
        "keywords": keywords,
        "geo_page": f"/business/local/{urllib.parse.quote(city.lower())}/{service_slug}/",
        "schema": ["LocalBusiness", "Service", "FAQPage", "BreadcrumbList"],
        "cta": ctx["primary_action"],
    }


def _video_plan(ctx):
    products = ctx["top_products"]
    subject = products[0] if products else ctx["module_label"].lower()
    return {
        "format": "TikTok/Reels 20 secondes",
        "hook": f"Besoin de {subject} à {ctx['location']} ?",
        "scenes": [
            "Problème client en situation réelle",
            f"Apparition de {ctx['name']} et de son offre" + (f": {subject}" if products else ""),
            "Preuve: zone, prix/service, contact direct",
            f"CTA: {ctx['primary_action']} sur WhatsApp via E-Shelle",
        ],
        "voiceover": (
            f"À {ctx['location']}, {ctx['name']} vous simplifie la vie. "
            f"{ctx['offer']}. Passez par E-Shelle et contactez directement sur WhatsApp."
        ),
        "generation_status": "Script prêt. Ajouter un agent vidéo pour produire automatiquement MP4/voix off.",
    }


def _automation_plan(ctx):
    return [
        {
            "workflow": "Capture lead chatbot",
            "steps": ["Détecter besoin", "Collecter nom + quartier + téléphone", "Envoyer vers WhatsApp", "Journaliser la demande"],
        },
        {
            "workflow": "Relance WhatsApp",
            "steps": ["J+1 relance douce", "J+3 confirmation", "J+7 avis ou nouvelle offre"],
        },
        {
            "workflow": "Contenu hebdomadaire",
            "steps": ["1 post Facebook", "1 statut WhatsApp", "1 script vidéo", "1 offre promo"],
        },
        {
            "workflow": "Reporting",
            "steps": ["Compter vues", "Compter clics WhatsApp", "Calculer demandes", "Envoyer résumé au client"],
        },
    ]


def _qa_checklist(ctx):
    return [
        {"item": "La fiche business a un nom, une ville, un quartier et un WhatsApp.", "done": bool(ctx["name"] and ctx["whatsapp"])},
        {"item": "Le chatbot ne promet pas de prix ou stock non renseigné.", "done": True},
        {"item": "Le CTA WhatsApp contient un message utile.", "done": bool(ctx["whatsapp"])},
        {"item": "Le mini-site présente au moins une offre claire.", "done": bool(ctx["offer"])},
        {"item": "Le plan SEO contient ville + secteur + schéma.", "done": True},
        {"item": "Le kit contient scripts WhatsApp, contenu social et script vidéo.", "done": True},
    ]
