"""Conservative prompts and helpers for E-Shelle Facebook post previews.

This module only prepares draft content. It does not publish to Facebook.
"""

import json
import re
from urllib.parse import urlencode
from django.db.models import Count

from ai_engine.services.llm_service import call_llm
from django.utils import timezone


def facebook_campaign_url(url, campaign):
    separator = "&" if "?" in url else "?"
    params = urlencode({"utm_source": "facebook", "utm_medium": "agent", "utm_campaign": campaign})
    return f"{url}{separator}{params}"


PROMPT_GLOBAL_FACEBOOK_AGENT = """
Tu es l'agent de contenu Facebook d'E-Shelle, une marketplace camerounaise.
Rédige des brouillons courts, clairs et vendeurs à partir des seules données fournies.

Règles:
- N'invente jamais prix, stock, ancienneté, livraison, qualité, avis, disponibilité ou
  comparaison de prix. N'affirme une photo réelle que si les données le confirment.
- Utilise la langue demandée quand elle est prise en charge. Pour pidgin, écris simplement
  en pidgin camerounais sans inventer d'expressions ou de faits. Pour ewondo et bassa,
  utilise le français tant qu'une traduction relue n'est pas fournie.
- Maximum 300 caractères pour le texte principal et 3 hashtags au maximum.
- Commence par un emoji pertinent.
- Garde l'URL de destination séparée du texte principal: elle sera destinée au premier
  commentaire Facebook. N'insère pas cette URL dans le texte principal.
- Termine par un CTA WhatsApp seulement si un lien ou numéro WhatsApp réel est fourni;
  sinon termine par un CTA invitant à consulter la fiche E-Shelle.
- Ne génère pas de témoignage, d'histoire personnelle, de certification ou d'allégation
  de conformité sans donnée explicite.
- Retourne uniquement un objet JSON valide avec les clés "text", "first_comment",
  "image_prompt" et "warnings". "warnings" est une liste de chaînes.
""".strip()


def business_created_payload(business):
    """Build a minimal, factual prompt payload from a saved BusinessProfile."""
    url = facebook_campaign_url(business.get_absolute_url(), f"business_{business.pk}")
    whatsapp = business.whatsapp_url() if (business.whatsapp or business.phone) else ""
    return {
        "type": "business_created",
        "business": {
            "name": business.display_name,
            "city": business.city,
            "district": business.district,
            "country": business.country,
            "category": business.display_module,
            "description": business.display_description,
            "language": business.language,
            "whatsapp_url": whatsapp,
            "profile_url": url,
            "has_promo_image": bool(business.promo_image),
            "has_logo": bool(business.logo),
        },
    }


def generate_business_created_draft(business):
    """Return a structured draft; never call the Facebook publishing API."""
    payload = business_created_payload(business)
    return _generate_draft(payload, fallback_url=payload["business"]["profile_url"])


def _generate_draft(payload, *, fallback_url, max_chars=300):
    result = call_llm(
        PROMPT_GLOBAL_FACEBOOK_AGENT,
        "Génère un brouillon Facebook court pour ces données. Retourne le JSON demandé.\n"
        + json.dumps(payload, ensure_ascii=False, default=str),
        max_tokens=500,
    )
    try:
        parsed = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Le fournisseur IA n'a pas retourné le JSON attendu.") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("text"), str):
        raise ValueError("Le brouillon IA ne contient pas de texte exploitable.")
    if len(parsed["text"]) > max_chars:
        raise ValueError(f"Le brouillon dépasse {max_chars} caractères; régénérez-le avant de l'enregistrer.")
    parsed.setdefault("first_comment", fallback_url)
    parsed.setdefault("image_prompt", "")
    parsed.setdefault("warnings", [])
    if not isinstance(parsed["warnings"], list):
        parsed["warnings"] = []
    if len(re.findall(r"(?<!\w)#[\wÀ-ÿ]+", parsed["text"])) > 3:
        parsed["warnings"].append("Le brouillon contient plus de trois hashtags; corrigez-le avant enregistrement.")
    language = (payload.get("business") or {}).get("language")
    if language in {"ewondo", "bassa"}:
        parsed["warnings"].append("Langue locale non vérifiée : le brouillon est demandé en français.")
    return parsed


def generate_product_draft(item):
    business = item.business
    url = facebook_campaign_url(item.business.get_absolute_url(), f"product_{item.pk}")
    return _generate_draft({
        "type": "product_created",
        "business": {"name": business.display_name, "city": business.city,
                     "country": business.country,
                     "language": business.language,
                     "whatsapp_url": business.whatsapp_url() if (business.whatsapp or business.phone) else ""},
        "product": {"name": item.display_title, "category": item.category,
                    "description": item.display_description, "price": item.display_price_label,
                    "stock": item.stock_quantity, "image_available": bool(item.image)},
        "rules": {"stock_claims_only_if_present": True, "no_price_comparison_without_evidence": True},
    }, fallback_url=url)


def generate_njangi_draft(group):
    product = group.product
    business = product.business
    # NjangiAchatGroupe is a product group-buy record, not a tontine Group;
    # link to the public Njangi landing page until a public detail route exists.
    url = facebook_campaign_url("https://e-shelle.com/njangi/", f"njangi_{group.pk}")
    return _generate_draft({
        "type": "njangi_launched",
        "business": {"name": business.display_name, "city": business.city,
                     "country": business.country,
                     "language": business.language},
        "product": {"name": product.display_title, "price_normal": product.display_price_label},
        "njangi": {"price_normal": group.prix_normal, "price_njangi": group.prix_njangi,
                   "savings_per_unit": group.prix_normal - group.prix_njangi,
                   "participants": group.quantite_actuelle, "target": group.quantite_cible,
                   "status": group.get_status_display(), "closing_at": group.date_cloture},
        "rules": {"do_not_claim_all_participants_are_individuals": True},
    }, fallback_url=url)


def generate_daily_summary_draft():
    from business.models import BusinessCatalogItem, BusinessLeadEvent, BusinessProfile
    from njangi.models import NjangiAchatGroupe

    since = timezone.localdate()
    businesses = BusinessProfile.objects.filter(is_active=True, created_at__date=since)
    products = BusinessCatalogItem.objects.filter(is_active=True, created_at__date=since)
    top = (BusinessLeadEvent.objects.filter(created_at__date=since, event_type=BusinessLeadEvent.EventType.WHATSAPP)
           .values("business_id", "business__name")
           .annotate(views=Count("id"))
           .order_by("-views").first())
    active_groups = NjangiAchatGroupe.objects.filter(status=NjangiAchatGroupe.Status.OPEN)
    url = facebook_campaign_url("https://e-shelle.com/", "daily_summary")
    return _generate_draft({
        "type": "daily_summary",
        "daily": {
            "business_count": businesses.count(),
            "business_names": list(businesses.values_list("name", flat=True)[:8]),
            "product_count": products.count(),
            "product_names": list(products.values_list("title", flat=True)[:8]),
            "top_business": top["business__name"] if top else "",
            "top_business_whatsapp_clicks": top["views"] if top else 0,
            "open_njangi": list(active_groups.values_list("product__title", "quantite_actuelle", "quantite_cible")[:8]),
        },
        "rules": {"no_claims_outside_payload": True},
    }, fallback_url=url, max_chars=600)
