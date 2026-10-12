import urllib.parse

from django.utils import timezone
from django.utils.translation import override

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
    "tone": "ton",
    "offre": "offre",
    "offer": "offre",
    "offre speciale": "offre",
    "offre spéciale": "offre",
    "contrainte": "contrainte",
    "constraint": "contrainte",
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
    french_context = _context(business, items, extra_brief, language="fr")
    english_context = _context(business, items, extra_brief, language="en")
    french_content = _kit_payload(french_context)
    kit.client_brief = french_content["client_brief"]
    kit.recommended_agents = french_content["recommended_agents"]
    kit.chatbot_prompt = french_content["chatbot_prompt"]
    kit.website_plan = french_content["website_plan"]
    kit.content_pack = french_content["content_pack"]
    kit.whatsapp_scripts = french_content["whatsapp_scripts"]
    kit.seo_plan = french_content["seo_plan"]
    kit.video_plan = french_content["video_plan"]
    kit.automation_plan = french_content["automation_plan"]
    kit.qa_checklist = french_content["qa_checklist"]
    kit.content_en = _kit_payload(english_context)
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
            "content_en",
            "status",
            "generated_at",
            "updated_at",
        ]
    )
    return kit



def _kit_payload(ctx):
    return {
        "client_brief": _client_brief(ctx),
        "recommended_agents": _recommended_agents(ctx),
        "chatbot_prompt": _chatbot_prompt(ctx),
        "website_plan": _website_plan(ctx),
        "content_pack": _content_pack(ctx),
        "whatsapp_scripts": _whatsapp_scripts(ctx),
        "seo_plan": _seo_plan(ctx),
        "video_plan": _video_plan(ctx),
        "automation_plan": _automation_plan(ctx),
        "qa_checklist": _qa_checklist(ctx),
    }


def ensure_english_kit_content(kit):
    if not kit.generated_at or kit.content_en:
        return kit.content_en
    items = list(BusinessCatalogItem.objects.filter(business=kit.business, is_active=True).order_by("order", "-created_at")[:8])
    extra_brief = (kit.client_brief or {}).get("note_client", "")
    context = _context(kit.business, items, extra_brief, language="en")
    kit.content_en = _kit_payload(context)
    kit.save(update_fields=["content_en", "updated_at"])
    return kit.content_en

def kit_summary_for_whatsapp(kit: ClientAIKit, language="fr") -> str:
    business = kit.business
    public_url = business.get_absolute_url()
    if language == "en":
        offer = ((kit.content_en or {}).get("client_brief") or {}).get("promesse") or business.display_promo_offer or business.display_description[:90] or "AI showcase + chatbot + WhatsApp"
        return f"""E-Shelle AI kit ready for {business.display_name}.
Offer: {offer}
Deliverables: chatbot, mini-site, content, WhatsApp, SEO, video and automation.
Link: {public_url}"""
    offer = business.promo_offer or business.description[:90] or "vitrine IA + chatbot + WhatsApp"
    return f"""Kit IA E-Shelle prêt pour {business.display_name}.
Offre: {offer}
Livrables: chatbot, mini-site, contenus, WhatsApp, SEO, vidéo, automatisation.
Lien: {public_url}"""


def _context(business, items, extra_brief, language="fr"):
    is_english = language == "en"
    module_values = {
        BusinessProfile.Module.RESTO: ("restaurant customers seeking quick ordering or reservations", "Order on WhatsApp", "clear menu, visible prices, direct contact"),
        BusinessProfile.Module.GAZ: ("families and businesses that need gas quickly", "Order gas", "delivery area, prices, reliable phone"),
        BusinessProfile.Module.PRESSING: ("workers, families and students looking to save time", "Request pickup or delivery", "services, timing, prices, neighborhood"),
        BusinessProfile.Module.SANTE: ("customers looking for a reliable health contact", "Contact a health professional", "clear information, contact details, medical caution"),
        BusinessProfile.Module.PHARMA: ("customers looking for a nearby pharmacy or product", "Check product availability", "stock, prices, neighborhood, contact"),
        BusinessProfile.Module.IMMOBILIER: ("renters, buyers and investors", "Schedule a viewing", "photos, location, price, property status"),
        BusinessProfile.Module.AUTO: ("buyers comparing vehicles before contacting a seller", "Contact the seller", "photos, price, condition, mileage"),
        BusinessProfile.Module.AGRO: ("buyers, wholesalers and producers", "Request a quote", "stock, price, origin, delivery"),
        BusinessProfile.Module.SERVICES: ("customers looking for a reliable provider", "Request a quote", "work samples, service area, availability"),
    }
    if is_english:
        audience, primary_action, proof = module_values.get(business.module, ("local customers and professional prospects", "Contact the business", "clear offer, public link, WhatsApp"))
        module_label = {
            "resto": "Restaurant", "gaz": "Gas", "pressing": "Laundry", "sante": "Health",
            "pharma": "Pharmacy", "immobilier": "Real estate", "auto": "Automotive",
            "agro": "Agriculture", "services": "Services", "formation": "Learning",
            "boutique": "Store", "market": "Marketplace", "transport": "Transport",
        }.get(business.module, business.get_module_display())
        name = business.name_en or business.name
        description = business.description_en or business.description
        offer = business.promo_offer_en or business.promo_offer or business.promo_headline_en or business.promo_headline or description[:140] or "a professional offer"
        location = ", ".join(part for part in [business.city, business.district] if part) or "Cameroon"
    else:
        module_info = MODULE_VALUE.get(business.module, {"audience": "clients locaux et prospects professionnels", "primary_action": "Contacter le business", "proof": "offre claire, lien public, WhatsApp"})
        audience, primary_action, proof = module_info["audience"], module_info["primary_action"], module_info["proof"]
        module_label = business.get_module_display()
        name = business.name
        description = business.description
        offer = business.promo_offer or business.promo_headline or description[:140] or "une offre professionnelle"
        location = ", ".join(part for part in [business.city, business.district] if part) or "Cameroun"
    hints = _parse_brief_note(extra_brief)
    catalog = []
    with override(language):
        for item in items:
            catalog.append({
                "title": item.display_title,
                "type": item.display_item_type,
                "price": item.formatted_price,
                "description": item.display_description[:160],
            })
    top_products = [entry["title"] for entry in catalog[:3]]
    return {
        "business": business, "name": name, "module": business.module, "module_label": module_label,
        "location": location, "phone": business.phone, "whatsapp": business.whatsapp or business.phone,
        "offer": hints["offre"] or offer, "description": description, "catalog": catalog,
        "top_products": top_products, "extra_brief": extra_brief.strip(),
        "tone": hints["ton"] or ("professional, direct, warm and tailored to Cameroon" if is_english else "professionnel, direct, chaleureux, adapté au Cameroun"),
        "constraint": hints["contrainte"], "audience": hints["cible"] or audience,
        "primary_action": primary_action, "proof": proof, "language": language,
        "display_headline": (business.promo_headline_en or business.promo_headline) if is_english else business.promo_headline,
    }


def _client_brief(ctx):
    if ctx["language"] == "en":
        return {"business": ctx["name"], "secteur": ctx["module_label"], "zone": ctx["location"], "cible": ctx["audience"], "promesse": ctx["offer"], "ton": ctx["tone"], "contrainte": ctx["constraint"] or "No special constraint provided.", "preuve": ctx["proof"], "action_principale": ctx["primary_action"], "catalogue": ctx["catalog"], "note_client": ctx["extra_brief"]}
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
    if ctx["language"] == "en":
        return [
            {"agent": "Client Onboarding Agent", "role": "Turn the business profile into a brief, FAQ, scripts and delivery plan.", "source": "business.ai_delivery.generate_client_ai_kit"},
            {"agent": "CentralAgentService", "role": "Connect the chatbot and direct customers to the profile, WhatsApp and catalogue.", "source": "e_shelle_ai.services.central_agent"},
            {"agent": "ContentWriter / AdGen", "role": "Create posts, descriptions, FAQs, sales scripts and video scripts.", "source": "e_shelle_ai.services.tools.content_writer + adgen"},
            {"agent": "WhatsAppAgent", "role": "Prepare campaigns, follow-ups and personalized short messages.", "source": "whatsapp_agent"},
            {"agent": "SEOAgent", "role": "Create local keywords, calls to action, GEO pages and an SEO checklist.", "source": "seo_agent"},
            {"agent": "CommercialAgent", "role": "Manage outreach, lead scoring, follow-ups and conversion tracking.", "source": "commercial_agent"},
        ]
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
    if ctx["language"] == "en":
        catalog_lines = "\n".join(f"- {item['title']} ({item['type']}): {item['price']} - {item['description']}" for item in ctx["catalog"]) or "- No products or services listed: ask what the customer needs, then direct them to WhatsApp."
        constraint = f"\n6. Strictly respect this provider constraint: {ctx['constraint']}." if ctx["constraint"] else ""
        return f"""You are the official E-Shelle chatbot for {ctx['name']}.\nIndustry: {ctx['module_label']}.\nArea: {ctx['location']}.\nTarget audience: {ctx['audience']}.\nOffer: {ctx['offer']}.\nProof points: {ctx['proof']}.\n\nGoals:\n1. Understand the customer in no more than one or two questions.\n2. Recommend the most relevant product or service.\n3. Keep replies brief, reassuring and helpful.\n4. Always suggest this next step: {ctx['primary_action']} through WhatsApp.\n5. Never invent a price, availability or condition missing from the brief.{constraint}\n\nKnown catalogue:\n{catalog_lines}\n\nTone: {ctx['tone']}.\nIf the customer asks for something else, collect their name, need, city or neighborhood and direct them to WhatsApp: {ctx['whatsapp']}."""
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
    if ctx["language"] == "en":
        products = ctx["top_products"]
        products_section = f"Priority products or services: {', '.join(products)}" if products else "Priority products or services"
        return {"page_type": "E-Shelle AI mini-site / business profile", "hero": {"h1": ctx["name"], "subtitle": ctx["offer"], "cta_primary": ctx["primary_action"], "cta_secondary": "Browse products and services"}, "sections": ["Hero with a clear offer and WhatsApp button", products_section, "Why choose this provider", "Service area and opening hours", "Quick FAQ", "Final WhatsApp and sharing call to action"], "assets_needed": ["Logo or main photo", "3 to 8 product or service photos", "Active WhatsApp number", "Prices or ranges, if available"], "tracking": ["profile view", "WhatsApp click", "call", "enquiry", "share"]}
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
    if ctx["language"] == "en":
        name, offer, products = ctx["name"], ctx["offer"], ctx["top_products"]
        products_line = f" Featured products: {', '.join(products)}." if products else ""
        return {"facebook_post": f"{name} is available in {ctx['location']}. {offer}.{products_line} Contact us on WhatsApp to {ctx['primary_action'].lower()}.", "instagram_caption": f"{offer}\nAvailable in {ctx['location']}" + (f"\nFeatured products: {', '.join(products)}" if products else "") + f"\nQuick action: {ctx['primary_action']}.", "whatsapp_status": f"{name} — {offer}. Message us now to {ctx['primary_action'].lower()}.", "product_description_template": "Lead with the customer need, then the benefit, price if available, service area and a simple WhatsApp call to action.", "image_prompt": f"Professional advertising visual for {name}, {ctx['module_label']}, Cameroon market, showing {offer}" + (f", featuring {products[0]}" if products else "") + ", clean modern layout, premium but local, high conversion.", "adgen_modules": ["headlines", "description", "social", "TikTok", "chatbot"]}
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
    if ctx["language"] == "en":
        name = ctx["name"]
        return [{"label": "First contact", "text": f"Hello, welcome to {name}. Tell us what you need and your neighborhood, and we will help you with {ctx['primary_action'].lower()}."}, {"label": "Lead follow-up", "text": f"Hello, I am following up on your enquiry with {name}. {ctx['offer']}. Would you like us to confirm the details now?"}, {"label": "After an enquiry", "text": "Thanks for your message. To proceed, send your name, neighborhood, exact need and preferred time."}, {"label": "Review request", "text": f"Thank you for choosing {name}. Your review helps other customers trust us. Could you share a short comment?"}]
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
    if ctx["language"] == "en":
        service_slug = urllib.parse.quote(ctx["module_label"].lower().replace(" ", "-"))
        city = ctx["location"].split(",")[0].strip() or "Douala"
        products = ctx["top_products"]
        keywords = [f"{ctx['module_label']} {city}", f"{ctx['name']} {city}", f"{ctx['primary_action']} {city}", "E-Shelle Cameroon", "WhatsApp Business Cameroon"]
        if products: keywords.insert(2, f"{products[0]} {city}")
        return {"title": f"{ctx['name']} - {ctx['module_label']} in {city}", "meta_description": f"Discover {ctx['name']} on E-Shelle: {ctx['offer']} in {ctx['location']}. Contact them quickly on WhatsApp."[:155], "keywords": keywords, "geo_page": f"/business/local/{urllib.parse.quote(city.lower())}/{service_slug}/", "schema": ["LocalBusiness", "Service", "FAQPage", "BreadcrumbList"], "cta": ctx["primary_action"]}
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
    if ctx["language"] == "en":
        products = ctx["top_products"]
        subject = products[0] if products else ctx["module_label"].lower()
        return {"format": "20-second TikTok/Reels video", "hook": f"Need {subject} in {ctx['location']}?", "scenes": ["Show the customer problem in a real setting", f"Introduce {ctx['name']} and its offer" + (f": {subject}" if products else ""), "Show proof: area, price or service, direct contact", f"Call to action: {ctx['primary_action']} on WhatsApp through E-Shelle"], "voiceover": f"In {ctx['location']}, {ctx['name']} makes things easier. {ctx['offer']}. Visit E-Shelle and contact them directly on WhatsApp.", "generation_status": "Script ready. Add a video agent to automatically produce the MP4 and voice-over."}
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
    if ctx["language"] == "en":
        return [{"workflow": "Chatbot lead capture", "steps": ["Identify the need", "Collect name, neighborhood and phone", "Send the lead to WhatsApp", "Log the enquiry"]}, {"workflow": "WhatsApp follow-up", "steps": ["Day 1: friendly follow-up", "Day 3: confirmation", "Day 7: review request or new offer"]}, {"workflow": "Weekly content", "steps": ["One Facebook post", "One WhatsApp status", "One video script", "One promotional offer"]}, {"workflow": "Reporting", "steps": ["Count profile views", "Count WhatsApp clicks", "Count enquiries", "Send a summary to the customer"]}]
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
    if ctx["language"] == "en":
        return [{"item": "The business profile has a name, city, neighborhood and WhatsApp number.", "done": bool(ctx["name"] and ctx["whatsapp"])}, {"item": "The chatbot does not promise unlisted prices or stock.", "done": True}, {"item": "The WhatsApp call to action includes a useful message.", "done": bool(ctx["whatsapp"])}, {"item": "The mini-site presents at least one clear offer.", "done": bool(ctx["offer"])}, {"item": "The SEO plan includes a city, industry and schema.", "done": True}, {"item": "The kit includes WhatsApp scripts, social content and a video script.", "done": True}]
    return [
        {"item": "La fiche business a un nom, une ville, un quartier et un WhatsApp.", "done": bool(ctx["name"] and ctx["whatsapp"])},
        {"item": "Le chatbot ne promet pas de prix ou stock non renseigné.", "done": True},
        {"item": "Le CTA WhatsApp contient un message utile.", "done": bool(ctx["whatsapp"])},
        {"item": "Le mini-site présente au moins une offre claire.", "done": bool(ctx["offer"])},
        {"item": "Le plan SEO contient ville + secteur + schéma.", "done": True},
        {"item": "Le kit contient scripts WhatsApp, contenu social et script vidéo.", "done": True},
    ]
