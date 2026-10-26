"""
Service de partage automatique des prestataires PREMIUM E-Shelle vers la Page Facebook Officielle.
Page Facebook E-Shelle ID: 1316700031522892
"""

import logging
import threading
from datetime import timedelta
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger("facebook_agent")

META_GRAPH_VERSION = "v25.0"
DEFAULT_PAGE_ID = "1316700031522892"


def get_facebook_page_credentials():
    """
    Récupère le PAGE_ID et PAGE_ACCESS_TOKEN depuis settings ou depuis
    le modèle FacebookPageConfig en base.
    """
    page_id = getattr(settings, "FACEBOOK_PAGE_ID", DEFAULT_PAGE_ID) or DEFAULT_PAGE_ID
    page_token = getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", "")

    # Fallback vers FacebookPageConfig si token non renseigné en settings
    if not page_token:
        try:
            from facebook_agent.models import FacebookPageConfig
            config = FacebookPageConfig.objects.filter(is_active=True).first()
            if config:
                page_token = config.page_access_token
                if not page_id or page_id == DEFAULT_PAGE_ID:
                    page_id = config.page_id or page_id
        except Exception as exc:
            logger.debug(f"[FacebookAutoShare] Impossible de lire FacebookPageConfig: {exc}")

    return page_id, page_token


def get_daily_shared_count() -> int:
    """Nombre de partages Facebook réussis aujourd'hui."""
    try:
        from business.models import FacebookShareLog
        today = timezone.localdate()
        return FacebookShareLog.objects.filter(status="success", shared_at__date=today).count()
    except Exception as exc:
        logger.warning(f"[FacebookAutoShare] Erreur comptage partages journaliers: {exc}")
        return 0


def build_aeo_message(business) -> str:
    """
    Construit un message optimisé AEO (Answer Engine Optimization) & GEO
    avec hashtags locaux et lien canonique.
    """
    nom = getattr(business, "nom", None) or getattr(business, "name", "Prestataire Partenaire")
    quartier = (getattr(business, "district", "") or "").strip()
    ville = (getattr(business, "city", "") or "Douala / Yaoundé").strip()
    localisation = f"{quartier}, {ville}" if quartier and ville else (quartier or ville or "Cameroun")
    
    categorie = (
        business.get_module_display()
        if hasattr(business, "get_module_display")
        else getattr(business, "module", "Service")
    )

    # Récupération de la description courte
    desc = (
        getattr(business, "promo_offer", "")
        or getattr(business, "promo_headline", "")
        or getattr(business, "description", "")
        or ""
    ).strip()
    if len(desc) > 130:
        desc = desc[:127] + "..."

    # Détermination du prix indicatif
    prix = "Sur devis / Disponible"
    try:
        first_item = business.catalog_items.filter(is_active=True).first()
        if first_item and first_item.display_price_label:
            prix = first_item.display_price_label
        elif business.promo_offer:
            prix = business.promo_offer
    except Exception:
        pass

    # WhatsApp
    whatsapp = getattr(business, "clean_whatsapp_number", "") or getattr(business, "whatsapp", "") or getattr(business, "phone", "")
    if whatsapp and not whatsapp.startswith("+") and not whatsapp.startswith("237"):
        whatsapp = f"+237 {whatsapp}"

    # Slug canonique
    slug = getattr(business, "public_slug", "") or getattr(business, "slug", "") or str(business.pk)
    canonical_url = f"https://e-shelle.com/business/{slug}/"

    # Construction des hashtags
    tags = ["#EShelle", "#Cameroun", "#Premium"]
    if ville:
        tags.append(f"#{slugify(ville).replace('-', '_').title()}")
    if quartier:
        tags.append(f"#{slugify(quartier).replace('-', '_').title()}")
    if categorie:
        tags.append(f"#{slugify(categorie).replace('-', '_').title()}")
    hashtags_str = " ".join(dict.fromkeys(tags))  # Dédoublonnage

    message = (
        f"🔥 NOUVEAU PREMIUM à {localisation}!\n"
        f"⭐ {nom} - {categorie}\n\n"
        f"📝 {desc}\n"
        f"💰 Prix: {prix}\n"
        f"📍 Quartier: {quartier or localisation}\n"
        f"📱 WhatsApp: {whatsapp}\n"
        f"⭐ Prestataire Premium Vérifié E-Shelle\n\n"
        f"👉 Consultez la vitrine officielle : {canonical_url}\n\n"
        f"{hashtags_str}"
    )
    return message


def should_share(business) -> bool:
    """
    Vérifie si un business doit être partagé sur la Page Facebook:
    - is_premium = True (plan == PREMIUM)
    - is_published = True (is_active et activation_status == ACTIVE)
    - facebook_shared_at est None ou date de plus de 24h
    - limite journalière de max 3 posts non atteinte
    """
    if not getattr(settings, "FACEBOOK_AUTO_SHARE_ENABLED", True):
        logger.debug("[FacebookAutoShare] Partage auto désactivé dans settings.")
        return False

    is_premium = getattr(business, "is_premium", None)
    if is_premium is None:
        is_premium = getattr(business, "plan", "") == "premium"
    if not is_premium:
        return False

    is_published = getattr(business, "is_published", None)
    if is_published is None:
        is_published = bool(getattr(business, "is_active", False))
    if not is_published:
        return False

    # Éviter de re-poster le même business dans les 24h
    if business.facebook_shared_at:
        delta = timezone.now() - business.facebook_shared_at
        if delta < timedelta(hours=24):
            logger.info(f"[FacebookAutoShare] Business {business.pk} déjà partagé il y a {delta.total_seconds()/3600:.1f}h.")
            return False

    # Vérification de la limite journalière (3 posts/jour)
    max_daily = getattr(settings, "FACEBOOK_MAX_POSTS_PER_DAY", 3)
    current_count = get_daily_shared_count()
    if current_count >= max_daily:
        logger.info(f"[FacebookAutoShare] Limite quotidienne atteinte: {current_count}/{max_daily} posts.")
        return False

    return True


def share_premium_to_facebook_page(business, dry_run: bool = False) -> Optional[str]:
    """
    Partage le business Premium vers la Page Facebook E-Shelle.
    Retourne le post_id Meta ou None en cas d'échec / erreur. Ne crashe jamais.
    """
    page_id, page_token = get_facebook_page_credentials()
    message = build_aeo_message(business)
    slug = getattr(business, "public_slug", "") or getattr(business, "slug", "") or str(business.pk)
    link = f"https://e-shelle.com/business/{slug}/"

    if dry_run:
        logger.info(f"[FacebookAutoShare][DRY-RUN] Simuler partage pour business {business.pk} sur page {page_id}")
        return f"dry_run_post_{page_id}_{business.pk}"

    if not page_token:
        logger.warning("[FacebookAutoShare] Aucun Page Access Token Facebook configuré.")
        return None

    # Détection d'une photo publique si disponible
    image_url = ""
    try:
        if getattr(business, "promo_image", None):
            url = business.promo_image.url
            if url.startswith("http://") or url.startswith("https://"):
                image_url = url
            elif getattr(settings, "SITE_URL", ""):
                image_url = f"{settings.SITE_URL.rstrip('/')}{url}"
    except Exception:
        pass

    endpoint = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{page_id}/feed"
    payload = {
        "message": message,
        "link": link,
        "access_token": page_token,
    }

    # Si image disponible et accessible publiquement, poster sur /photos pour un meilleur engagement
    if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
        photo_endpoint = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{page_id}/photos"
        photo_payload = {
            "url": image_url,
            "caption": message,
            "access_token": page_token,
        }
        try:
            logger.info(f"[FacebookAutoShare] Publication photo sur page Facebook {page_id}")
            response = requests.post(photo_endpoint, data=photo_payload, timeout=25)
            data = response.json()
            if response.status_code == 200 and "id" in data:
                post_id = data.get("post_id") or data.get("id")
                logger.info(f"[FacebookAutoShare] Succès publication photo: {post_id}")
                return str(post_id)
            else:
                logger.warning(f"[FacebookAutoShare] Échec publication photo Meta: {data}. Repli sur feed.")
        except Exception as photo_err:
            logger.warning(f"[FacebookAutoShare] Erreur requête photo: {photo_err}. Repli sur feed.")

    # Publication lien & texte standard
    try:
        logger.info(f"[FacebookAutoShare] Publication lien/feed sur page Facebook {page_id}")
        response = requests.post(endpoint, data=payload, timeout=25)
        data = response.json()
        if response.status_code == 200 and "id" in data:
            post_id = str(data["id"])
            logger.info(f"[FacebookAutoShare] Succès publication feed: {post_id}")
            return post_id
        else:
            logger.error(f"[FacebookAutoShare] Erreur retournée par Meta: {data}")
            return None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"[FacebookAutoShare] Erreur connexion Meta Graph API: {req_err}")
        return None
    except Exception as exc:
        logger.exception(f"[FacebookAutoShare] Erreur inattendue partage: {exc}")
        return None


def execute_premium_share(business_pk: int) -> Optional[str]:
    """
    Exécute le partage synchrone pour une instance donnée, enregistre le log
    et met à jour les champs facebook_shared_at et last_facebook_post_id.
    """
    from business.models import BusinessProfile, FacebookShareLog

    business = BusinessProfile.objects.filter(pk=business_pk).first()
    if not business:
        logger.warning(f"[FacebookAutoShare] Business #{business_pk} introuvable.")
        return None

    if not should_share(business):
        logger.debug(f"[FacebookAutoShare] Business #{business_pk} non éligible au partage.")
        return None

    try:
        post_id = share_premium_to_facebook_page(business)
        if post_id:
            now = timezone.now()
            BusinessProfile.objects.filter(pk=business.pk).update(
                facebook_shared_at=now,
                last_facebook_post_id=post_id,
            )
            FacebookShareLog.objects.create(
                business=business,
                post_id=post_id,
                status="success",
                message=f"Publication réussie sur la page Facebook E-Shelle ({post_id})",
            )
            logger.info(f"[FacebookAutoShare] Partage validé pour business #{business.pk} (post: {post_id})")
            return post_id
        else:
            FacebookShareLog.objects.create(
                business=business,
                post_id="",
                status="failed",
                message="Échec de publication Meta (voir logs pour détails)",
            )
            return None
    except Exception as exc:
        logger.exception(f"[FacebookAutoShare] Exception lors de l'exécution du partage #{business_pk}: {exc}")
        try:
            FacebookShareLog.objects.create(
                business=business,
                post_id="",
                status="failed",
                message=f"Exception: {exc}",
            )
        except Exception:
            pass
        return None


def trigger_async_share_premium(business_pk: int):
    """
    Déclenche le partage en arrière-plan sans bloquer la requête HTTP de l'utilisateur.
    """
    # Démarrage d'un thread démon
    thread = threading.Thread(
        target=execute_premium_share,
        args=(business_pk,),
        daemon=True,
        name=f"fb_auto_share_{business_pk}",
    )
    thread.start()
