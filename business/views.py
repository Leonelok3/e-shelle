import urllib.parse

from django.contrib.admin.views.decorators import staff_member_required
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
    DEFAULT_AFFILIATE_RATE,
    attach_referral_if_needed,
    get_affiliate_by_code,
    get_or_create_affiliate_profile,
)

from .models import (
    AppCommission,
    BusinessKeyAccount,
    BusinessKeyPaymentRequest,
    BusinessCatalogItem,
    BusinessLeadEvent,
    BusinessProfile,
    HomeAdSlide,
    PaymentRequest,
    PartnerCRMLead,
    PartnerLevel,
    PremiumSectorCampaign,
    ProviderPlan,
)
from .reporting import business_report_context, render_business_report_pdf
from .services import collect_business_items, create_tracking_event, record_event_hit


BUSINESS_KEY_PACKS = {
    BusinessKeyAccount.Tier.FREE: {
        "name": "Gratuit",
        "price": 0,
        "label": "Demarrer sans argent",
        "desc": "Lien partenaire, scripts de base et acces aux outils publics pour commencer.",
        "tools": ["Lien partenaire", "Scripts WhatsApp", "Dashboard commissions", "Phone OCR local"],
    },
    BusinessKeyAccount.Tier.KEY: {
        "name": "Business Key",
        "price": 5000,
        "label": "Pack recommande",
        "desc": "La methode complete pour prospecter, importer des contacts, creer des campagnes et vendre E-Shelle.",
        "tools": ["Missions avancees", "Scripts premium", "Agent Commercial IA", "Contacts WhatsApp", "Pages SEO locales"],
    },
    BusinessKeyAccount.Tier.PRO: {
        "name": "Ambassadeur Pro",
        "price": 10000,
        "label": "Equipe terrain",
        "desc": "Pour organiser une petite force commerciale locale et suivre les opportunites par ville.",
        "tools": ["Pipeline prioritaire", "Scripts equipe", "Campagnes par ville", "Reporting", "Support prioritaire"],
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
    ]
    return render(request, "business/partner.html", {"proof": proof, "packs": packs, "account": account})


def business_key_packs(request):
    """Page claire des prix Business Key."""
    account = _get_business_key_account(request.user)
    packs = [
        {"tier": tier, **data}
        for tier, data in BUSINESS_KEY_PACKS.items()
    ]
    return render(request, "business/business_key_packs.html", {"packs": packs, "account": account})


def business_key_how_to_earn(request):
    """Page pedagogique: comment gagner proprement avec E-Shelle."""
    return render(request, "business/business_key_how_to_earn.html")


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
        ("Business", "15 000 FCFA/mois", "Visibilite, leads WhatsApp, IA commerciale"),
        ("Premium", "30 000 FCFA/mois", "Boost, priorite locale, contenu et campagnes"),
        ("Business Key", "5 000 FCFA", "Pack partenaire pour vendre E-Shelle"),
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
        },
    )


@login_required
def catalogue_commissions(request):
    """Catalogue de toutes les apps E-Shelle vendables par un partenaire."""
    apps = AppCommission.objects.filter(is_active=True).order_by("priority", "app_name")
    levels = PartnerLevel.objects.filter(is_active=True).prefetch_related("apps_accessibles").order_by("prix_fcfa", "level")
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
    estimated_commission = int(potential * float(DEFAULT_AFFILIATE_RATE))
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
    if tier not in {BusinessKeyAccount.Tier.KEY, BusinessKeyAccount.Tier.PRO}:
        messages.error(request, "Choisis un pack payant valide.")
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
    pending = BusinessKeyPaymentRequest.objects.select_related("user").filter(
        status=BusinessKeyPaymentRequest.Status.PENDING
    )
    recent = BusinessKeyPaymentRequest.objects.select_related("user").exclude(
        status=BusinessKeyPaymentRequest.Status.PENDING
    )[:20]
    return render(request, "business/business_key_admin.html", {"pending": pending, "recent": recent})


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
        ("Contacts WhatsApp", "/whatsapp/contacts/"),
        ("Campagnes WhatsApp", "/whatsapp/campagnes/"),
        ("Phone OCR", "/phone-ocr/"),
        ("Agent SEO IA", "/seo/"),
        ("Creer une fiche business", "/business/onboarding/?plan=free"),
    ]
    unlocked_tools = BUSINESS_KEY_PACKS[account.tier]["tools"]
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
        "affiliate_rate_percent": int(DEFAULT_AFFILIATE_RATE * 100),
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
            BusinessCatalogItem.objects.create(
                business=business,
                item_type=item_type,
                title=title,
                description=description,
                price_label=price_label,
                image=request.FILES.get("image"),
                order=order,
                is_active=True,
            )
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

# Create your views here.
