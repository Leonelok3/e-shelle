import json
import logging
import re
import urllib.parse

from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def _track_actions(obj, module: str, urls: dict) -> dict:
    try:
        from business.services import build_tracked_actions

        return build_tracked_actions(
            obj,
            module,
            urls,
            source="central_agent",
            record_view=True,
        )
    except Exception as exc:
        logger.debug("Business tracking unavailable: %s", exc)
        return {}


MODULE_URLS = {
    "resto": "/resto/",
    "pressing": "/pressing/",
    "gaz": "/gaz/",
    "formation": "/formations/",
    "boutique": "/boutique/",
    "adgen": "/pub/",
    "transport": "https://simplo.e-shelle.com/",
    "auto": "/auto/",
    "services": "/artisans/",
    "sante": "/sante/",
    "immobilier": "/immobilier/",
    "jobs": "/jobs/",
    "njangi": "/njangi/",
    "fintech": "/billing/",
    "agro": "/agro/",
    "rencontres": "/rencontres/",
    "quincaillerie": "/boutique/?q=quincaillerie",
    "business_onboarding": "/business/onboarding/",
    "general": "/",
}

MODULE_LABELS = {
    "resto": "Voir les restaurants ->",
    "pressing": "Voir les pressings ->",
    "gaz": "Commander du gaz ->",
    "formation": "Voir les formations ->",
    "boutique": "Ouvrir la boutique ->",
    "adgen": "Créer un visuel ->",
    "transport": "Voir le transport ->",
    "auto": "Voir les véhicules ->",
    "services": "Voir les services ->",
    "sante": "Voir sante ->",
    "immobilier": "Voir les annonces ->",
    "jobs": "Voir les emplois ->",
    "njangi": "Ouvrir Njangi ->",
    "fintech": "Ouvrir les paiements ->",
    "agro": "Voir Agro ->",
    "rencontres": "Voir Rencontres ->",
    "quincaillerie": "Voir quincaillerie ->",
    "business_onboarding": "Inscrire mon business ->",
}

SYSTEM_PROMPT = """Tu es E-Shelle AI, l'assistant intelligent de la plateforme E-Shelle, une super-app africaine made in Cameroun.

Tu parles francais naturellement, avec une touche africaine chaleureuse. Tu es rapide, precis, utile.

Ta mission : comprendre ce que l'utilisateur veut, lui donner une reponse courte et le rediriger vers le bon module E-Shelle.

Modules disponibles :
- resto : restaurants, maquis, cafes au Cameroun
- pressing : nettoyage de vetements
- gaz : livraison de gaz domestique
- formation : cours en ligne, concours camerounais, certifications IA
- boutique : achat de produits, templates, ebooks, plugins
- adgen : generation d'affiches, logos, visuels marketing par IA
- transport : bus, taxis, covoiturage, livraison colis
- auto : achat, vente et location de voitures
- sante : medicaments, pharmacies, professionnels de sante
- immobilier : vente et location de terrains, maisons, appartements
- jobs : emplois, stages, missions freelance
- njangi : tontine digitale
- fintech : Mobile Money, paiement, transfert d'argent, microfinance
- agro : marche agricole B2B/B2C
- rencontres : rencontres serieuses
- quincaillerie : materiaux de construction, outillage
- general : aide, navigation, questions generales

Reponds toujours en JSON strict avec ce format :
{
  "module": "nom_du_module",
  "message": "Reponse naturelle en francais, 2 a 4 phrases max.",
  "redirect": true,
  "redirect_label": "Voir le module ->",
  "generate_image": false,
  "image_prompt": ""
}

Si l'utilisateur demande une affiche, un logo, un flyer, une banniere ou un visuel, choisis adgen et mets generate_image=true avec un prompt DALL-E en anglais.
Si l'utilisateur veut acceder a un service, mets redirect=true.
Ne reponds jamais hors JSON."""


def route_message(user_message: str, conversation_history: list) -> dict:
    """Route un message vers le bon module E-Shelle."""
    try:
        from e_shelle_ai.services.central_agent import CentralAgentService

        return CentralAgentService().route_message(user_message, conversation_history)
    except Exception as exc:
        logger.debug("Central agent unavailable, using legacy router: %s", exc)

    fallback = _fallback_route(user_message)
    fallback["results"] = _results_or_external(fallback["module"], user_message)
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return fallback

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in conversation_history[-10:]:
        role = msg.get("role")
        content = msg.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o"),
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=500,
            temperature=0.7,
        )
        result = json.loads(response.choices[0].message.content)
        result = _normalize_result(result, fallback)
        result["results"] = _results_or_external(result["module"], user_message)
        if result.get("generate_image") and result.get("image_prompt"):
            result["image_url"] = generate_image(result["image_prompt"])
        else:
            result["image_url"] = ""
        return result
    except Exception as exc:
        logger.exception("Chat router error: %s", exc)
        fallback["error"] = str(exc)
        return fallback


def generate_image(prompt: str) -> str:
    """Genere une image avec le modele image configure."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return ""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        enhanced_prompt = (
            "Professional African business marketing visual, Cameroon style, "
            f"vibrant colors. {prompt}. High quality, clean design."
        )
        response = client.images.generate(
            model=getattr(settings, "OPENAI_IMAGE_MODEL", "dall-e-3"),
            prompt=enhanced_prompt,
            size=getattr(settings, "OPENAI_IMAGE_SIZE", "1024x1024"),
            quality=getattr(settings, "OPENAI_IMAGE_QUALITY", "standard"),
            n=1,
        )
        return response.data[0].url
    except Exception as exc:
        logger.exception("Image generation error: %s", exc)
        return ""


def _normalize_result(result: dict, fallback: dict) -> dict:
    module = result.get("module") or fallback["module"]
    if module not in MODULE_URLS:
        module = fallback["module"]

    redirect = bool(result.get("redirect", module != "general"))
    normalized = {
        "module": module,
        "message": result.get("message") or fallback["message"],
        "redirect": redirect,
        "redirect_label": result.get("redirect_label") or MODULE_LABELS.get(module, ""),
        "generate_image": bool(result.get("generate_image", False)),
        "image_prompt": result.get("image_prompt", ""),
        "redirect_url": MODULE_URLS.get(module, "/"),
        "image_url": "",
        "results": fallback.get("results", []),
    }
    return normalized


def get_module_results(module: str, query: str, limit: int = 3) -> list:
    """Retourne des cartes actionnables depuis les donnees existantes."""
    builders = {
        "gaz": _gaz_results,
        "resto": _resto_results,
        "pressing": _pressing_results,
        "formation": _formation_results,
        "jobs": _jobs_results,
        "sante": _sante_results,
    }
    builder = builders.get(module)
    if not builder:
        return []
    try:
        return builder(query, limit)
    except Exception as exc:
        logger.exception("Module result error for %s: %s", module, exc)
        return []


def _results_or_external(module: str, query: str) -> list:
    results = get_module_results(module, query)
    if results:
        return results
    if module in {"adgen", "business_onboarding"}:
        return []
    if module == "general" and not _should_offer_external(query):
        return []
    return [_external_result_card(module, query)]


def _external_result_card(module: str, query: str) -> dict:
    label = MODULE_LABELS.get(module, "Continuer ->")
    if module == "transport":
        return {
            "title": "Simplo Transport",
            "subtitle": "Moto, taxi, transport et services terrain",
            "details": "Ce service est disponible sur Simplo. Ouvre le module transport pour continuer.",
            "badge": "Externe",
            "url": "https://simplo.e-shelle.com/",
            "primary_label": "Ouvrir Simplo",
            "primary_url": "https://simplo.e-shelle.com/",
            "secondary_label": "Recherche Google",
            "secondary_url": _google_search_url(query),
        }

    return {
        "title": "Recherche externe",
        "subtitle": "E-Shelle elargit encore ses resultats",
        "details": "Je n'ai pas encore assez de prestataires fiables dans ce module. Tu peux lancer une recherche externe en attendant.",
        "badge": "Bientot sur E-Shelle",
        "url": _google_search_url(query),
        "primary_label": label.replace("Voir", "Chercher").replace("->", "").strip() or "Chercher",
        "primary_url": _google_search_url(query),
        "secondary_label": "Inscrire un prestataire",
        "secondary_url": "/business/onboarding/",
    }


def _google_search_url(query: str) -> str:
    q = f"{query} Cameroun Douala"
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"


def _should_offer_external(query: str) -> bool:
    text = query.lower()
    triggers = ["cherche", "chercher", "trouve", "trouver", "besoin", "veux", "recherche"]
    return any(trigger in text for trigger in triggers) and bool(_search_terms(query))


def _gaz_results(query: str, limit: int) -> list:
    from gaz.models import DepotGaz

    qs = (
        DepotGaz.objects.filter(is_active=True)
        .select_related("ville", "quartier")
        .order_by("-is_featured", "-is_verified", "nom")
    )
    qs = _apply_location_filter(qs, query, "ville__nom", "quartier__nom", "adresse", "zone_livraison")

    cards = []
    for depot in qs[:limit]:
        details = []
        if depot.quartier:
            details.append(depot.quartier.nom)
        if depot.adresse:
            details.append(depot.adresse)
        price = _gaz_price_text(depot)
        if price:
            details.append(price)

        urls = {
            "url": f"/gaz/depot/{depot.slug}/",
            "primary_url": depot.whatsapp_url,
            "secondary_url": depot.tel_url,
        }
        urls.update(_track_actions(depot, "gaz", urls))
        cards.append(
            {
                "title": depot.nom,
                "subtitle": depot.ville.nom if depot.ville_id else "Depot de gaz",
                "details": " - ".join(details),
                "badge": "Verifie" if depot.is_verified else "Gaz",
                "url": urls["url"],
                "primary_label": "Commander",
                "primary_url": urls["primary_url"],
                "secondary_label": "Appeler",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _resto_results(query: str, limit: int) -> list:
    from resto.models import Restaurant

    qs = (
        Restaurant.objects.filter(is_active=True)
        .select_related("city", "neighborhood")
        .order_by("-is_featured", "-views_count", "name")
    )
    qs = _apply_location_filter(qs, query, "city__name", "neighborhood__name", "address")

    cards = []
    for resto in qs[:limit]:
        details = []
        if resto.neighborhood:
            details.append(resto.neighborhood.name)
        if getattr(resto, "delivery_available", False):
            details.append("Livraison")
        details.append(resto.status_label)

        urls = {
            "url": f"/resto/r/{resto.slug}/",
            "primary_url": resto.whatsapp_url(),
            "secondary_url": resto.phone_url(),
        }
        urls.update(_track_actions(resto, "resto", urls))
        cards.append(
            {
                "title": resto.name,
                "subtitle": resto.city.name if resto.city_id else "Restaurant",
                "details": " - ".join(details),
                "badge": resto.status_label,
                "url": urls["url"],
                "primary_label": "Commander",
                "primary_url": urls["primary_url"],
                "secondary_label": "Appeler",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _pressing_results(query: str, limit: int) -> list:
    from pressing.models import Pressing

    qs = (
        Pressing.objects.filter(is_active=True)
        .select_related("ville", "quartier")
        .order_by("-is_featured", "-is_verified", "nom")
    )
    qs = _apply_location_filter(qs, query, "ville__nom", "quartier__nom", "adresse", "zone_livraison")

    cards = []
    for pressing in qs[:limit]:
        details = []
        if pressing.quartier:
            details.append(pressing.quartier.nom)
        if pressing.express:
            details.append("Express")
        if getattr(pressing, "livraison", False) or getattr(pressing, "livraison_domicile", False):
            details.append("Collecte/livraison")

        urls = {
            "url": f"/pressing/p/{pressing.slug}/",
            "primary_url": pressing.whatsapp_url,
            "secondary_url": pressing.tel_url,
        }
        urls.update(_track_actions(pressing, "pressing", urls))
        cards.append(
            {
                "title": pressing.nom,
                "subtitle": pressing.ville.nom if pressing.ville_id else "Pressing",
                "details": " - ".join(details),
                "badge": "Verifie" if pressing.is_verified else "Pressing",
                "url": urls["url"],
                "primary_label": "Commander",
                "primary_url": urls["primary_url"],
                "secondary_label": "Appeler",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _formation_results(query: str, limit: int) -> list:
    from formations.models import Formation

    qs = (
        Formation.objects.filter(is_published=True)
        .select_related("categorie")
        .order_by("-is_featured", "titre")
    )
    focus_terms = [term for term in _search_terms(query) if term in {"enam", "ens", "bac", "concours"}]
    if focus_terms:
        focus_q = Q()
        for term in focus_terms:
            focus_q |= Q(titre__icontains=term) | Q(description__icontains=term) | Q(description_courte__icontains=term)
        focused = qs.filter(focus_q).distinct()
        if focused.exists():
            qs = focused
    qs = _apply_text_filter(qs, query, "titre", "description", "description_courte", "categorie__nom")

    cards = []
    for formation in qs[:limit]:
        details = []
        if formation.categorie_id:
            details.append(formation.categorie.nom)
        is_free = getattr(formation, "is_gratuite", getattr(formation, "est_gratuite", False))
        details.append("Gratuit" if is_free else _money_text(formation.prix))

        urls = {
            "url": f"/formations/{formation.slug}/",
            "primary_url": f"/formations/{formation.slug}/",
            "secondary_url": f"/formations/{formation.slug}/inscrire/",
        }
        cards.append(
            {
                "title": formation.titre,
                "subtitle": "Formation E-Shelle",
                "details": " - ".join([d for d in details if d]),
                "badge": formation.get_niveau_display() if hasattr(formation, "get_niveau_display") else "Cours",
                "url": urls["url"],
                "primary_label": "Voir le cours",
                "primary_url": urls["primary_url"],
                "secondary_label": "S'inscrire",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _jobs_results(query: str, limit: int) -> list:
    from jobs.models import OffreJob

    qs = (
        OffreJob.objects.filter(is_active=True)
        .select_related("ville", "secteur")
        .order_by("-is_featured", "-created_at")
    )
    qs = _apply_location_filter(qs, query, "ville__nom", "quartier")
    qs = _apply_text_filter(qs, query, "titre", "entreprise", "description", "secteur__nom")

    cards = []
    for job in qs[:limit]:
        details = []
        if job.ville_id:
            details.append(job.ville.nom)
        if job.quartier:
            details.append(job.quartier)
        details.append(job.get_type_contrat_display())
        details.append(job.salaire_display)

        urls = {
            "url": job.get_absolute_url(),
            "primary_url": job.whatsapp_url if (job.whatsapp or job.telephone) else job.get_absolute_url(),
            "secondary_url": job.get_absolute_url(),
        }
        urls.update(_track_actions(job, "jobs", urls))
        cards.append(
            {
                "title": job.titre,
                "subtitle": job.entreprise,
                "details": " - ".join([d for d in details if d]),
                "badge": job.get_mode_travail_display(),
                "url": urls["url"],
                "primary_label": "Postuler",
                "primary_url": urls["primary_url"],
                "secondary_label": "Details",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _sante_results(query: str, limit: int) -> list:
    product_cards = _sante_product_results(query, limit)
    pro_cards = _sante_professional_results(query, limit)
    if _location_terms(query):
        return (pro_cards + product_cards)[:limit]
    combined = product_cards + pro_cards
    return combined[:limit]


def _sante_product_results(query: str, limit: int) -> list:
    from sante.models import ProduitSante

    qs = (
        ProduitSante.objects.filter(is_active=True)
        .select_related("ville", "categorie")
        .order_by("-is_featured", "-is_verified", "-created_at")
    )
    qs = _apply_location_filter(qs, query, "ville__nom")
    qs = _apply_text_filter(qs, query, "titre", "description", "categorie__nom", "vendeur_nom")

    cards = []
    for produit in qs[:limit]:
        details = []
        if produit.ville_id:
            details.append(produit.ville.nom)
        if produit.categorie_id:
            details.append(produit.categorie.nom)
        details.append(produit.prix_display)

        urls = {
            "url": produit.get_absolute_url(),
            "primary_url": produit.commande_whatsapp_url,
            "secondary_url": produit.tel_url,
        }
        urls.update(_track_actions(produit, "sante", urls))
        cards.append(
            {
                "title": produit.titre,
                "subtitle": produit.vendeur_nom,
                "details": " - ".join([d for d in details if d]),
                "badge": "Produit sante",
                "url": urls["url"],
                "primary_label": "Commander",
                "primary_url": urls["primary_url"],
                "secondary_label": "Appeler",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _sante_professional_results(query: str, limit: int) -> list:
    from sante.models import ProfessionnelSante

    qs = (
        ProfessionnelSante.objects.filter(is_active=True)
        .select_related("ville")
        .prefetch_related("specialites")
        .order_by("-is_featured", "-is_verified", "nom")
    )
    qs = _apply_location_filter(qs, query, "ville__nom", "quartier", "adresse")
    qs = _apply_text_filter(qs, query, "nom", "description", "specialites__nom")

    cards = []
    for pro in qs[:limit]:
        specialites = [s.nom for s in pro.specialites.all()[:2]]
        details = []
        if pro.ville_id:
            details.append(pro.ville.nom)
        if pro.quartier:
            details.append(pro.quartier)
        details.extend(specialites)

        urls = {
            "url": f"/sante/professionnel/{pro.slug}/",
            "primary_url": pro.whatsapp_url,
            "secondary_url": pro.tel_url,
        }
        urls.update(_track_actions(pro, "sante", urls))
        cards.append(
            {
                "title": pro.nom,
                "subtitle": pro.get_type_pro_display(),
                "details": " - ".join([d for d in details if d]),
                "badge": "Verifie" if pro.is_verified else "Sante",
                "url": urls["url"],
                "primary_label": "WhatsApp",
                "primary_url": urls["primary_url"],
                "secondary_label": "Appeler",
                "secondary_url": urls["secondary_url"],
            }
        )
    return cards


def _apply_location_filter(qs, query: str, *fields):
    terms = _location_terms(query)
    if not terms:
        return qs

    for term in terms:
        exact_q = Q()
        for field in fields:
            exact_q |= Q(**{f"{field}__iexact": term})
        exact = qs.filter(exact_q).distinct()
        if exact.exists():
            return exact

    broad_q = Q()
    for term in terms:
        for field in fields:
            broad_q |= Q(**{f"{field}__icontains": term})

    matched = qs.filter(broad_q).distinct()
    return matched if matched.exists() else qs


def _apply_text_filter(qs, query: str, *fields):
    terms = _search_terms(query)
    if not terms:
        return qs

    text_q = Q()
    for term in terms:
        for field in fields:
            text_q |= Q(**{f"{field}__icontains": term})

    matched = qs.filter(text_q).distinct()
    return matched if matched.exists() else qs


def _location_terms(query: str) -> list:
    text = query.lower()
    patterns = [
        r"(?:a|à|pres de|près de|proche de|vers|quartier|au quartier)\s+([a-zA-ZÀ-ÿ0-9' -]{3,})",
    ]
    terms = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            cleaned = _clean_term(match)
            if cleaned:
                terms.append(cleaned)

    terms.extend(
        term for term in _search_terms(query)
        if term not in _INTENT_WORDS and len(term) >= 4
    )
    return _unique(terms)


def _search_terms(query: str) -> list:
    raw = re.findall(r"[a-zA-ZÀ-ÿ0-9']+", query.lower())
    return _unique([w for w in raw if len(w) >= 4 and w not in _STOP_WORDS])


def _clean_term(value: str) -> str:
    value = re.split(r"\b(?:pour|avec|ce soir|aujourd'hui|demain|svp|merci)\b", value, maxsplit=1)[0]
    value = value.strip(" ,.;:!?()[]'\"")
    if value == "bonaberie":
        value = "bonaberi"
    return value if len(value) >= 3 else ""


def _unique(values: list) -> list:
    seen = set()
    unique_values = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _gaz_price_text(depot) -> str:
    prices = []
    if depot.prix_6kg:
        prices.append(f"6kg {depot.prix_6kg:,} FCFA")
    if depot.prix_12kg:
        prices.append(f"12kg {depot.prix_12kg:,} FCFA")
    if depot.prix_15kg:
        prices.append(f"15kg {depot.prix_15kg:,} FCFA")
    return " / ".join(prices).replace(",", " ")


def _money_text(value) -> str:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return "Gratuit"
    return f"{amount:,} FCFA".replace(",", " ")


_STOP_WORDS = {
    "veux", "cherche", "trouve", "moi", "pour", "avec", "dans", "chez",
    "soir", "aujourd", "hui", "demain", "besoin", "avoir", "faire",
    "commander", "acheter", "preparer", "préparer", "près", "pres",
}

_INTENT_WORDS = {
    "gaz", "restaurant", "resto", "maquis", "formation", "cours", "concours",
    "pressing", "emploi", "jobs", "stage", "travail", "sante", "santé",
    "pharmacie", "medicament", "médicament", "medecin", "médecin",
    "service", "services", "plombier", "electricien", "électricien", "artisan",
    "auto", "voiture", "vehicule", "véhicule",
}


def _fallback_route(user_message: str) -> dict:
    text = user_message.lower()
    module = "general"
    image = False

    rules = [
        ("adgen", ["affiche", "logo", "flyer", "visuel", "banniere", "bannière", "poster", "design", "pub", "publicite", "publicité", "post facebook", "campagne"]),
        ("business_onboarding", ["inscrire mon", "inscrire ma", "ajouter mon", "ajouter ma", "referencer mon", "référencer mon", "publier mon business", "vendre sur e-shelle", "devenir prestataire"]),
        ("boutique", ["template", "ebook", "plugin", "outil digital"]),
        ("gaz", ["gaz", "bouteille", "butane", "propane"]),
        ("resto", ["restaurant", "resto", "maquis", "manger", "plat", "nourriture"]),
        ("formation", ["formation", "cours", "concours", "enam", "ens", "apprendre", "certification"]),
        ("pressing", ["pressing", "linge", "vetement", "vêtement", "blanchisserie"]),
        ("auto", ["auto", "voiture", "vehicule", "véhicule", "car", "occasion", "acheter voiture", "louer voiture"]),
        ("transport", ["transport", "taxi", "moto", "moto taxi", "mototaxi", "benskin", "bend skin", "okada", "bus", "covoiturage", "colis", "livraison"]),
        ("services", ["plombier", "electricien", "électricien", "menuisier", "macon", "maçon", "peintre", "technicien", "reparateur", "réparateur", "artisan", "service a domicile", "service à domicile"]),
        ("sante", ["sante", "santé", "pharmacie", "medicament", "médicament", "medecin", "médecin"]),
        ("immobilier", ["terrain", "maison", "appartement", "logement", "studio", "chambre", "loyer", "location", "immobilier"]),
        ("jobs", ["emploi", "job", "stage", "travail", "freelance", "mission"]),
        ("njangi", ["njangi", "tontine", "cotisation", "investir"]),
        ("fintech", ["argent", "payer", "paiement", "mobile money", "transfert", "microfinance"]),
        ("agro", ["agro", "agriculture", "producteur", "recolte", "récolte", "vivres"]),
        ("rencontres", ["rencontre", "amour", "mariage", "relation"]),
        ("quincaillerie", ["quincaillerie", "ciment", "fer", "tole", "tôle", "outillage", "construction"]),
        ("boutique", ["acheter", "produit", "boutique", "magasin", "shop", "template", "ebook", "plugin", "outil"]),
    ]

    for candidate, keywords in rules:
        if any(keyword in text for keyword in keywords):
            module = candidate
            break

    if module == "adgen":
        image = True

    message = _fallback_message(module)
    return {
        "module": module,
        "message": message,
        "redirect": module != "general",
        "redirect_label": MODULE_LABELS.get(module, ""),
        "generate_image": image,
        "image_prompt": user_message if image else "",
        "redirect_url": MODULE_URLS.get(module, "/"),
        "image_url": "",
        "results": [],
    }


def _fallback_message(module: str) -> str:
    messages = {
        "adgen": "Oui, on peut creer un visuel professionnel pour ton business. Je t'ouvre l'espace creation IA pour lancer l'affiche avec les bons details.",
        "gaz": "Parfait, je t'oriente vers les fournisseurs de gaz disponibles. Tu pourras choisir un depot et passer rapidement a l'action.",
        "resto": "Bonne idee. Je t'envoie vers E-Shelle Resto pour voir les restaurants, maquis et plats disponibles.",
        "formation": "Bien vu. Je t'oriente vers les formations et ressources pour apprendre ou preparer ton concours serieusement.",
        "transport": "C'est note. Pour les motos, taxis et transports, je t'oriente vers Simplo Transport, le module dedie d'E-Shelle.",
        "auto": "Parfait. Je te montre les vehicules disponibles sur E-Shelle Auto avec les contacts utiles pour avancer vite.",
        "services": "C'est note. Je t'oriente vers les services et artisans. Si E-Shelle n'a pas encore de prestataire disponible, je te propose une recherche externe en attendant.",
        "immobilier": "D'accord. Je t'oriente vers les annonces immobilieres et logements disponibles. Si E-Shelle n'a pas encore assez de resultats, je te propose aussi une recherche externe.",
        "general": "Dis-moi simplement ce que tu cherches: gaz, resto, formation, emploi, sante, transport ou creation d'affiche. Je te dirige au bon endroit.",
        "business_onboarding": "Tres bien. Vous pouvez inscrire votre business sur E-Shelle, recevoir des clients via WhatsApp et suivre vos demandes. Je vous ouvre la page pour creer votre fiche.",
    }
    return messages.get(module, "C'est note. Je t'oriente vers le bon module E-Shelle pour avancer rapidement.")
