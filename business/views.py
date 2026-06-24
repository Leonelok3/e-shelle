import urllib.parse

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from billing.models import AffiliateProfile, Commission, Referral
from billing.affiliates import (
    attach_referral_if_needed,
    get_affiliate_by_code,
    get_or_create_affiliate_profile,
)

from .models import (
    AppCommission,
    BusinessKeyAccount,
    BusinessKeyPaymentRequest,
    BusinessCatalogItem,
    BusinessCatalogItemImage,
    BusinessLeadEvent,
    BusinessProfile,
    ClientAIKit,
    HomeAdSlide,
    PaymentRequest,
    PartnerCRMLead,
    PartnerLevel,
    PremiumSectorCampaign,
    ProviderPlan,
    UnmetSearchRequest,
    UnmetSearchResponse,
)
from .ai_delivery import generate_client_ai_kit, kit_summary_for_whatsapp
from .ai_arsenal import arsenal_agents, arsenal_stats, fidelisation_agent, opportunites_agent
from .reporting import business_report_context, render_business_report_pdf
from .services import collect_business_items, create_tracking_event, record_event_hit


BUSINESS_KEY_PRICE_XAF = 9900
BUSINESS_KEY_PARTNER_RECRUIT_RATE = 50
BUSINESS_KEY_PROVIDER_RATE = 30
BUSINESS_KEY_FULL_TOOLS = [
    "Lien partenaire personnel",
    "Dashboard commissions",
    "CRM prospects",
    "Creation de fiches prestataires",
    "Kit commercial et scripts WhatsApp",
    "Agent Commercial IA",
    "Contacts et campagnes WhatsApp",
    "Phone OCR local",
    "Agent SEO IA",
    "AdGen publicites IA",
    "Audio Studio IA",
    "LEBELAGE/Shopify Importer",
    "Catalogue commissions",
    "Academy quotidienne",
]

BUSINESS_KEY_PACKS = {
    BusinessKeyAccount.Tier.FREE: {
        "name": "Gratuit",
        "price": 0,
        "label": "Apercu",
        "desc": "Compte de decouverte. Pour vendre et toucher les commissions, active la Business Key.",
        "tools": ["Lien partenaire", "Apercu dashboard", "Scripts de decouverte"],
        "public": False,
    },
    BusinessKeyAccount.Tier.KEY: {
        "name": "E-Shelle Business Key",
        "price": BUSINESS_KEY_PRICE_XAF,
        "label": "Prix unique",
        "desc": "Une seule cle pour acceder a toutes les fonctionnalites et outils marketing E-Shelle.",
        "tools": BUSINESS_KEY_FULL_TOOLS,
        "public": True,
    },
    BusinessKeyAccount.Tier.PRO: {
        "name": "E-Shelle Business Key",
        "price": BUSINESS_KEY_PRICE_XAF,
        "label": "Ancien niveau compatible",
        "desc": "Ancien niveau conserve pour compatibilite. Acces complet comme la Business Key.",
        "tools": BUSINESS_KEY_FULL_TOOLS,
        "public": False,
    },
}


def _get_business_key_account(user):
    if not user.is_authenticated:
        return None
    account, _ = BusinessKeyAccount.objects.get_or_create(user=user)
    return account


def _business_key_missions(user, profile, referrals_count, converted_businesses):
    contacts_count = 0
    campaigns_count = 0
    seo_pages_count = 0
    try:
        from whatsapp_agent.models import Campagne, ContactWhatsApp

        contacts_count = ContactWhatsApp.objects.count()
        campaigns_count = Campagne.objects.count()
    except Exception:
        pass
    try:
        from seo_agent.services import LocalSEOAgent

        seo_pages_count = len(LocalSEOAgent().prioritized_pages())
    except Exception:
        pass

    return [
        {
            "title": "Ajouter 10 contacts business",
            "progress": min(contacts_count, 10),
            "target": 10,
            "done": contacts_count >= 10,
            "reward": "Debloque une campagne de test plus propre.",
        },
        {
            "title": "Creer 1 campagne WhatsApp",
            "progress": min(campaigns_count, 1),
            "target": 1,
            "done": campaigns_count >= 1,
            "reward": "Tu maitrises le pipeline de vente.",
        },
        {
            "title": "Faire inscrire 1 business",
            "progress": min(converted_businesses, 1),
            "target": 1,
            "done": converted_businesses >= 1,
            "reward": "Premiere conversion partenaire.",
        },
        {
            "title": "Obtenir 5 clics sur ton lien",
            "progress": min(profile.click_count, 5),
            "target": 5,
            "done": profile.click_count >= 5,
            "reward": "Preuve que ton message attire.",
        },
        {
            "title": "Generer une page SEO locale",
            "progress": min(seo_pages_count, 1),
            "target": 1,
            "done": seo_pages_count >= 1,
            "reward": "Visibilite Google locale.",
        },
    ]


def _business_key_daily_lessons():
    return [
        {
            "day": 1,
            "title": "Pitch Business Key en 30 secondes",
            "lesson": "Explique E-Shelle simplement: une cle a 9 900 XAF, tous les outils marketing, 50% sur partenaires et 30% sur prestataires.",
            "script": "Bonjour, E-Shelle Business Key te donne les outils pour vendre des services digitaux locaux: fiches prestataires, scripts, CRM, IA et commissions. La cle est a 9 900 XAF.",
            "mission": "Envoie ce pitch a 3 personnes serieuses qui cherchent une activite commerciale.",
            "proof": "Note les 3 noms dans ton CRM ou dans ton cahier terrain.",
        },
        {
            "day": 2,
            "title": "Prospection WhatsApp propre",
            "lesson": "Un bon partenaire ne spamme pas. Il cible un commerce precis, ecrit court et propose une demo.",
            "script": "Bonjour, je peux vous creer une fiche E-Shelle propre avec WhatsApp, services, photos et lien partageable. Voulez-vous voir une demo rapide avec votre activite ?",
            "mission": "Contacte 5 prestataires autour de toi avec un message personnalise.",
            "proof": "Ajoute les prospects chauds dans le CRM partenaire.",
        },
        {
            "day": 3,
            "title": "Fiche prestataire qui vend",
            "lesson": "Une fiche vend quand elle contient nom clair, ville, quartier, WhatsApp, photo, services/prix et appel a l'action.",
            "script": "Je vais vous montrer une fiche propre: le client voit vos services, votre zone, vos prix et peut vous ecrire directement sur WhatsApp.",
            "mission": "Cree ou ameliore une fiche prestataire test.",
            "proof": "Verifie la checklist qualite avant de partager le lien.",
        },
        {
            "day": 4,
            "title": "Recruter un partenaire",
            "lesson": "La commission partenaire est forte: 50% sur une Business Key validee. Il faut recruter des gens capables de vendre proprement.",
            "script": "Tu peux rejoindre E-Shelle Business Key a 9 900 XAF, utiliser tous les outils et gagner quand tu aides des prestataires ou recrutes un partenaire.",
            "mission": "Presente Business Key a 2 personnes qui savent parler aux commerces.",
            "proof": "Partage ton lien partenaire et note les retours.",
        },
        {
            "day": 5,
            "title": "Vendre a un prestataire",
            "lesson": "Le prestataire paie s'il voit une preuve: fiche, catalogue, message WhatsApp, post ou page locale.",
            "script": "On ne vous demande pas de payer dans le vide. Je vous montre d'abord une fiche ou une campagne test, ensuite vous decidez.",
            "mission": "Fais une demo a un commerce reel.",
            "proof": "Capture le lien ou la fiche montree au prospect.",
        },
        {
            "day": 6,
            "title": "Relance sans pression",
            "lesson": "La relance rappelle la valeur, pas la pression. Elle doit etre courte, polie et utile.",
            "script": "Bonjour, je reviens vers vous pour la fiche E-Shelle. Le but est que vos clients trouvent vos services et vous contactent plus vite. On active cette semaine ?",
            "mission": "Relance 5 prospects deja contactes.",
            "proof": "Classe-les: interesse, a relancer, refuse, converti.",
        },
        {
            "day": 7,
            "title": "Bilan et certification",
            "lesson": "Un partenaire progresse quand il mesure: prospects, fiches, demos, paiements, commissions.",
            "script": "Cette semaine j'ai contacte des prestataires, cree des fiches et suivi mes prospects. Je passe maintenant au plan de la semaine prochaine.",
            "mission": "Fais ton bilan hebdomadaire et choisis 10 prospects pour la semaine prochaine.",
            "proof": "Mets a jour ton CRM et tes missions.",
        },
    ]


def _business_key_quality_checklist(business=None):
    checks = [
        ("Nom clair", bool(getattr(business, "name", "")) if business else False),
        ("Ville renseignee", bool(getattr(business, "city", "")) if business else False),
        ("Quartier ou zone", bool(getattr(business, "district", "")) if business else False),
        ("WhatsApp ou telephone", bool((getattr(business, "whatsapp", "") or getattr(business, "phone", ""))) if business else False),
        ("Description utile", len(getattr(business, "description", "") or "") >= 40 if business else False),
        ("Offre ou promesse claire", bool(getattr(business, "promo_offer", "")) if business else False),
    ]
    done = sum(1 for _, ok in checks if ok)
    total = len(checks)
    score = int((done / total) * 100) if total else 0
    return {"checks": checks, "done": done, "total": total, "score": score}


def _business_key_certification(profile, referrals_count, converted_businesses, completed_lessons_count, crm_count):
    criteria = [
        ("Lire 7 lecons", completed_lessons_count, 7),
        ("Ajouter 10 prospects CRM", crm_count, 10),
        ("Obtenir 5 clics lien", profile.click_count, 5),
        ("Faire inscrire 1 business", converted_businesses, 1),
        ("Recruter 1 inscrit", referrals_count, 1),
    ]
    done = sum(1 for _, value, target in criteria if value >= target)
    score = int((done / len(criteria)) * 100) if criteria else 0
    return {
        "criteria": criteria,
        "done": done,
        "total": len(criteria),
        "score": score,
        "is_certified": done == len(criteria),
    }


def _detect_unmet_module(query: str) -> str:
    text = (query or "").lower()
    keyword_map = [
        (BusinessProfile.Module.RESTO, ["restaurant", "resto", "manger", "plat", "ndole", "eru", "taro", "pizza", "grill"]),
        (BusinessProfile.Module.GAZ, ["gaz", "bouteille", "bonbonne"]),
        (BusinessProfile.Module.PRESSING, ["pressing", "linge", "laver", "blanchisserie", "repassage"]),
        (BusinessProfile.Module.PHARMA, ["pharmacie", "medicament", "medicament", "sante", "ordonnance"]),
        (BusinessProfile.Module.IMMOBILIER, ["maison", "studio", "appartement", "chambre", "terrain", "loyer", "loyer", "immobilier", "meuble", "meuble", "non meuble", "non meuble", "bail"]),
        (BusinessProfile.Module.AUTO, ["voiture", "vehicule", "auto", "location voiture", "taxi"]),
        (BusinessProfile.Module.AGRO, ["agro", "plantain", "mais", "huile", "legume", "legumes", "vivres", "tomate", "manioc", "macabo"]),
        (BusinessProfile.Module.TRANSPORT, ["transport", "course", "livraison", "chauffeur", "colis"]),
        (BusinessProfile.Module.SERVICES, ["service", "reparation", "technicien", "plombier", "electricien", "artisan"]),
        (BusinessProfile.Module.FORMATION, ["cours", "formation", "apprendre", "professeur", "repetition"]),
        (BusinessProfile.Module.MARKET, ["montre", "telephone", "iphone", "ordinateur", "laptop", "pc", "accessoire"]),
        (BusinessProfile.Module.BOUTIQUE, ["boutique", "acheter", "produit", "vetement", "chaussure"]),
    ]
    for module, keywords in keyword_map:
        if any(keyword in text for keyword in keywords):
            return module
    return BusinessProfile.Module.GENERAL


def _normalize_unmet_module(query: str, selected_module: str) -> str:
    """Corrige la categorie si le texte du client est plus precis que le choix manuel."""

    detected = _detect_unmet_module(query)
    if detected != BusinessProfile.Module.GENERAL and detected != selected_module:
        return detected
    return selected_module if selected_module in dict(BusinessProfile.Module.choices) else detected


def _score_unmet_request(query: str, city: str = "", district: str = "", whatsapp: str = "", email: str = "", notes: str = "") -> dict:
    text = " ".join([query or "", notes or ""]).lower()
    module = _detect_unmet_module(text)
    score = 35
    if whatsapp:
        score += 25
    if email:
        score += 10
    if city:
        score += 10
    if district:
        score += 10
    if any(word in text for word in ["urgent", "aujourd", "maintenant", "ce soir", "vite"]):
        score += 15
    if any(word in text for word in ["budget", "prix", "payer", "acheter", "louer", "commander"]):
        score += 10
    score = min(score, 100)
    priority = "haute" if score >= 80 else "moyenne" if score >= 60 else "normal"
    return {
        "module": module,
        "ai_category": dict(BusinessProfile.Module.choices).get(module, "General"),
        "ai_priority": priority,
        "lead_score": score,
        "estimated_value_xaf": _estimated_unmet_value(module),
    }


def _estimated_unmet_value(module: str) -> int:
    return {
        BusinessProfile.Module.IMMOBILIER: 30000,
        BusinessProfile.Module.AUTO: 25000,
        BusinessProfile.Module.MARKET: 15000,
        BusinessProfile.Module.RESTO: 5000,
        BusinessProfile.Module.AGRO: 8000,
        BusinessProfile.Module.SERVICES: 12000,
    }.get(module, 10000)


def _notify_partner_text(unmet_request):
    zone = " / ".join(part for part in [unmet_request.district, unmet_request.city] if part) or "zone non precisee"
    return (
        "Nouvelle opportunite E-Shelle. "
        f"Besoin: {unmet_request.query}. Categorie: {unmet_request.get_module_display()}. "
        f"Zone: {zone}. Score IA: {unmet_request.lead_score}/100. "
        "Connecte-toi pour voir la demande et relancer proprement."
    )


def _client_followup_text(unmet_request):
    return (
        f"Bonjour, ici E-Shelle. Nous avons bien recu votre demande: {unmet_request.query}. "
        "Un partenaire/prestataire peut vous recontacter si une solution est disponible."
    )


def _external_search_links(query: str) -> list:
    q = urllib.parse.quote_plus(f"{query} Cameroun")
    return [
        {"label": "Google", "url": f"https://www.google.com/search?q={q}", "desc": "Verifier les resultats web maintenant."},
        {"label": "Images", "url": f"https://www.google.com/search?tbm=isch&q={q}", "desc": "Voir les photos et annonces visuelles."},
        {"label": "Facebook", "url": f"https://www.facebook.com/search/top?q={urllib.parse.quote_plus(query)}", "desc": "Explorer les groupes, pages et annonces locales."},
    ]


def _opportunity_matches(unmet_request, limit=3):
    businesses = BusinessProfile.objects.filter(is_active=True)
    if unmet_request.module and unmet_request.module != BusinessProfile.Module.GENERAL:
        businesses = businesses.filter(module=unmet_request.module)
    if unmet_request.city:
        city_matches = businesses.filter(city__iexact=unmet_request.city)
        if city_matches.exists():
            businesses = city_matches
    if unmet_request.district:
        district_matches = businesses.filter(district__icontains=unmet_request.district)
        if district_matches.exists():
            businesses = district_matches
    return list(businesses.order_by("-plan", "-leads_count", "-views_count", "name")[:limit])


def _matching_businesses_for_request(unmet_request, limit=20):
    businesses = BusinessProfile.objects.filter(is_active=True)
    if unmet_request.module and unmet_request.module != BusinessProfile.Module.GENERAL:
        businesses = businesses.filter(module=unmet_request.module)
    if unmet_request.city:
        businesses = businesses.filter(city__icontains=unmet_request.city)
    if unmet_request.district:
        district_matches = businesses.filter(district__icontains=unmet_request.district)
        if district_matches.exists():
            businesses = district_matches
    return businesses.order_by("-boost_expires_at", "-subscription_expires_at", "-leads_count", "name")[:limit]


def _provider_unmet_message(unmet_request, business):
    zone = " / ".join(part for part in [unmet_request.district, unmet_request.city] if part) or "votre zone"
    contact = unmet_request.whatsapp or unmet_request.email or "contact a demander via E-Shelle"
    return (
        f"Bonjour {business.name}, une personne cherche un service comme le votre a {zone}. "
        f"Besoin: {unmet_request.query}. Contact client: {contact}. "
        "Si vous pouvez l'aider, contactez-le rapidement. "
        "E-Shelle vous remercie pour votre fidelite, nous travaillons chaque jour pour ameliorer votre visibilite."
    )


def _customer_unmet_capture_text(query=""):
    base = "Aucun resultat parfait pour votre recherche."
    if query:
        base = f"Aucun resultat parfait pour: {query}."
    return (
        f"{base} Laissez votre WhatsApp ou email: E-Shelle peut transmettre votre besoin aux prestataires "
        "disponibles dans votre zone et vous prevenir des bons plans locaux."
    )


def _business_key_sector_cards(referral_link=""):
    """Argumentaires par secteur pour le kit Business Key."""
    referral_note = f" Lien: {referral_link}" if referral_link else ""
    return [
        {
            "name": "Restaurants",
            "slug": "restaurant",
            "problem": "Ils dependent des appels, statuts WhatsApp et clients de passage.",
            "solution": "Fiche visible, menu partageable, campagne WhatsApp, commande rapide et page Google locale.",
            "offer": "Plan Business a 15 000 FCFA/mois pour augmenter les commandes WhatsApp.",
            "script": "Bonjour, E-Shelle aide les restaurants a recevoir plus de commandes WhatsApp avec une fiche visible, un menu partageable et des campagnes locales. Voulez-vous une demo rapide ?" + referral_note,
            "objection": "Je poste deja mes plats sur WhatsApp.",
            "answer": "Justement, E-Shelle rend votre menu plus propre, partageable et trouvable meme par les clients qui ne sont pas encore dans vos contacts.",
            "links": [
                ("Creer une fiche", "/business/onboarding/?plan=free"),
                ("Agent Commercial IA", "/commercial-agent/"),
                ("Campagne WhatsApp", "/whatsapp/campagnes/creer/"),
                ("SEO local", "/seo/"),
            ],
        },
        {
            "name": "Pressing",
            "slug": "pressing",
            "problem": "Les clients oublient le pressing ou ne savent pas qui livre dans leur quartier.",
            "solution": "Fiche quartier, contact WhatsApp, offres hebdomadaires et relances clients.",
            "offer": "Plan Business pour attirer les clients proches et recevoir les demandes rapidement.",
            "script": "Bonjour, E-Shelle peut rendre votre pressing visible dans votre quartier et faciliter les demandes clients sur WhatsApp. Je peux vous montrer une fiche demo en 2 minutes." + referral_note,
            "objection": "Mes clients viennent deja au comptoir.",
            "answer": "Oui, mais les nouveaux clients cherchent d'abord sur WhatsApp, Google ou via recommandation. E-Shelle vous donne une vitrine simple.",
            "links": [
                ("Creer une fiche", "/business/onboarding/?plan=free"),
                ("Importer contacts", "/phone-ocr/"),
                ("Contacts WhatsApp", "/whatsapp/contacts/"),
                ("Campagne WhatsApp", "/whatsapp/campagnes/"),
            ],
        },
        {
            "name": "Gaz & livraison",
            "slug": "gaz",
            "problem": "Quand un client cherche du gaz, il veut un numero fiable maintenant.",
            "solution": "Fiche depot, quartier, WhatsApp, disponibilite, campagne de rappel et boost local.",
            "offer": "Plan Business pour recevoir plus d'appels et demandes WhatsApp dans la zone.",
            "script": "Bonjour, plusieurs familles cherchent du gaz rapidement par quartier. E-Shelle peut afficher votre depot et envoyer les demandes directement vers WhatsApp. Voulez-vous tester ?" + referral_note,
            "objection": "Je n'ai pas besoin d'internet.",
            "answer": "Vos clients utilisent deja WhatsApp. E-Shelle ne remplace pas votre travail, il vous apporte plus de demandes.",
            "links": [
                ("Creer une fiche", "/business/onboarding/?plan=free"),
                ("Gaz E-Shelle", "/gaz/"),
                ("Agent Commercial IA", "/commercial-agent/"),
                ("SEO local", "/seo/"),
            ],
        },
        {
            "name": "Immobilier",
            "slug": "immobilier",
            "problem": "Les biens sont disperses dans les groupes et les clients ne savent pas qui est serieux.",
            "solution": "Vitrine agence, fiches biens, partage WhatsApp, SEO quartier et contacts qualifies.",
            "offer": "Plan Premium pour valoriser les biens et capter prospects acheteurs/locataires.",
            "script": "Bonjour, E-Shelle peut donner une vitrine propre a vos biens immobiliers, avec liens WhatsApp et visibilite locale par quartier. Voulez-vous voir une demo ?" + referral_note,
            "objection": "Je publie deja dans les groupes Facebook.",
            "answer": "Les groupes donnent de la visibilite courte. Une vitrine E-Shelle donne un lien propre a envoyer a chaque prospect.",
            "links": [
                ("Immobilier", "/immobilier/"),
                ("Creer une fiche", "/business/onboarding/?plan=free"),
                ("AdGen", "/pub/"),
                ("SEO local", "/seo/"),
            ],
        },
        {
            "name": "Auto",
            "slug": "auto",
            "problem": "Les vendeurs ont besoin de montrer les vehicules clairement et rassurer les acheteurs.",
            "solution": "Annonce auto, contact WhatsApp, photos, boost et scripts de vente.",
            "offer": "Plan Business ou Premium pour mettre les vehicules en avant.",
            "script": "Bonjour, E-Shelle peut vous aider a presenter vos vehicules avec une fiche propre, photos, prix et contact WhatsApp direct. Voulez-vous que je vous montre ?" + referral_note,
            "objection": "Les acheteurs viennent par connaissance.",
            "answer": "E-Shelle ajoute un canal supplementaire: un lien propre que vos connaissances peuvent partager facilement.",
            "links": [
                ("Auto", "/auto/"),
                ("AdGen", "/pub/"),
                ("Campagne WhatsApp", "/whatsapp/campagnes/"),
                ("Contacts", "/whatsapp/contacts/"),
            ],
        },
        {
            "name": "Agro / Market / Pharma",
            "slug": "market",
            "problem": "Les produits existent, mais la demande est mal organisee et les clients ne voient pas les offres.",
            "solution": "Catalogue, vitrine produit, WhatsApp, campagne, posts IA et referencement local.",
            "offer": "Plan Business pour vendre et recevoir des demandes sans perdre les contacts.",
            "script": "Bonjour, E-Shelle peut transformer vos produits en mini catalogue partageable avec commande WhatsApp et campagne de relance. On peut faire un test simple ?" + referral_note,
            "objection": "Je n'ai pas beaucoup de produits.",
            "answer": "Meme 5 produits bien presentes peuvent mieux vendre qu'une longue liste confuse dans WhatsApp.",
            "links": [
                ("Market", "/annonces/"),
                ("Agro", "/agro/"),
                ("Pharma", "/pharma/"),
                ("AdGen", "/pub/"),
            ],
        },
    ]


FOLLOW_UP_SCRIPTS = [
    {
        "key": "after_contact",
        "label": "Relance apres 1 jour",
        "text": "Bonjour {{nom}}, je reviens vers vous pour la demo E-Shelle. On peut vous aider a recevoir plus de demandes WhatsApp et rendre votre activite plus visible. Est-ce que je peux vous montrer en 2 minutes ?",
    },
    {
        "key": "after_demo",
        "label": "Relance apres preuve envoyee",
        "text": "Bonjour {{nom}}, avez-vous pu regarder la fiche/demo E-Shelle ? L'objectif est simple: une vitrine propre, un lien WhatsApp et plus de clients qui comprennent vite votre offre.",
    },
    {
        "key": "payment",
        "label": "Relance paiement",
        "text": "Bonjour {{nom}}, si la demo vous convient, on peut activer votre plan Business et lancer la visibilite. Le paiement peut se faire par Mobile Money, puis E-Shelle active votre fiche.",
    },
    {
        "key": "last_chance",
        "label": "Derniere relance douce",
        "text": "Bonjour {{nom}}, je ferme ma liste de relance aujourd'hui. Si vous voulez toujours tester E-Shelle pour votre activite, je peux vous accompagner maintenant.",
    },
]


def _crm_script_for_lead(lead):
    sector_cards = {card["slug"]: card for card in _business_key_sector_cards()}
    card = sector_cards.get(lead.sector)
    if card:
        return card["script"].replace("Bonjour,", f"Bonjour {lead.contact_name or lead.business_name},", 1)
    return f"Bonjour {lead.contact_name or lead.business_name}, E-Shelle peut aider votre activite a etre plus visible et recevoir des demandes WhatsApp. Voulez-vous une demo rapide ?"


def _normalize_cameroon_phone(number):
    cleaned = "".join(ch for ch in (number or "") if ch.isdigit())
    if not cleaned:
        return ""
    if cleaned.startswith("237"):
        return f"+{cleaned}"
    if len(cleaned) in {8, 9}:
        return f"+237{cleaned}"
    return f"+{cleaned}" if number.strip().startswith("+") else cleaned


def _lead_sector_card(lead):
    cards = {card["slug"]: card for card in _business_key_sector_cards()}
    return cards.get(lead.sector) or {
        "name": lead.get_sector_display(),
        "problem": "Le business manque de visibilite claire et de suivi client.",
        "solution": "Fiche E-Shelle, contact WhatsApp, campagne de relance et visibilite locale.",
        "offer": "Plan Business a proposer selon le besoin.",
        "script": _crm_script_for_lead(lead),
        "objection": "Je vais reflechir.",
        "answer": "On peut commencer par une demo simple et vous decidez apres avoir vu la preuve.",
        "links": [("Creer une fiche", "/business/onboarding/?plan=free"), ("Agent Commercial IA", "/commercial-agent/")],
    }


@require_GET
def track(request, public_id):
    """Redirige vers WhatsApp/appel/detail en comptant le lead."""
    event = get_object_or_404(BusinessLeadEvent, public_id=public_id)
    target_url = record_event_hit(event, request=request)
    return redirect(target_url)


@require_GET
def go_business(request, business_id, event_type):
    """Clic public depuis la home: compte le lead puis redirige."""
    business = get_object_or_404(BusinessProfile, pk=business_id, is_active=True)
    allowed = {
        "view": BusinessLeadEvent.EventType.VIEW,
        "whatsapp": BusinessLeadEvent.EventType.WHATSAPP,
        "detail": BusinessLeadEvent.EventType.DETAIL,
        "order": BusinessLeadEvent.EventType.ORDER,
    }
    event_kind = allowed.get(event_type, BusinessLeadEvent.EventType.DETAIL)
    target_url = _business_public_target(business, event_kind)
    if event_kind != BusinessLeadEvent.EventType.VIEW:
        BusinessProfile.objects.filter(pk=business.pk).update(views_count=F("views_count") + 1)
    event = create_tracking_event(business, event_kind, target_url, source="home")
    return redirect(record_event_hit(event, request=request))


@require_GET
def go_slide(request, slide_id):
    """Clic sur un slide publicitaire de la home."""
    slide = get_object_or_404(HomeAdSlide.objects.select_related("business"), pk=slide_id, is_active=True)
    target_url = slide.destination_url()
    HomeAdSlide.objects.filter(pk=slide.pk).update(clicks_count=F("clicks_count") + 1)
    if slide.business:
        BusinessProfile.objects.filter(pk=slide.business_id).update(views_count=F("views_count") + 1)
        event = create_tracking_event(
            slide.business,
            BusinessLeadEvent.EventType.ORDER,
            target_url,
            source="home_slide",
            metadata={"slide_id": slide.pk, "slide_title": slide.title},
        )
        target_url = record_event_hit(event, request=request)
    return redirect(target_url)


def _business_public_target(business, event_kind):
    if event_kind in {BusinessLeadEvent.EventType.WHATSAPP, BusinessLeadEvent.EventType.ORDER}:
        number = (business.whatsapp or business.phone or "").replace("+", "").replace(" ", "").replace("-", "")
        if number:
            if not number.startswith("237"):
                number = f"237{number}"
            import urllib.parse
            text = urllib.parse.quote(f"Bonjour {business.name}, je viens de E-Shelle.")
            return f"https://wa.me/{number}?text={text}"
    if business.promo_url:
        return business.promo_url
    import urllib.parse
    return f"/chat/?q={urllib.parse.quote(f'Je veux contacter {business.name}')}"


def public_profile(request, public_slug):
    """Vitrine publique centrale d'une activite E-Shelle."""
    business = get_object_or_404(BusinessProfile, public_slug=public_slug, is_active=True)
    BusinessProfile.objects.filter(pk=business.pk).update(views_count=F("views_count") + 1)
    source_object = business.content_object
    source_url = ""
    if source_object and hasattr(source_object, "get_absolute_url"):
        try:
            source_url = source_object.get_absolute_url()
        except Exception:
            source_url = ""
    public_url = request.build_absolute_uri(business.get_absolute_url())
    share_text = f"Decouvrez {business.name} sur E-Shelle: {public_url}"
    whatsapp_url = business.whatsapp_url(f"Bonjour {business.name}, je viens de votre boutique E-Shelle: {public_url}")
    return render(
        request,
        "business/public_profile.html",
        {
            "business": business,
            "source_object": source_object,
            "source_url": source_url,
            "items": collect_business_items(business),
            "public_url": public_url,
            "share_text": share_text,
            "share_whatsapp_url": f"https://wa.me/?text={urllib.parse.quote(share_text)}",
            "whatsapp_url": whatsapp_url,
        },
    )


def provider_plans(request):
    """Page publique des abonnements prestataires."""
    plans = ProviderPlan.objects.filter(is_active=True).order_by("order", "monthly_price_xaf")
    proof = {
        "premium_businesses": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "views": BusinessProfile.objects.aggregate(total=Sum("views_count"))["total"] or 0,
        "leads": BusinessProfile.objects.aggregate(total=Sum("leads_count"))["total"] or 0,
    }
    return render(request, "business/provider_plans.html", {"plans": plans, "proof": proof})


def solutions(request):
    """Page commerciale qui oriente chaque besoin vers la bonne application E-Shelle."""
    proof = {
        "premium_businesses": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "views": BusinessProfile.objects.aggregate(total=Sum("views_count"))["total"] or 0,
        "leads": BusinessProfile.objects.aggregate(total=Sum("leads_count"))["total"] or 0,
    }
    solutions_grid = [
        {
            "title": "Je veux plus de clients",
            "tag": "Visibilité",
            "desc": "Fiche business, WhatsApp, mise en avant locale, statistiques et carrousel premium.",
            "url": "/business/plans/",
            "cta": "Devenir Premium",
            "accent": "#7ee56f",
        },
        {
            "title": "Je veux vendre mes produits",
            "tag": "Marketplace",
            "desc": "Publiez produits, services, véhicules, biens immobiliers ou produits santé avec lien partageable.",
            "url": "/annonces/",
            "cta": "Voir la marketplace",
            "accent": "#f28a19",
        },
        {
            "title": "Je veux créer une pub",
            "tag": "IA Marketing",
            "desc": "AdGen génère titres, posts Facebook/Instagram, messages WhatsApp et scripts vidéo.",
            "url": "/pub/",
            "cta": "Ouvrir AdGen",
            "accent": "#8b5cf6",
        },
        {
            "title": "Je gère une tontine ou réunion",
            "tag": "Association",
            "desc": "Njangi Digital suit membres, cotisations, mains, prêts, fonds communs et rapports PDF.",
            "url": "/njangi/",
            "cta": "Voir Njangi",
            "accent": "#38bdf8",
        },
        {
            "title": "Je fais de la collecte terrain",
            "tag": "Microfinance",
            "desc": "Tchaslucpay suit collecteurs, clients, dépôts, retraits, reçus PDF et soldes.",
            "url": "http://127.0.0.1:8001/",
            "cta": "Voir la collecte",
            "accent": "#10b981",
        },
        {
            "title": "Je cherche un artisan fiable",
            "tag": "Travaux",
            "desc": "Plombiers, électriciens, maçons, carreleurs, peintres et menuisiers proches du client.",
            "url": "/artisans/",
            "cta": "Voir artisans",
            "accent": "#facc15",
        },
    ]
    demos = [
        ("Santé", "/sante/produits/", "Produits santé avec photos et commande WhatsApp"),
        ("Immobilier", "/immobilier/", "Biens, agences et vitrines publiques"),
        ("Auto", "/auto/", "Vente et location de véhicules"),
        ("Artisans", "/artisans/", "Profils artisans et demandes travaux"),
        ("Njangi", "/njangi/groupe/reunion-demo-e-shelle/", "Réunion/tontine démo"),
        ("Collecte", "http://127.0.0.1:8001/", "Collecte terrain et reçus PDF"),
        ("AdGen", "/pub/", "Publicités IA pour business"),
    ]
    return render(
        request,
        "business/solutions.html",
        {"solutions": solutions_grid, "demos": demos, "proof": proof},
    )


def custom_app_offer(request):
    """Offre application personnalisee hebergee sur domaine client."""
    whatsapp_text = urllib.parse.quote(
        "Bonjour E-Shelle, je veux une application personnalisee pour mon business avec hebergement sur mon domaine."
    )
    return render(
        request,
        "business/custom_app_offer.html",
        {"whatsapp_url": f"https://wa.me/237680625082?text={whatsapp_text}"},
    )


def eshelle_communication(request):
    """Plan de lancement terrain pour faire connaitre E-Shelle sans disperser les outils."""
    proof = {
        "businesses": BusinessProfile.objects.filter(is_active=True).count(),
        "requests": UnmetSearchRequest.objects.count(),
        "premium": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
    }
    promise = "Vous cherchez quelque chose au Cameroun ? E-Shelle trouve ou demande au reseau pour vous."
    scripts = [
        {
            "channel": "WhatsApp statut",
            "title": "Message court quotidien",
            "text": f"{promise} Teste maintenant: cherche resto, gaz, studio, formation, produit ou service local sur E-Shelle.",
        },
        {
            "channel": "WhatsApp direct",
            "title": "Client ou proche",
            "text": "Bonjour, si tu cherches un service, un produit ou un prestataire au Cameroun, essaie E-Shelle. Si le resultat n'existe pas encore, E-Shelle enregistre ta demande et active le reseau local.",
        },
        {
            "channel": "Facebook",
            "title": "Post de lancement",
            "text": "E-Shelle veut devenir le moteur local du Cameroun: vous cherchez, E-Shelle trouve dans sa base, demande au reseau ou propose des pistes externes. Les prestataires gagnent en visibilite, les clients gagnent du temps.",
        },
        {
            "channel": "TikTok/Reel",
            "title": "Script 25 secondes",
            "text": "0-5s: Vous cherchez un studio, un resto ou un service fiable ? 5-15s: Tapez votre besoin sur E-Shelle. 15-22s: Si E-Shelle ne trouve pas, il demande au reseau. 22-25s: E-Shelle, le Google local assiste par IA.",
        },
        {
            "channel": "Prestataire",
            "title": "Recrutement business",
            "text": "Bonjour, E-Shelle recoit des recherches locales. Si votre fiche est visible, les clients peuvent vous contacter plus vite. On peut creer votre fiche avec WhatsApp, zone, services, photos et offres.",
        },
        {
            "channel": "Partenaire",
            "title": "Business Key",
            "text": "Avec la Business Key a 9 900 XAF, vous avez les outils E-Shelle pour vendre: fiches, IA marketing, CRM, demandes clients, scripts et commissions.",
        },
    ]
    niches = [
        {
            "name": "Studios et chambres Yaounde",
            "goal": "Verifier que les demandes immobilieres sortent bien vers les partenaires.",
            "mission": "Faire 20 recherches test par quartier et recruter 10 bailleurs/agences.",
        },
        {
            "name": "Restaurants Douala",
            "goal": "Prouver que les clients trouvent ou demandent un plat precis.",
            "mission": "Creer 15 fiches resto avec photos, menus et WhatsApp.",
        },
        {
            "name": "Gaz et livraison quartier",
            "goal": "Transformer les recherches urgentes en appels WhatsApp.",
            "mission": "Recruter les depots par quartier et tester les demandes sans resultat.",
        },
        {
            "name": "Produits market Akwa",
            "goal": "Comparer produits existants, demandes manquees et redirections externes.",
            "mission": "Ajouter 30 produits reels et mesurer les recherches sans resultat.",
        },
    ]
    checklist = [
        "Publier 3 statuts WhatsApp par jour pendant 7 jours.",
        "Faire 10 demonstrations E-Shelle a des prestataires chaque jour.",
        "Creer ou ameliorer les fiches des prestataires qui repondent.",
        "Verifier chaque soir les demandes non satisfaites dans le Command Center.",
        "Contacter les categories sans offre et recruter les prestataires manquants.",
        "Mesurer les sources: accueil, chat, recherche, Facebook, WhatsApp et terrain.",
    ]
    quick_links = [
        ("Tester une recherche", "/chat/?q=studio%20obili"),
        ("Demande express", "/business/demande-express/"),
        ("Demandes clients", "/business/demandes/"),
        ("Pipeline opportunites", "/business/opportunites/"),
        ("Command Center", "/business/command-center/"),
        ("Business Key", "/business/partner/"),
    ]
    return render(
        request,
        "business/eshelle_communication.html",
        {
            "promise": promise,
            "proof": proof,
            "scripts": scripts,
            "niches": niches,
            "checklist": checklist,
            "quick_links": quick_links,
        },
    )


def ai_arsenal(request):
    """Cockpit public/interne des agents IA E-Shelle et des agents a activer."""
    days = _positive_int(request.GET.get("days"), 14)
    return render(
        request,
        "business/ai_arsenal.html",
        {
            "days": days,
            "agents": arsenal_agents(),
            "stats": arsenal_stats(days=days),
            "fidelisation_rows": fidelisation_agent(days=days),
            "opportunity_rows": opportunites_agent(),
        },
    )


@staff_member_required
@require_POST
def ai_arsenal_action(request):
    """Actions directes lancees depuis l'Arsenal IA, sans dupliquer les agents existants."""
    action = request.POST.get("action", "").strip()
    next_url = request.POST.get("next") or "business:ai_arsenal"

    if action == "generate_relance":
        business = get_object_or_404(BusinessProfile, pk=request.POST.get("business_id"), is_active=True)
        from commercial_agent.models import ProspectBusiness
        from commercial_agent.services import CommercialAgentService

        prospect, created = ProspectBusiness.objects.get_or_create(
            business_profile=business,
            defaults={
                "nom": business.name,
                "module": business.module,
                "ville": business.city,
                "quartier": business.district,
                "telephone": business.phone,
                "whatsapp": business.whatsapp,
                "description": business.description,
                "source": ProspectBusiness.Source.BUSINESS_PROFILE,
                "statut": ProspectBusiness.Statut.QUALIFIE,
                "assigne_a": request.user,
            },
        )
        if not created:
            prospect.nom = business.name
            prospect.module = business.module
            prospect.ville = business.city
            prospect.quartier = business.district
            prospect.telephone = business.phone
            prospect.whatsapp = business.whatsapp
            prospect.description = business.description
            prospect.assigne_a = prospect.assigne_a or request.user
            prospect.save(update_fields=["nom", "module", "ville", "quartier", "telephone", "whatsapp", "description", "assigne_a", "maj_le"])
        CommercialAgentService.refresh_prospect(prospect)
        relance = CommercialAgentService.create_relance(
            prospect,
            user=request.user,
            message=CommercialAgentService.generate_message(
                prospect,
                canal="whatsapp",
                contexte="Relance de fidelisation depuis l'Arsenal IA E-Shelle.",
            ),
        )
        messages.success(request, f"Relance IA generee pour {prospect.nom}: {relance.message[:140]}")
        return redirect("commercial_agent:prospect_detail", pk=prospect.pk)

    if action == "create_whatsapp_campaign":
        from commercial_agent.services import CommercialAgentService

        module = request.POST.get("module", "").strip()
        city = request.POST.get("city", "").strip()
        if city == "Toutes zones":
            city = ""
        limit = _positive_int(request.POST.get("limit"), 50)
        name = request.POST.get("name") or f"Arsenal IA WhatsApp {module or 'E-Shelle'} {timezone.localdate().strftime('%d/%m/%Y')}"
        campaign = CommercialAgentService.create_whatsapp_campaign_from_due(
            name=name,
            user=request.user,
            module=module,
            ville=city,
            limit=limit,
        )
        if campaign.total_destinataires:
            messages.success(request, f"Campagne WhatsApp creee avec {campaign.total_destinataires} prospect(s). Verifie avant lancement.")
        else:
            messages.warning(request, "Campagne WhatsApp creee mais aucun prospect eligible n'a ete trouve. Synchronise d'abord les fiches/contacts.")
        return redirect("whatsapp_agent:wa_detail", pk=campaign.pk)

    if action == "create_prospect_campaign":
        from commercial_agent.services import CommercialAgentService

        module = request.POST.get("module", "").strip()
        city = request.POST.get("city", "").strip()
        if city == "Toutes zones":
            city = ""
        name = request.POST.get("name") or f"Arsenal IA Prospection {module or 'E-Shelle'} {timezone.localdate().strftime('%d/%m/%Y')}"
        campaign = CommercialAgentService.create_campaign_from_due(name=name, user=request.user, module=module, ville=city)
        messages.success(request, f"Campagne de prospection creee avec {campaign.prospects.count()} prospect(s).")
        return redirect("commercial_agent:dashboard")

    if action == "assign_opportunities":
        module = request.POST.get("module", "").strip()
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        open_statuses = [
            UnmetSearchRequest.Status.NEW,
            UnmetSearchRequest.Status.NOTIFIED,
            UnmetSearchRequest.Status.IN_PROGRESS,
            UnmetSearchRequest.Status.CONTACTED,
            UnmetSearchRequest.Status.PROVIDER_FOUND,
        ]
        requests_qs = UnmetSearchRequest.objects.filter(status__in=open_statuses)
        if module:
            requests_qs = requests_qs.filter(module=module)
        if city and city != "Toutes zones":
            requests_qs = requests_qs.filter(city__iexact=city)
        if district:
            requests_qs = requests_qs.filter(district__icontains=district)
        count = requests_qs.update(assigned_partner=request.user, status=UnmetSearchRequest.Status.NOTIFIED, updated_at=timezone.now())
        messages.success(request, f"{count} demande(s) assignee(s) a votre compte.")
        return redirect("business:unmet_search_opportunities")

    messages.error(request, "Action Arsenal IA inconnue.")
    return redirect(next_url)


def partner(request):
    """Page publique pour recruter ambassadeurs et affiliés."""
    account = _get_business_key_account(request.user)
    proof = {
        "businesses": BusinessProfile.objects.filter(is_active=True).count(),
        "premium": BusinessProfile.objects.filter(
            is_active=True,
            plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM],
        ).count(),
        "leads": BusinessProfile.objects.aggregate(total=Sum("leads_count"))["total"] or 0,
    }
    packs = [
        {
            "tier": tier,
            "name": data["name"],
            "price": data["price"],
            "label": data["label"],
            "desc": data["desc"],
            "items": data["tools"],
        }
        for tier, data in BUSINESS_KEY_PACKS.items()
        if data.get("public", True)
    ]
    return render(
        request,
        "business/partner.html",
        {
            "proof": proof,
            "packs": packs,
            "account": account,
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


def business_key_packs(request):
    """Page claire des prix Business Key."""
    account = _get_business_key_account(request.user)
    packs = [
        {"tier": tier, **data}
        for tier, data in BUSINESS_KEY_PACKS.items()
        if data.get("public", True)
    ]
    return render(
        request,
        "business/business_key_packs.html",
        {
            "packs": packs,
            "account": account,
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


def business_key_how_to_earn(request):
    """Page pedagogique: comment gagner proprement avec E-Shelle."""
    return render(
        request,
        "business/business_key_how_to_earn.html",
        {
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


def business_key_recruit(request):
    """Landing courte pour convertir vite les futurs partenaires."""
    return render(request, "business/business_key_recruit.html")


def business_key_academy(request):
    """Academy Business Key: methode, secteurs, outils et progression."""
    account = _get_business_key_account(request.user)
    sectors = _business_key_sector_cards()
    modules = [
        ("1", "Comprendre E-Shelle", "Savoir expliquer la plateforme en 30 secondes."),
        ("2", "Choisir un secteur", "Restaurants, pressing, gaz, immobilier, auto, agro ou market."),
        ("3", "Prospecter proprement", "Utiliser un script court, demander une demo, eviter le spam."),
        ("4", "Creer une preuve", "Fiche business, campagne WhatsApp, post AdGen ou page SEO locale."),
        ("5", "Conclure et suivre", "Demande de paiement, activation admin, commission et relance."),
    ]
    return render(
        request,
        "business/business_key_academy.html",
        {"account": account, "sectors": sectors, "modules": modules},
    )


def business_key_daily_academy(request):
    """Formation quotidienne Business Key: lecon, mission, score et certification."""
    profile = get_or_create_affiliate_profile(request.user) if request.user.is_authenticated else None
    lessons = _business_key_daily_lessons()
    selected_day = _positive_int(request.GET.get("jour"), 0)
    if not selected_day:
        selected_day = ((timezone.localdate().toordinal() - 1) % len(lessons)) + 1
    selected_day = max(1, min(len(lessons), selected_day))
    lesson = lessons[selected_day - 1]

    completed = set(request.session.get("business_key_completed_lessons", []))
    if request.method == "POST":
        completed.add(str(selected_day))
        request.session["business_key_completed_lessons"] = sorted(completed)
        request.session.modified = True
        messages.success(request, "Lecon marquee comme terminee. Continue comme ca.")
        return redirect(f"{request.path}?jour={selected_day}")

    crm_count = PartnerCRMLead.objects.filter(partner=request.user).count() if request.user.is_authenticated else 0
    referrals_count = Referral.objects.filter(affiliate=profile).count() if profile else 0
    converted_businesses = PartnerCRMLead.objects.filter(
        partner=request.user,
        status=PartnerCRMLead.Status.CONVERTED,
    ).count() if request.user.is_authenticated else 0
    latest_business = BusinessProfile.objects.filter(owner=request.user).order_by("-updated_at").first() if request.user.is_authenticated else None
    quality = _business_key_quality_checklist(latest_business)
    certification = _business_key_certification(
        profile=profile,
        referrals_count=referrals_count,
        converted_businesses=converted_businesses,
        completed_lessons_count=len(completed),
        crm_count=crm_count,
    ) if profile else None

    return render(
        request,
        "business/business_key_daily_academy.html",
        {
            "lessons": lessons,
            "lesson": lesson,
            "selected_day": selected_day,
            "completed": completed,
            "completed_count": len(completed),
            "quality": quality,
            "latest_business": latest_business,
            "certification": certification,
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


@login_required
def business_key_kit(request):
    """Kit commercial consultable par les partenaires."""
    profile = get_or_create_affiliate_profile(request.user)
    referral_link = request.build_absolute_uri(f"/ref/{profile.ref_code}/")
    sectors = _business_key_sector_cards(referral_link)
    scripts = [{"title": sector["name"], "text": sector["script"]} for sector in sectors]
    scripts.insert(
        0,
        {
            "title": "Recruter un partenaire",
            "text": f"Tu peux gagner avec E-Shelle sans stock. Tu aides les commerces a trouver des clients, tu partages ton lien {referral_link}, et tu gagnes quand un client paie un service reel.",
        },
    )
    scripts.extend(
        [
            {
                "title": "Cours de langue",
                "text": f"Bonjour, E-Shelle propose des cours de langue a 5 000 FCFA/mois: anglais, allemand, italien et preparation progressive. Voulez-vous essayer ou voir le programme ? Lien: {referral_link}",
            },
            {
                "title": "Formation IA / Marketing",
                "text": f"Bonjour, E-Shelle peut vous former a utiliser l'IA, creer des contenus, vendre en ligne et prospecter avec WhatsApp. Le programme commence a 5 000 FCFA/mois. Voulez-vous voir le contenu ? Lien: {referral_link}",
            },
            {
                "title": "E-Shelle Love",
                "text": f"Bonjour, E-Shelle Love aide les personnes serieuses a faire des rencontres plus organisees et plus respectueuses. L'abonnement commence a 5 000 FCFA/mois. Voulez-vous voir comment ca marche ? Lien: {referral_link}",
            },
            {
                "title": "Site web / logiciel personnalise",
                "text": f"Bonjour, E-Shelle peut creer un site web, une boutique, un catalogue ou un logiciel personnalise pour votre activite. On peut commencer par une page vitrine avec WhatsApp et SEO local. Voulez-vous une estimation ? Lien: {referral_link}",
            },
        ]
    )
    price_lines = [
        ("Fiche gratuite", "0 FCFA", "Presence de base et lien partageable"),
        ("Cours de langue", "5 000 FCFA/mois", "Anglais, allemand, italien et preparation avec suivi E-Shelle"),
        ("Formations IA / Marketing", "5 000 FCFA/mois", "Apprendre a utiliser l'IA, vendre en ligne et creer du contenu"),
        ("E-Shelle Love", "5 000 FCFA/mois", "Rencontres serieuses, profils verifies et accompagnement discret"),
        ("Business", "10 000 FCFA/mois", "Visibilite, leads WhatsApp, IA commerciale"),
        ("Premium", "25 000 FCFA/mois", "Boost, priorite locale, contenu et campagnes"),
        ("Business Key", f"{BUSINESS_KEY_PRICE_XAF} FCFA", "Prix unique avec acces complet aux outils marketing E-Shelle"),
        ("Commission partenaire", f"{BUSINESS_KEY_PARTNER_RECRUIT_RATE}%", "Quand tu fais souscrire un autre partenaire a la Business Key"),
        ("Commission prestataire", f"{BUSINESS_KEY_PROVIDER_RATE}%", "Sur les frais payes par un prestataire que tu fais enregistrer"),
        ("Site web vitrine", "50 000 FCFA+", "Page professionnelle, WhatsApp, SEO local et formulaire de contact"),
        ("Boutique / catalogue web", "100 000 FCFA+", "Catalogue produits, commandes WhatsApp, paiements et administration"),
        ("Logiciel personnalise", "150 000 FCFA+", "Application metier sur mesure pour ecole, commerce, tontine ou service"),
    ]
    agent_links = [
        ("Agent Commercial IA", "/commercial-agent/", "Qualifier les prospects et preparer les messages."),
        ("WhatsApp Agent", "/whatsapp/campagnes/", "Lancer et suivre les campagnes."),
        ("Contacts WhatsApp", "/whatsapp/contacts/", "Choisir les numeros a relancer."),
        ("Phone OCR", "/phone-ocr/", "Extraire des numeros depuis une capture autorisee."),
        ("AdGen", "/pub/", "Generer posts, accroches et visuels marketing."),
        ("SEO Agent", "/seo/", "Creer des pages locales rentables."),
    ]
    return render(
        request,
        "business/business_key_kit.html",
        {
            "referral_link": referral_link,
            "scripts": scripts,
            "price_lines": price_lines,
            "sectors": sectors,
            "agent_links": agent_links,
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


@login_required
def catalogue_commissions(request):
    """Catalogue de toutes les apps E-Shelle vendables par un partenaire."""
    apps = AppCommission.objects.filter(is_active=True).order_by("priority", "app_name")
    levels = PartnerLevel.objects.filter(
        is_active=True,
        level=PartnerLevel.Level.BUSINESS_KEY,
    ).prefetch_related("apps_accessibles").order_by("prix_fcfa", "level")
    profile = get_or_create_affiliate_profile(request.user)
    referral_link = request.build_absolute_uri(f"/ref/{profile.ref_code}/")
    return render(
        request,
        "business/catalogue_commissions.html",
        {
            "apps": apps,
            "levels": levels,
            "partner": profile,
            "referral_link": referral_link,
            "page_title": "Catalogue des commissions",
        },
    )


def unmet_search_create(request):
    """Capture une recherche non satisfaite pour la transformer en opportunite locale."""
    initial_query = (request.GET.get("q") or request.POST.get("query") or "").strip()[:260]
    initial_city = (request.GET.get("city") or request.POST.get("city") or "").strip()[:100]
    initial_district = (request.GET.get("district") or request.POST.get("district") or "").strip()[:120]
    detected_module = _detect_unmet_module(initial_query)
    created_request = None
    matching_businesses = []
    provider_messages = []

    if request.method == "POST":
        query = request.POST.get("query", "").strip()[:260]
        whatsapp = request.POST.get("whatsapp", "").strip()[:40]
        email = request.POST.get("email", "").strip()[:254]
        consent_share = request.POST.get("consent_share_contact") == "on"
        if not query:
            messages.error(request, "Expliquez rapidement ce que vous cherchez.")
        elif not (whatsapp or email):
            messages.error(request, "Laissez au moins un WhatsApp ou un email.")
        elif not consent_share:
            messages.error(request, "Le consentement est obligatoire pour transmettre votre demande aux prestataires.")
        else:
            city = request.POST.get("city", "").strip()[:100]
            district = request.POST.get("district", "").strip()[:120]
            notes = request.POST.get("notes", "").strip()
            ai = _score_unmet_request(query, city=city, district=district, whatsapp=whatsapp, email=email, notes=notes)
            module = _normalize_unmet_module(query, request.POST.get("module") or ai["module"])
            ai["ai_category"] = dict(BusinessProfile.Module.choices).get(module, ai["ai_category"])
            ai["estimated_value_xaf"] = _estimated_unmet_value(module)
            created_request = UnmetSearchRequest.objects.create(
                query=query,
                module=module,
                city=city,
                district=district,
                customer_name=request.POST.get("customer_name", "").strip()[:120],
                whatsapp=whatsapp,
                email=email,
                notes=notes,
                consent_share_contact=consent_share,
                consent_promotions=request.POST.get("consent_promotions") == "on",
                source=request.POST.get("source", "search").strip()[:40] or "search",
                ai_category=ai["ai_category"],
                ai_priority=ai["ai_priority"],
                lead_score=ai["lead_score"],
                estimated_value_xaf=ai["estimated_value_xaf"],
                created_by=request.user if request.user.is_authenticated else None,
                expires_at=timezone.now() + timezone.timedelta(days=7),
            )
            matching_businesses = list(_matching_businesses_for_request(created_request, limit=12))
            created_request.notified_count = len(matching_businesses)
            created_request.status = UnmetSearchRequest.Status.NOTIFIED if matching_businesses else UnmetSearchRequest.Status.NEW
            created_request.save(update_fields=["notified_count", "status", "updated_at"])
            provider_messages = [
                {
                    "business": business,
                    "text": _provider_unmet_message(created_request, business),
                    "whatsapp_url": business.whatsapp_url(_provider_unmet_message(created_request, business)),
                }
                for business in matching_businesses
                if business.clean_whatsapp_number
            ]
            messages.success(request, "Votre demande a ete enregistree. E-Shelle va la rendre visible aux prestataires concernes.")

    return render(
        request,
        "business/unmet_search_create.html",
        {
            "initial_query": initial_query,
            "initial_city": initial_city,
            "initial_district": initial_district,
            "detected_module": detected_module,
            "modules": BusinessProfile.Module.choices,
            "created_request": created_request,
            "matching_businesses": matching_businesses,
            "provider_messages": provider_messages,
            "capture_text": _customer_unmet_capture_text(initial_query),
            "external_links": _external_search_links(initial_query or "service Cameroun"),
        },
    )


@login_required
def unmet_search_requests(request):
    """Demandes clients visibles par les prestataires connectes."""
    my_businesses = BusinessProfile.objects.filter(owner=request.user, is_active=True).order_by("name")
    modules = list(my_businesses.values_list("module", flat=True).distinct())
    cities = [city for city in my_businesses.values_list("city", flat=True).distinct() if city]
    requests_qs = UnmetSearchRequest.objects.filter(
        status__in=[
            UnmetSearchRequest.Status.NEW,
            UnmetSearchRequest.Status.NOTIFIED,
            UnmetSearchRequest.Status.IN_PROGRESS,
        ],
        consent_share_contact=True,
    )

    rows = []
    for unmet_request in requests_qs.order_by("-created_at")[:80]:
        module_match = my_businesses.filter(module=unmet_request.module)
        city_match = module_match.filter(city__iexact=unmet_request.city) if unmet_request.city else module_match
        district_match = city_match.filter(district__icontains=unmet_request.district) if unmet_request.district else city_match
        matching_business = district_match.first() or city_match.first() or module_match.first()
        if not matching_business and unmet_request.module == BusinessProfile.Module.GENERAL:
            matching_business = my_businesses.first()
        response = None
        if matching_business:
            response = UnmetSearchResponse.objects.filter(request=unmet_request, business=matching_business).first()
        is_module_match = bool(matching_business and matching_business.module == unmet_request.module)
        is_city_match = bool(matching_business and (not unmet_request.city or matching_business.city.lower() == unmet_request.city.lower()))
        compatibility = "compatible" if is_module_match and is_city_match else "a verifier"
        if matching_business and is_module_match and not is_city_match:
            compatibility = "meme categorie"
        can_contact = bool(matching_business and (is_module_match or unmet_request.module == BusinessProfile.Module.GENERAL))
        contact_text = _provider_unmet_message(unmet_request, matching_business) if can_contact else ""
        partner_text = (
            "Bonjour, je vous contacte via E-Shelle au sujet de votre demande: "
            f"{unmet_request.query}. Pouvez-vous confirmer votre besoin et votre zone ?"
        )
        rows.append(
            {
                "request": unmet_request,
                "business": matching_business,
                "response": response,
                "whatsapp_url": f"https://wa.me/{unmet_request.clean_whatsapp_number}?text={urllib.parse.quote(contact_text)}" if unmet_request.clean_whatsapp_number and can_contact else "",
                "client_whatsapp_url": f"https://wa.me/{unmet_request.clean_whatsapp_number}?text={urllib.parse.quote(partner_text)}" if unmet_request.clean_whatsapp_number else "",
                "compatibility": compatibility,
            }
        )
    rows.sort(key=lambda row: {"compatible": 0, "meme categorie": 1, "a verifier": 2}.get(row["compatibility"], 3))

    return render(
        request,
        "business/unmet_search_requests.html",
        {
            "rows": rows,
            "my_businesses": my_businesses,
        },
    )


@login_required
def unmet_search_opportunities(request):
    """Pipeline commercial Search -> Demande -> Relance -> Conversion."""
    selected_status = request.GET.get("status", "").strip()
    selected_module = request.GET.get("module", "").strip()
    selected_priority = request.GET.get("priority", "").strip()

    qs = UnmetSearchRequest.objects.filter(consent_share_contact=True).select_related("assigned_partner", "created_by")
    if not request.user.is_staff:
        qs = qs.filter(models.Q(assigned_partner=request.user) | models.Q(assigned_partner__isnull=True))
    if selected_status:
        qs = qs.filter(status=selected_status)
    else:
        qs = qs.exclude(status__in=[UnmetSearchRequest.Status.EXPIRED, UnmetSearchRequest.Status.CANCELED])
    if selected_module:
        qs = qs.filter(module=selected_module)
    if selected_priority:
        qs = qs.filter(ai_priority=selected_priority)

    rows = []
    for unmet_request in qs.order_by("-lead_score", "-created_at")[:120]:
        partner_message = _notify_partner_text(unmet_request)
        client_message = _client_followup_text(unmet_request)
        matches = _opportunity_matches(unmet_request, limit=3)
        rows.append(
            {
                "request": unmet_request,
                "matches": matches,
                "needs_recruitment": not bool(matches),
                "partner_whatsapp_url": f"https://wa.me/?text={urllib.parse.quote(partner_message)}",
                "client_whatsapp_url": f"https://wa.me/{unmet_request.clean_whatsapp_number}?text={urllib.parse.quote(client_message)}" if unmet_request.clean_whatsapp_number else "",
            }
        )

    stats_base = UnmetSearchRequest.objects.filter(consent_share_contact=True)
    if not request.user.is_staff:
        stats_base = stats_base.filter(models.Q(assigned_partner=request.user) | models.Q(assigned_partner__isnull=True))
    stats = {
        "open": stats_base.exclude(status__in=[UnmetSearchRequest.Status.SOLD, UnmetSearchRequest.Status.LOST, UnmetSearchRequest.Status.CANCELED, UnmetSearchRequest.Status.EXPIRED]).count(),
        "new": stats_base.filter(status=UnmetSearchRequest.Status.NEW).count(),
        "contacted": stats_base.filter(status=UnmetSearchRequest.Status.CONTACTED).count(),
        "sold": stats_base.filter(status=UnmetSearchRequest.Status.SOLD).count(),
        "value": stats_base.exclude(status=UnmetSearchRequest.Status.LOST).aggregate(total=Sum("estimated_value_xaf"))["total"] or 0,
    }
    partners = get_user_model().objects.filter(
        models.Q(business_key_account__tier__in=[BusinessKeyAccount.Tier.KEY, BusinessKeyAccount.Tier.PRO])
        | models.Q(is_staff=True)
    ).distinct().order_by("username") if request.user.is_staff else []

    return render(
        request,
        "business/unmet_search_opportunities.html",
        {
            "rows": rows,
            "stats": stats,
            "partners": partners,
            "statuses": UnmetSearchRequest.Status.choices,
            "modules": BusinessProfile.Module.choices,
            "priorities": ["haute", "moyenne", "normal"],
            "filters": {"status": selected_status, "module": selected_module, "priority": selected_priority},
        },
    )


@staff_member_required
def eshelle_command_center(request):
    """Cockpit global du moteur de recherche et du reseau commercial E-Shelle."""
    days = _positive_int(request.GET.get("days"), 7)
    since = timezone.now() - timezone.timedelta(days=days)
    today = timezone.localdate()

    try:
        from e_shelle_ai.models import CentralAgentQueryLog
    except Exception:
        CentralAgentQueryLog = None

    requests_qs = UnmetSearchRequest.objects.filter(created_at__gte=since)
    open_requests = UnmetSearchRequest.objects.exclude(
        status__in=[
            UnmetSearchRequest.Status.SOLD,
            UnmetSearchRequest.Status.LOST,
            UnmetSearchRequest.Status.CANCELED,
            UnmetSearchRequest.Status.EXPIRED,
        ]
    )
    businesses = BusinessProfile.objects.filter(is_active=True)
    lead_events = BusinessLeadEvent.objects.filter(created_at__gte=since)

    query_logs = CentralAgentQueryLog.objects.filter(created_at__gte=since) if CentralAgentQueryLog else []
    query_count = query_logs.count() if CentralAgentQueryLog else 0
    no_result_count = query_logs.filter(had_results=False).count() if CentralAgentQueryLog else 0

    hot_requests = []
    for unmet_request in open_requests.order_by("-lead_score", "-created_at")[:12]:
        matches = _opportunity_matches(unmet_request, limit=3)
        hot_requests.append({"request": unmet_request, "matches": matches, "needs_recruitment": not bool(matches)})

    module_labels = dict(BusinessProfile.Module.choices)
    recruitment_rows = []
    for row in open_requests.values("module", "city").annotate(total=Count("id"), max_score=models.Max("lead_score")).order_by("-total", "-max_score")[:16]:
        provider_count = businesses.filter(module=row["module"], city__iexact=row["city"]).count() if row["city"] else businesses.filter(module=row["module"]).count()
        if provider_count == 0 or row["total"] >= 2:
            recruitment_rows.append(
                {
                    "module": row["module"],
                    "label": module_labels.get(row["module"], row["module"]),
                    "city": row["city"] or "Toutes zones",
                    "requests": row["total"],
                    "providers": provider_count,
                    "max_score": row["max_score"] or 0,
                }
            )

    module_demand = [
        {**row, "label": module_labels.get(row["module"], row["module"])}
        for row in open_requests.values("module").annotate(total=Count("id"), value=Sum("estimated_value_xaf")).order_by("-total")[:10]
    ]
    partner_accounts = BusinessKeyAccount.objects.select_related("user").filter(
        tier__in=[BusinessKeyAccount.Tier.KEY, BusinessKeyAccount.Tier.PRO],
        expires_at__gt=timezone.now(),
    )
    assigned_by_partner = (
        open_requests.exclude(assigned_partner__isnull=True)
        .values("assigned_partner__username")
        .annotate(total=Count("id"), sold=Count("id", filter=models.Q(status=UnmetSearchRequest.Status.SOLD)))
        .order_by("-total")[:10]
    )
    source_rows = (
        UnmetSearchRequest.objects.filter(created_at__gte=since)
        .values("source")
        .annotate(
            total=Count("id"),
            hot=Count("id", filter=models.Q(lead_score__gte=80)),
            value=Sum("estimated_value_xaf"),
        )
        .order_by("-total")[:10]
    )

    stats = {
        "days": days,
        "queries": query_count,
        "no_results": no_result_count,
        "captured": requests_qs.count(),
        "today_captured": UnmetSearchRequest.objects.filter(created_at__date=today).count(),
        "open": open_requests.count(),
        "hot": open_requests.filter(lead_score__gte=80).count(),
        "sold": UnmetSearchRequest.objects.filter(status=UnmetSearchRequest.Status.SOLD, updated_at__gte=since).count(),
        "pipeline_value": open_requests.aggregate(total=Sum("estimated_value_xaf"))["total"] or 0,
        "contacts": lead_events.filter(event_type__in=[BusinessLeadEvent.EventType.WHATSAPP, BusinessLeadEvent.EventType.PHONE, BusinessLeadEvent.EventType.ORDER]).count(),
        "active_partners": partner_accounts.count(),
        "providers": businesses.count(),
    }

    return render(
        request,
        "business/eshelle_command_center.html",
        {
            "stats": stats,
            "hot_requests": hot_requests,
            "recruitment_rows": recruitment_rows,
            "module_demand": module_demand,
            "assigned_by_partner": assigned_by_partner,
            "source_rows": source_rows,
            "recent_queries": query_logs[:12] if CentralAgentQueryLog else [],
            "days": days,
        },
    )


@login_required
@require_POST
def unmet_search_opportunity_action(request, request_id):
    unmet_request = get_object_or_404(UnmetSearchRequest, pk=request_id, consent_share_contact=True)
    if unmet_request.assigned_partner_id and unmet_request.assigned_partner_id != request.user.id and not request.user.is_staff:
        messages.error(request, "Cette opportunite est assignee a un autre partenaire.")
        return redirect("business:unmet_search_opportunities")

    status = request.POST.get("status", "").strip()
    if status in dict(UnmetSearchRequest.Status.choices):
        unmet_request.status = status
    note = request.POST.get("conversion_note", "").strip()
    if note:
        unmet_request.conversion_note = note
    if not unmet_request.assigned_partner_id:
        unmet_request.assigned_partner = request.user
    unmet_request.save(update_fields=["status", "conversion_note", "assigned_partner", "updated_at"])
    messages.success(request, "Opportunite mise a jour.")
    return redirect("business:unmet_search_opportunities")


@staff_member_required
@require_POST
def unmet_search_assign(request, request_id):
    unmet_request = get_object_or_404(UnmetSearchRequest, pk=request_id, consent_share_contact=True)
    partner_id = request.POST.get("partner_id")
    partner = get_user_model().objects.filter(pk=partner_id).first() if partner_id else None
    unmet_request.assigned_partner = partner
    if partner and unmet_request.status == UnmetSearchRequest.Status.NEW:
        unmet_request.status = UnmetSearchRequest.Status.NOTIFIED
    unmet_request.save(update_fields=["assigned_partner", "status", "updated_at"])
    messages.success(request, "Assignation mise a jour.")
    return redirect("business:unmet_search_opportunities")


@login_required
@require_POST
def unmet_search_request_action(request, request_id):
    unmet_request = get_object_or_404(UnmetSearchRequest, pk=request_id, consent_share_contact=True)
    business = BusinessProfile.objects.filter(pk=request.POST.get("business_id"), owner=request.user, is_active=True).first()
    if not business:
        messages.error(request, "Aucune fiche prestataire valide pour repondre a cette demande.")
        return redirect("business:unmet_search_requests")
    status = request.POST.get("status", UnmetSearchResponse.Status.CONTACTED)
    if status not in dict(UnmetSearchResponse.Status.choices):
        status = UnmetSearchResponse.Status.CONTACTED
    UnmetSearchResponse.objects.update_or_create(
        request=unmet_request,
        business=business,
        defaults={
            "responded_by": request.user,
            "status": status,
            "note": request.POST.get("note", "").strip(),
        },
    )
    if status == UnmetSearchResponse.Status.SATISFIED:
        unmet_request.status = UnmetSearchRequest.Status.SATISFIED
    else:
        unmet_request.status = UnmetSearchRequest.Status.IN_PROGRESS
    unmet_request.save(update_fields=["status", "updated_at"])
    messages.success(request, "Action enregistree.")
    return redirect("business:unmet_search_requests")


@login_required
def business_key_crm(request):
    """CRM simple pour suivre les prospects Business Key."""
    if request.method == "POST":
        business_name = request.POST.get("business_name", "").strip()
        if not business_name:
            messages.error(request, "Le nom du business est obligatoire.")
            return redirect("business:business_key_crm")
        PartnerCRMLead.objects.create(
            partner=request.user,
            business_name=business_name,
            contact_name=request.POST.get("contact_name", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            whatsapp=request.POST.get("whatsapp", "").strip(),
            city=request.POST.get("city", "").strip(),
            district=request.POST.get("district", "").strip(),
            sector=request.POST.get("sector") if request.POST.get("sector") in dict(PartnerCRMLead.Sector.choices) else PartnerCRMLead.Sector.OTHER,
            status=request.POST.get("status") if request.POST.get("status") in dict(PartnerCRMLead.Status.choices) else PartnerCRMLead.Status.NEW,
            potential_xaf=_positive_int(request.POST.get("potential_xaf"), 15000),
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, "Prospect ajoute au CRM partenaire.")
        return redirect("business:business_key_crm")

    status_filter = request.GET.get("status", "").strip()
    sector_filter = request.GET.get("sector", "").strip()
    leads = PartnerCRMLead.objects.filter(partner=request.user)
    if status_filter:
        leads = leads.filter(status=status_filter)
    if sector_filter:
        leads = leads.filter(sector=sector_filter)

    all_leads = PartnerCRMLead.objects.filter(partner=request.user)
    stats = {
        "total": all_leads.count(),
        "interested": all_leads.filter(status=PartnerCRMLead.Status.INTERESTED).count(),
        "follow_up": all_leads.filter(status=PartnerCRMLead.Status.FOLLOW_UP).count(),
        "converted": all_leads.filter(status=PartnerCRMLead.Status.CONVERTED).count(),
        "potential": all_leads.exclude(status=PartnerCRMLead.Status.REFUSED).aggregate(total=Sum("potential_xaf"))["total"] or 0,
    }
    prepared_leads = []
    for lead in leads[:80]:
        first_script = _crm_script_for_lead(lead)
        relances = []
        for script in FOLLOW_UP_SCRIPTS:
            text = script["text"].replace("{{nom}}", lead.contact_name or lead.business_name)
            relances.append({**script, "text": text, "whatsapp_url": lead.whatsapp_url(text)})
        prepared_leads.append(
            {
                "lead": lead,
                "first_script": first_script,
                "first_whatsapp_url": lead.whatsapp_url(first_script),
                "relances": relances,
            }
        )

    return render(
        request,
        "business/business_key_crm.html",
        {
            "leads": prepared_leads,
            "stats": stats,
            "statuses": PartnerCRMLead.Status.choices,
            "sectors": PartnerCRMLead.Sector.choices,
            "filters": {"status": status_filter, "sector": sector_filter},
            "follow_up_scripts": FOLLOW_UP_SCRIPTS,
        },
    )


@login_required
def business_key_crm_update(request, pk):
    lead = get_object_or_404(PartnerCRMLead, pk=pk, partner=request.user)
    if request.method != "POST":
        return redirect("business:business_key_crm")
    status = request.POST.get("status", "").strip()
    if status in dict(PartnerCRMLead.Status.choices):
        lead.status = status
    lead.notes = request.POST.get("notes", lead.notes).strip()
    next_follow_up = request.POST.get("next_follow_up_at", "").strip()
    lead.next_follow_up_at = next_follow_up or None
    lead.save(update_fields=["status", "notes", "next_follow_up_at", "updated_at"])
    messages.success(request, "Prospect mis a jour.")
    return redirect("business:business_key_crm")


@login_required
def business_key_crm_demo(request, pk):
    """Demo express a montrer au prospect."""
    lead = get_object_or_404(PartnerCRMLead, pk=pk, partner=request.user)
    card = _lead_sector_card(lead)
    first_script = _crm_script_for_lead(lead)
    activation_text = urllib.parse.quote(
        f"Bonjour E-Shelle, je veux activer {lead.business_name} apres la demo Business Key."
    )
    context = {
        "lead": lead,
        "card": card,
        "first_script": first_script,
        "whatsapp_url": lead.whatsapp_url(first_script),
        "activation_url": f"https://wa.me/237680625082?text={activation_text}",
        "price": "15 000 FCFA/mois" if lead.sector != PartnerCRMLead.Sector.IMMOBILIER else "30 000 FCFA/mois",
    }
    return render(request, "business/business_key_crm_demo.html", context)


@login_required
def business_key_crm_opportunities(request):
    """Vue argent: prospects chauds, potentiel et prochaines relances."""
    leads = PartnerCRMLead.objects.filter(partner=request.user)
    open_leads = leads.exclude(status__in=[PartnerCRMLead.Status.CONVERTED, PartnerCRMLead.Status.REFUSED])
    hot_leads = leads.filter(status__in=[PartnerCRMLead.Status.INTERESTED, PartnerCRMLead.Status.FOLLOW_UP]).order_by("next_follow_up_at", "-potential_xaf")[:20]
    due_leads = open_leads.filter(next_follow_up_at__lte=timezone.localdate()).order_by("next_follow_up_at")[:20]
    potential = open_leads.aggregate(total=Sum("potential_xaf"))["total"] or 0
    estimated_commission = int(potential * (BUSINESS_KEY_PROVIDER_RATE / 100))
    status_labels = dict(PartnerCRMLead.Status.choices)
    sector_labels = dict(PartnerCRMLead.Sector.choices)
    by_status = [
        {**row, "label": status_labels.get(row["status"], row["status"])}
        for row in open_leads.values("status").annotate(total=Count("id"), potential=Sum("potential_xaf")).order_by("status")
    ]
    by_sector = [
        {**row, "label": sector_labels.get(row["sector"], row["sector"])}
        for row in open_leads.values("sector").annotate(total=Count("id"), potential=Sum("potential_xaf")).order_by("-potential")
    ]
    return render(
        request,
        "business/business_key_crm_opportunities.html",
        {
            "total_open": open_leads.count(),
            "potential": potential,
            "estimated_commission": estimated_commission,
            "hot_leads": hot_leads,
            "due_leads": due_leads,
            "by_status": by_status,
            "by_sector": by_sector,
        },
    )


@login_required
def business_key_crm_create_campaign(request):
    """Cree une campagne WhatsApp depuis les prospects CRM selectionnes."""
    if request.method != "POST":
        return redirect("business:business_key_crm")
    ids = request.POST.getlist("lead_ids")
    leads = PartnerCRMLead.objects.filter(partner=request.user, pk__in=ids).exclude(status=PartnerCRMLead.Status.REFUSED)
    contacts = []
    try:
        from whatsapp_agent.models import Campagne, ContactWhatsApp
    except Exception:
        messages.error(request, "Le module WhatsApp n'est pas disponible.")
        return redirect("business:business_key_crm")

    for lead in leads:
        number = _normalize_cameroon_phone(lead.preferred_phone)
        if not number:
            continue
        contact, _ = ContactWhatsApp.objects.update_or_create(
            numero=number,
            defaults={
                "nom": lead.contact_name or lead.business_name,
                "ville": lead.city,
                "groupe": f"CRM {lead.get_sector_display()}",
                "source": ContactWhatsApp.SOURCE_MANUEL,
                "note": f"Prospect CRM Business Key: {lead.business_name}",
                "importe_par": request.user,
                "consentement_confirme": True,
            },
        )
        contacts.append(contact)

    if not contacts:
        messages.error(request, "Aucun prospect selectionne avec numero WhatsApp valide.")
        return redirect("business:business_key_crm")

    message_template = request.POST.get("message_template", "").strip() or (
        "Bonjour {{prenom}}, je reviens vers vous concernant E-Shelle. "
        "On peut vous aider a etre plus visible et recevoir plus de demandes WhatsApp. "
        "Voulez-vous une demo rapide ?"
    )
    campagne = Campagne.objects.create(
        nom=request.POST.get("campaign_name", "").strip() or f"CRM Business Key {timezone.now():%d/%m/%Y %H:%M}",
        description="Campagne creee depuis le CRM Partenaire Business Key.",
        message_template=message_template,
        statut=Campagne.STATUT_VALIDEE,
        filtre_role="crm_business_key",
        cree_par=request.user,
        total_destinataires=len(contacts),
    )
    campagne.destinataires_contacts.set(contacts)
    PartnerCRMLead.objects.filter(pk__in=[lead.pk for lead in leads]).update(status=PartnerCRMLead.Status.FOLLOW_UP)
    messages.success(request, f"Campagne WhatsApp creee avec {len(contacts)} prospect(s).")
    return redirect("whatsapp_agent:wa_detail", pk=campagne.pk)


@login_required
def business_key_payment_request(request):
    """Demande manuelle Mobile Money pour activer une Business Key."""
    if request.method != "POST":
        return redirect("business:business_key_packs")

    tier = request.POST.get("tier", "").strip()
    if tier != BusinessKeyAccount.Tier.KEY:
        messages.error(request, "La Business Key est maintenant une offre unique a 9 900 FCFA.")
        return redirect("business:business_key_packs")

    pack = BUSINESS_KEY_PACKS[tier]
    BusinessKeyPaymentRequest.objects.create(
        user=request.user,
        tier=tier,
        amount_xaf=pack["price"],
        momo_number=request.POST.get("momo_number", "").strip(),
        proof=request.FILES.get("proof"),
        note=request.POST.get("note", "").strip(),
    )
    messages.success(
        request,
        "Demande recue. Un administrateur verifiera le paiement Mobile Money et activera ta Business Key.",
    )
    return redirect("business:partner_dashboard")


@staff_member_required
def business_key_admin(request):
    """Interface staff simple pour valider les Business Key sans chercher dans Django Admin."""
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)
    pending = BusinessKeyPaymentRequest.objects.select_related("user").filter(
        status=BusinessKeyPaymentRequest.Status.PENDING
    )
    recent = BusinessKeyPaymentRequest.objects.select_related("user").exclude(
        status=BusinessKeyPaymentRequest.Status.PENDING
    )[:20]
    accounts = BusinessKeyAccount.objects.select_related("user")
    active_accounts = accounts.filter(
        tier__in=[BusinessKeyAccount.Tier.KEY, BusinessKeyAccount.Tier.PRO],
        expires_at__gt=timezone.now(),
    )
    commissions = Commission.objects.select_related("affiliate", "affiliate__user", "transaction")
    pending_commissions = commissions.filter(status="PENDING")
    provider_payments = PaymentRequest.objects.select_related("business", "plan", "requested_by")
    crm_leads = PartnerCRMLead.objects.select_related("partner")
    businesses = BusinessProfile.objects.select_related("owner")

    hot_leads = crm_leads.filter(
        status__in=[PartnerCRMLead.Status.INTERESTED, PartnerCRMLead.Status.FOLLOW_UP]
    ).order_by("next_follow_up_at", "-potential_xaf")[:10]
    unmet_requests = UnmetSearchRequest.objects.filter(
        status__in=[UnmetSearchRequest.Status.NEW, UnmetSearchRequest.Status.NOTIFIED, UnmetSearchRequest.Status.IN_PROGRESS]
    )
    recent_businesses = businesses.order_by("-created_at")[:10]
    recent_partners = active_accounts.order_by("-activated_at")[:10]
    top_commissions = (
        pending_commissions.values("affiliate__user__username")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")[:8]
    )

    stats = {
        "active_partners": active_accounts.count(),
        "pending_business_key_payments": pending.count(),
        "pending_provider_payments": provider_payments.filter(status=PaymentRequest.Status.PENDING).count(),
        "pending_commissions": pending_commissions.aggregate(total=Sum("amount"))["total"] or 0,
        "paid_commissions": commissions.filter(status="PAID").aggregate(total=Sum("amount"))["total"] or 0,
        "crm_hot": crm_leads.filter(status__in=[PartnerCRMLead.Status.INTERESTED, PartnerCRMLead.Status.FOLLOW_UP]).count(),
        "unmet_open": unmet_requests.count(),
        "new_businesses": businesses.filter(created_at__gte=since).count(),
        "converted_crm": crm_leads.filter(status=PartnerCRMLead.Status.CONVERTED).count(),
    }

    return render(
        request,
        "business/business_key_admin.html",
        {
            "pending": pending,
            "recent": recent,
            "stats": stats,
            "days": days,
            "recent_partners": recent_partners,
            "top_commissions": top_commissions,
            "hot_leads": hot_leads,
            "unmet_requests": unmet_requests.order_by("-created_at")[:10],
            "recent_businesses": recent_businesses,
            "provider_payment_requests": provider_payments.order_by("-created_at")[:10],
            "business_key_price": BUSINESS_KEY_PRICE_XAF,
            "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
            "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        },
    )


@staff_member_required
def business_key_admin_action(request, pk, action):
    payment = get_object_or_404(BusinessKeyPaymentRequest.objects.select_related("user"), pk=pk)
    if request.method != "POST":
        return redirect("business:business_key_admin")

    if action == "confirm":
        payment.confirm()
        messages.success(request, f"Business Key activee pour {payment.user}.")
    elif action == "cancel" and payment.status != BusinessKeyPaymentRequest.Status.CONFIRMED:
        payment.status = BusinessKeyPaymentRequest.Status.CANCELED
        payment.save(update_fields=["status"])
        messages.success(request, "Demande refusee.")
    else:
        messages.error(request, "Action impossible.")
    return redirect("business:business_key_admin")


def commercial(request):
    """Page publique pour recruter des commerciaux terrain."""
    return render(request, "business/commercial.html")


@staff_member_required
def commercial_admin_dashboard(request):
    """Dashboard staff pour suivre prospects, secteurs et campagnes premium."""
    selected_module = request.GET.get("module", "").strip()
    selected_status = request.GET.get("status", "").strip()
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)

    businesses = BusinessProfile.objects.order_by("-created_at")
    if selected_module:
        businesses = businesses.filter(module=selected_module)

    payment_requests = PaymentRequest.objects.select_related("business", "plan", "requested_by").order_by("-created_at")
    if selected_status:
        payment_requests = payment_requests.filter(status=selected_status)

    campaigns = PremiumSectorCampaign.objects.order_by("-starts_at")
    if selected_module:
        campaigns = campaigns.filter(module=selected_module)
    campaigns = campaigns[:12]

    module_pipeline = (
        businesses.values("module")
        .annotate(
            total=Count("id"),
            premium=Count("id", filter=models.Q(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM])),
            leads=Sum("leads_count"),
            views=Sum("views_count"),
        )
        .order_by("-total")
    )
    recent_leads = BusinessLeadEvent.objects.select_related("business").filter(created_at__gte=since).order_by("-created_at")
    if selected_module:
        recent_leads = recent_leads.filter(business__module=selected_module)
    recent_leads = recent_leads[:20]

    funnel = {
        "visitors": max(BusinessLeadEvent.objects.filter(created_at__gte=since, event_type=BusinessLeadEvent.EventType.VIEW).count(), 1),
        "contacts": BusinessLeadEvent.objects.filter(
            created_at__gte=since,
            event_type__in=[BusinessLeadEvent.EventType.WHATSAPP, BusinessLeadEvent.EventType.PHONE, BusinessLeadEvent.EventType.ORDER],
        ).count(),
        "requests": payment_requests.filter(created_at__gte=since).count(),
        "premium": businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
    }
    funnel["contacts_pct"] = round((funnel["contacts"] / funnel["visitors"]) * 100, 1)
    funnel["requests_pct"] = round((funnel["requests"] / funnel["visitors"]) * 100, 1)
    funnel["premium_pct"] = round((funnel["premium"] / max(businesses.count(), 1)) * 100, 1)

    context = {
        "total_businesses": businesses.count(),
        "premium_businesses": businesses.filter(plan__in=[BusinessProfile.Plan.BUSINESS, BusinessProfile.Plan.PREMIUM]).count(),
        "pending_payments": payment_requests.filter(status=PaymentRequest.Status.PENDING).count(),
        "total_leads": businesses.aggregate(total=Sum("leads_count"))["total"] or 0,
        "module_pipeline": module_pipeline,
        "payment_requests": payment_requests[:12],
        "campaigns": campaigns,
        "recent_leads": recent_leads,
        "funnel": funnel,
        "filters": {"module": selected_module, "status": selected_status, "days": days},
        "modules": BusinessProfile.Module.choices,
        "statuses": PaymentRequest.Status.choices,
    }
    return render(request, "business/commercial_admin_dashboard.html", context)


@login_required
def partner_dashboard(request):
    """Dashboard partenaire: lien, clics, inscrits, conversions, commissions."""
    profile = get_or_create_affiliate_profile(request.user)
    account = _get_business_key_account(request.user)
    referral_path = f"/ref/{profile.ref_code}/"
    referral_link = request.build_absolute_uri(referral_path)
    whatsapp_share_text = urllib.parse.quote(
        "Bonjour, je te partage E-Shelle Business Key. "
        "Tu peux gagner en aidant des commerces reels a trouver des clients en ligne: "
        f"{referral_link}"
    )
    whatsapp_share_url = f"https://wa.me/?text={whatsapp_share_text}"

    referrals = Referral.objects.filter(affiliate=profile).select_related("referred_user")
    referred_user_ids = list(referrals.values_list("referred_user_id", flat=True))
    converted_businesses = 0
    if referred_user_ids:
        from .models import BusinessProfile
        converted_businesses = BusinessProfile.objects.filter(owner_id__in=referred_user_ids).count()

    commissions = Commission.objects.filter(affiliate=profile)
    pending_amount = commissions.filter(status="PENDING").aggregate(total=Sum("amount"))["total"] or 0
    paid_amount = commissions.filter(status="PAID").aggregate(total=Sum("amount"))["total"] or 0
    total_commissions = commissions.aggregate(total=Sum("amount"))["total"] or 0
    recent_referrals = referrals.order_by("-created_at")[:8]
    conversion_rate = round((converted_businesses / max(referrals.count(), 1)) * 100, 1)

    missions = _business_key_missions(request.user, profile, referrals.count(), converted_businesses)
    scripts = [
        {
            "label": "Restaurant",
            "text": "Bonjour, je suis partenaire E-Shelle. On aide les restaurants a recevoir plus de commandes WhatsApp avec une fiche visible, menu, lien partageable et IA commerciale. Voulez-vous une demo rapide ?",
        },
        {
            "label": "Pressing",
            "text": "Bonjour, E-Shelle peut rendre votre pressing visible dans votre quartier et faciliter les demandes clients sur WhatsApp. Je peux vous montrer une fiche demo en 2 minutes.",
        },
        {
            "label": "Gaz / livraison",
            "text": "Bonjour, plusieurs clients cherchent du gaz rapidement par quartier. E-Shelle peut afficher votre service et envoyer les demandes vers WhatsApp. Voulez-vous tester ?",
        },
        {
            "label": "Partenaire",
            "text": "Tu peux gagner avec E-Shelle en aidant des business reels a etre visibles en ligne. Pas besoin de stock: tu recommandes, tu suis tes liens, et tu gagnes quand le client paie.",
        },
    ]
    tools = [
        ("Agent Commercial IA", "/commercial-agent/"),
        ("CRM Partenaire", "/business/partner/crm/"),
        ("Demandes clients", "/business/demandes/"),
        ("Opportunites E-Shelle", "/business/opportunites/"),
        ("Contacts WhatsApp", "/whatsapp/contacts/"),
        ("Campagnes WhatsApp", "/whatsapp/campagnes/"),
        ("Phone OCR", "/phone-ocr/"),
        ("Agent SEO IA", "/seo/"),
        ("Creer une fiche business", "/business/onboarding/?plan=free"),
    ]
    unlocked_tools = BUSINESS_KEY_FULL_TOOLS if account.is_active_paid else BUSINESS_KEY_PACKS[BusinessKeyAccount.Tier.FREE]["tools"]
    payment_requests = BusinessKeyPaymentRequest.objects.filter(user=request.user).order_by("-created_at")[:5]

    context = {
        "account": account,
        "profile": profile,
        "referral_link": referral_link,
        "whatsapp_share_url": whatsapp_share_url,
        "referrals_count": referrals.count(),
        "converted_businesses": converted_businesses,
        "pending_amount": pending_amount,
        "paid_amount": paid_amount,
        "balance_amount": pending_amount,
        "total_commissions": total_commissions,
        "conversion_rate": conversion_rate,
        "affiliate_rate_percent": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
        "partner_recruit_rate": BUSINESS_KEY_PARTNER_RECRUIT_RATE,
        "provider_rate": BUSINESS_KEY_PROVIDER_RATE,
        "business_key_price": BUSINESS_KEY_PRICE_XAF,
        "recent_referrals": recent_referrals,
        "commissions": commissions.order_by("-created_at")[:20],
        "missions": missions,
        "scripts": scripts,
        "tools": tools,
        "unlocked_tools": unlocked_tools,
        "packs": BUSINESS_KEY_PACKS,
        "payment_requests": payment_requests,
    }
    return render(request, "business/partner_dashboard.html", context)


@login_required
def onboarding(request):
    """Creation rapide d'une fiche business adaptee au terrain."""
    selected_plan = request.GET.get("plan") or request.POST.get("plan") or request.session.get("business_selected_plan", "free")
    plan = ProviderPlan.objects.filter(code=selected_plan, is_active=True).first() or ProviderPlan.objects.filter(code="free").first()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        module = request.POST.get("module", BusinessProfile.Module.GENERAL)
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        phone = request.POST.get("phone", "").strip()
        whatsapp = request.POST.get("whatsapp", "").strip()
        promo_headline = request.POST.get("promo_headline", "").strip()
        promo_offer = request.POST.get("promo_offer", "").strip()
        description = request.POST.get("description", "").strip()

        if not name or not phone:
            messages.error(request, "Le nom du business et le telephone sont obligatoires.")
        else:
            affiliate = get_affiliate_by_code(request.session.get("ref_code"))
            if affiliate:
                attach_referral_if_needed(request.user, affiliate, source="business_onboarding")
            business = BusinessProfile.objects.create(
                owner=request.user,
                module=module if module in dict(BusinessProfile.Module.choices) else BusinessProfile.Module.GENERAL,
                name=name,
                city=city,
                district=district,
                phone=phone,
                whatsapp=whatsapp or phone,
                promo_headline=promo_headline,
                promo_offer=promo_offer,
                description=description,
                logo=request.FILES.get("logo"),
                plan=BusinessProfile.Plan.FREE,
                is_active=True,
            )
            request.session["current_business_id"] = business.id
            request.session.modified = True
            messages.success(request, "Votre fiche business a ete creee. Choisissez maintenant comment activer votre plan.")
            if plan and plan.code != "free":
                return redirect(f"/business/payment/request/{business.id}/?plan={plan.code}")
            return redirect("business:dashboard")

    return render(
        request,
        "business/onboarding.html",
        {
            "plan": plan,
            "modules": BusinessProfile.Module.choices,
        },
    )


@login_required
def dashboard(request):
    businesses = BusinessProfile.objects.filter(owner=request.user).order_by("-updated_at")
    current_id = request.GET.get("business")
    current = businesses.filter(pk=current_id).first() if current_id else businesses.first()
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)
    pending_requests = PaymentRequest.objects.filter(requested_by=request.user).select_related("business", "plan")[:8]
    recent_events = []
    event_stats = []
    chart_stats = []
    marketing_pack = None
    public_url = ""
    share_whatsapp_url = ""
    whatsapp_url = ""
    if current:
        public_url = request.build_absolute_uri(current.get_absolute_url())
        share_text = f"Decouvrez {current.name} sur E-Shelle: {public_url}"
        share_whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(share_text)}"
        whatsapp_url = current.whatsapp_url(f"Bonjour {current.name}, je viens de votre boutique E-Shelle: {public_url}")
        filtered_events = current.lead_events.filter(created_at__gte=since)
        recent_events = filtered_events.order_by("-created_at")[:12]
        event_stats = (
            filtered_events.values("event_type")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        chart_stats = _event_chart_stats(event_stats)
        marketing_pack = _build_marketing_pack(current)
    return render(
        request,
        "business/dashboard.html",
        {
            "businesses": businesses,
            "current": current,
            "pending_requests": pending_requests,
            "plans": ProviderPlan.objects.filter(is_active=True).order_by("order"),
            "recent_events": recent_events,
            "event_stats": event_stats,
            "chart_stats": chart_stats,
            "marketing_pack": marketing_pack,
            "public_url": public_url,
            "share_whatsapp_url": share_whatsapp_url,
            "whatsapp_url": whatsapp_url,
            "filters": {"days": days, "business": current.id if current else ""},
        },
    )


@login_required
def catalog_manage(request, business_id):
    """Gestion rapide des produits/services visibles sur la fiche publique."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        item_type = request.POST.get("item_type", BusinessCatalogItem.ItemType.PRODUCT)
        description = request.POST.get("description", "").strip()
        price_label = request.POST.get("price_label", "").strip()
        order = _positive_int(request.POST.get("order"), 0)

        if not title:
            messages.error(request, "Le nom du produit ou service est obligatoire.")
        else:
            if item_type not in dict(BusinessCatalogItem.ItemType.choices):
                item_type = BusinessCatalogItem.ItemType.PRODUCT
            item = BusinessCatalogItem.objects.create(
                business=business,
                item_type=item_type,
                title=title,
                description=description,
                price_label=price_label,
                image=request.FILES.get("image"),
                order=order,
                is_active=True,
            )
            # handle additional photos
            extra_images = request.FILES.getlist("images")
            for img in extra_images:
                BusinessCatalogItemImage.objects.create(item=item, image=img)

            messages.success(request, "Produit/service ajoute sur la fiche publique.")
            return redirect("business:catalog_manage", business_id=business.id)

    items = business.catalog_items.all()
    public_url = request.build_absolute_uri(business.get_absolute_url())
    return render(
        request,
        "business/catalog_manage.html",
        {
            "business": business,
            "items": items,
            "public_url": public_url,
            "item_types": BusinessCatalogItem.ItemType.choices,
        },
    )


@login_required
@require_POST
def catalog_item_action(request, business_id, item_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    item = get_object_or_404(BusinessCatalogItem, pk=item_id, business=business)
    action = request.POST.get("action")
    if action == "toggle":
        item.is_active = not item.is_active
        item.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Visibilite du produit mise a jour.")
    elif action == "delete":
        item.delete()
        messages.success(request, "Produit/service supprime du catalogue.")
    else:
        messages.error(request, "Action catalogue inconnue.")
    return redirect("business:catalog_manage", business_id=business.id)


@login_required
def performance_report(request, business_id):
    """Rapport prestataire imprimable/partageable."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    days = _positive_int(request.GET.get("days"), 30)
    since = timezone.now() - timezone.timedelta(days=days)
    report_context = business_report_context(business, days)
    filtered_events = report_context["events"]
    events = filtered_events.order_by("-created_at")[:80]
    event_stats = filtered_events.values("event_type").annotate(total=Count("id")).order_by("-total")
    chart_stats = _event_chart_stats(event_stats)
    report_text = report_context["summary"]
    import urllib.parse
    whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(report_text)}"
    return render(
        request,
        "business/performance_report.html",
        {
            "business": business,
            "events": events,
            "event_stats": event_stats,
            "chart_stats": chart_stats,
            "report_text": report_text,
            "whatsapp_url": whatsapp_url,
            "days": days,
        },
    )


@login_required
def performance_report_pdf(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    days = _positive_int(request.GET.get("days"), 30)
    report_context = business_report_context(business, days)
    pdf = render_business_report_pdf(business, report_context)
    filename = f"rapport-e-shelle-{business.slug or business.id}-{days}j.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def ai_delivery_kit(request, business_id):
    """Atelier IA: kit complet pour livrer un client avec les agents E-Shelle."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    kit = getattr(business, "ai_delivery_kit", None)

    if request.method == "POST":
        extra_brief = request.POST.get("extra_brief", "")
        kit = generate_client_ai_kit(business, user=request.user, extra_brief=extra_brief)
        messages.success(request, "Kit IA client genere. Vous pouvez maintenant vendre/livrer ce pack.")
        return redirect("business:ai_delivery_kit", business_id=business.id)

    if not kit:
        kit = ClientAIKit.objects.create(business=business, created_by=request.user)

    whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(kit_summary_for_whatsapp(kit))}" if kit.generated_at else ""
    return render(
        request,
        "business/ai_delivery_kit.html",
        {
            "business": business,
            "kit": kit,
            "whatsapp_url": whatsapp_url,
        },
    )


def _event_chart_stats(event_stats):
    rows = list(event_stats)
    max_total = max([row["total"] for row in rows] or [1])
    return [
        {
            "label": row["event_type"],
            "total": row["total"],
            "percent": max(6, round((row["total"] / max_total) * 100)),
        }
        for row in rows
    ]


def _positive_int(value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number in {7, 30, 90, 365} else default


def _build_marketing_pack(business):
    offer = business.promo_offer or "une offre spéciale disponible aujourd'hui"
    location = ", ".join(part for part in [business.city, business.district] if part)
    location_text = f" à {location}" if location else ""
    name = business.name
    module = business.get_module_display()
    whatsapp = (
        f"Bonjour, profitez de {offer} chez {name}{location_text}. "
        "Répondez à ce message pour réserver ou commander via E-Shelle."
    )
    facebook = (
        f"{name} vous accueille{location_text}. {offer}. "
        f"Service {module}, contact rapide, visibilité E-Shelle et réponse directe sur WhatsApp."
    )
    status = f"{name} · {offer} · Commandez maintenant sur E-Shelle."
    carousel = [
        business.promo_headline or f"Découvrez {name}",
        offer,
        f"Disponible{location_text}",
        "Contact rapide via E-Shelle AI",
    ]
    return {
        "whatsapp": whatsapp,
        "facebook": facebook,
        "status": status,
        "carousel": carousel,
        "image_prompt": (
            f"Professional premium advertising visual for {name}, {module}, Cameroon market, "
            f"highlighting: {offer}. Clean modern layout, product/service in focus."
        ),
    }


@login_required
def payment_request(request, business_id):
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    plan_code = request.GET.get("plan") or request.POST.get("plan") or "business"
    plan = get_object_or_404(ProviderPlan, code=plan_code, is_active=True)

    if request.method == "POST":
        method = request.POST.get("method", PaymentRequest.Method.CASH_ON_DELIVERY)
        phone = request.POST.get("phone", business.whatsapp or business.phone)
        note = request.POST.get("note", "").strip()
        payment = PaymentRequest.objects.create(
            business=business,
            plan=plan,
            requested_by=request.user,
            method=method if method in dict(PaymentRequest.Method.choices) else PaymentRequest.Method.CASH_ON_DELIVERY,
            amount_xaf=plan.monthly_price_xaf,
            phone=phone,
            note=note,
        )
        business.activation_status = BusinessProfile.ActivationStatus.PENDING
        business.save(update_fields=["activation_status", "updated_at"])
        messages.success(request, "Demande envoyee. L'equipe E-Shelle vous contactera pour confirmer le paiement.")
        return redirect("business:payment_success", pk=payment.pk)

    return render(
        request,
        "business/payment_request.html",
        {
            "business": business,
            "plan": plan,
            "methods": PaymentRequest.Method.choices,
        },
    )


@login_required
def payment_success(request, pk):
    payment = get_object_or_404(PaymentRequest, pk=pk, requested_by=request.user)
    whatsapp_number = "237680625082"
    whatsapp_text = (
        f"Bonjour E-Shelle, j'ai envoye une demande d'activation pour {payment.business.name}. "
        f"Plan: {payment.plan.name}. Montant: {payment.amount_xaf} FCFA. "
        f"Reference demande: #{payment.pk}."
    )
    import urllib.parse
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(whatsapp_text)}"
    return render(
        request,
        "business/payment_success.html",
        {
            "payment": payment,
            "whatsapp_url": whatsapp_url,
        },
    )

@login_required
def business_edit(request, business_id):
    """Modification d'une fiche business existante."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        module = request.POST.get("module", BusinessProfile.Module.GENERAL)
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        phone = request.POST.get("phone", "").strip()
        whatsapp = request.POST.get("whatsapp", "").strip()
        promo_headline = request.POST.get("promo_headline", "").strip()
        promo_offer = request.POST.get("promo_offer", "").strip()
        description = request.POST.get("description", "").strip()
        promo_url = request.POST.get("promo_url", "").strip()

        if not name or not phone:
            messages.error(request, "Le nom du business et le telephone sont obligatoires.")
        else:
            business.name = name
            if module in dict(BusinessProfile.Module.choices):
                business.module = module
            business.city = city
            business.district = district
            business.phone = phone
            business.whatsapp = whatsapp or phone
            business.promo_headline = promo_headline
            business.promo_offer = promo_offer
            business.description = description
            business.promo_url = promo_url

            if "logo" in request.FILES:
                business.logo = request.FILES["logo"]
            if "promo_image" in request.FILES:
                business.promo_image = request.FILES["promo_image"]

            business.save()
            messages.success(request, "Votre fiche business a été mise à jour.")
            return redirect(f"/business/dashboard/?business={business.id}")

    return render(
        request,
        "business/business_edit.html",
        {
            "business": business,
            "modules": BusinessProfile.Module.choices,
        },
    )


@login_required
def catalog_item_edit(request, business_id, item_id):
    """Modification d'un produit/service et de ses photos supplementaires."""
    business = get_object_or_404(BusinessProfile, pk=business_id, owner=request.user)
    item = get_object_or_404(BusinessCatalogItem, pk=item_id, business=business)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        item_type = request.POST.get("item_type", BusinessCatalogItem.ItemType.PRODUCT)
        description = request.POST.get("description", "").strip()
        price_label = request.POST.get("price_label", "").strip()
        order = _positive_int(request.POST.get("order"), 0)

        delete_images_ids = request.POST.getlist("delete_images")

        if not title:
            messages.error(request, "Le nom du produit ou service est obligatoire.")
        else:
            if item_type not in dict(BusinessCatalogItem.ItemType.choices):
                item_type = BusinessCatalogItem.ItemType.PRODUCT
            item.title = title
            item.item_type = item_type
            item.description = description
            item.price_label = price_label
            item.order = order

            if "image" in request.FILES:
                item.image = request.FILES["image"]

            item.save()

            # Delete checked images
            if delete_images_ids:
                BusinessCatalogItemImage.objects.filter(item=item, id__in=delete_images_ids).delete()

            # Add new extra images
            extra_images = request.FILES.getlist("images")
            for img in extra_images:
                BusinessCatalogItemImage.objects.create(item=item, image=img)

            messages.success(request, "Produit/service mis à jour.")
            return redirect("business:catalog_manage", business_id=business.id)

    return render(
        request,
        "business/catalog_item_edit.html",
        {
            "business": business,
            "item": item,
            "item_types": BusinessCatalogItem.ItemType.choices,
        },
    )


from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

@staff_member_required
def ai_slide_generator_page(request):
    """Page d'administration pour generer des slides de presentation avec l'IA."""
    from .models import PresentationSlide, BusinessProfile
    
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        subtitle = request.POST.get("subtitle", "").strip()
        badge = request.POST.get("badge", "").strip()
        mockup_type = request.POST.get("mockup_type", "desktop")
        cta_label = request.POST.get("cta_label", "Visiter le site").strip()
        cta_url = request.POST.get("cta_url", "").strip()
        tech_stack = request.POST.get("tech_stack", "").strip()
        features = request.POST.get("features", "").strip()
        bg_gradient = request.POST.get("bg_gradient", "linear-gradient(135deg, #0f172a, #1e293b)").strip()
        text_color = request.POST.get("text_color", "#ffffff").strip()
        order = _positive_int(request.POST.get("order"), 0)
        is_active = request.POST.get("is_active") == "on" or request.POST.get("is_active") == "true" or request.POST.get("is_active") == True

        if not title:
            messages.error(request, "Le titre est obligatoire.")
        else:
            slide = PresentationSlide(
                title=title,
                subtitle=subtitle,
                badge=badge,
                mockup_type=mockup_type,
                cta_label=cta_label,
                cta_url=cta_url,
                tech_stack=tech_stack,
                features=features,
                bg_gradient=bg_gradient,
                text_color=text_color,
                order=order,
                is_active=is_active,
            )
            if "image" in request.FILES:
                slide.image = request.FILES["image"]
            
            slide.save()
            messages.success(request, f"Le slide '{title}' a été créé avec succès !")
            return redirect("admin:business_presentationslide_changelist")

    # GET request
    businesses = BusinessProfile.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "business/ai_slide_generator.html",
        {
            "businesses": businesses,
        }
    )


@csrf_exempt
@staff_member_required
@require_POST
def api_generate_slide_ai(request):
    """Endpoint API pour generer les specifications d'un slide via Claude AI."""
    from django.conf import settings
    from django.http import JsonResponse
    import anthropic

    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()
    except Exception:
        return JsonResponse({"success": False, "error": "JSON invalide"}, status=400)

    if not prompt:
        return JsonResponse({"success": False, "error": "Le prompt ne doit pas être vide"}, status=400)

    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        return JsonResponse({"success": False, "error": "Cle API Anthropic non configuree dans settings.py"}, status=500)

    system_instruction = (
        "Tu es un expert en marketing et UI designer pour E-Shelle, une agence web au Cameroun. "
        "Ton but est de concevoir un slide de présentation accrocheur pour présenter une maquette de site web. "
        "Génère des textes percutants adaptés au contexte camerounais et africain. "
        "Choisis un gradient de fond linear-gradient CSS très moderne (favorise le dark mode chic, e.g. indigo foncé, bleu nuit, forêt profond, pourpre, violet, doré, etc. de haute qualité) qui s'associe bien avec le domaine. "
        "Retourne UNIQUEMENT un objet JSON valide avec les clés suivantes :\n"
        "{\n"
        '  "title": "Nom court du projet / site",\n'
        '  "subtitle": "Slogan court de vente (max 150 caractères)",\n'
        '  "badge": "Catégorie (ex: Fintech, E-Commerce, Agri-Tech, Restauration)",\n'
        '  "cta_label": "Libellé d\'appel à l\'action (ex: Visiter le site)",\n'
        '  "cta_url": "Lien logique fictif ou réel (ex: /resto/ ou /agro/)",\n'
        '  "tech_stack": "Technologies clés séparées par des virgules (ex: Django, Postgres, TailwindCSS)",\n'
        '  "features": ["3 fonctionnalités phares concises"],\n'
        '  "bg_gradient": "linear-gradient(135deg, #hex1, #hex2)",\n'
        '  "text_color": "#ffffff",\n'
        '  "mockup_type": "Choix parmi: desktop, laptop, mobile"\n'
        "}\n"
        "Ne mets aucun bloc de code markdown, pas de ```json ou d'explications supplémentaires. Juste le JSON brut."
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Fallback cascade to avoid environment specific issues
        model = getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            system=system_instruction,
        )

        content_text = response.content[0].text.strip()
        
        # Clean potential markdown wrapping if Claude ignores prompt instructions
        if content_text.startswith("```"):
            lines = content_text.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content_text = "\n".join(lines[1:-1]).strip()
        
        slide_data = json.loads(content_text)
        return JsonResponse({"success": True, "slide": slide_data})

    except Exception as e:
        logger.exception("Erreur lors de l'appel Anthropic")
        return JsonResponse({"success": False, "error": f"Erreur IA : {str(e)}"}, status=500)

