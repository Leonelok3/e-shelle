"""
facebook_publisher.py — immobilier_cameroun/services
Publication automatique de biens immobiliers sur la Page Facebook officielle E-Shelle.
Utilise get_facebook_page_credentials() de manière autonome SANS modifier core/services/facebook_auto_share.py.
"""
import os
import logging
import requests
from typing import Optional
from django.conf import settings
from django.utils.text import slugify

logger = logging.getLogger("facebook_immo")

META_GRAPH_VERSION = "v25.0"


def publier_bien_sur_facebook(bien, draft=None) -> Optional[str]:
    """
    Publie un bien immobilier validé sur la page Facebook E-Shelle.
    Retourne l'ID du post Facebook créé ou None en cas d'erreur / absence de token.
    Ne lève jamais d'exception fatale.
    """
    try:
        from core.services.facebook_auto_share import get_facebook_page_credentials
        page_id, page_token = get_facebook_page_credentials()
    except Exception as e:
        logger.warning(f"[Facebook Immo] Impossible de charger les credentials Facebook : {e}")
        return None

    if not page_token or not page_id:
        logger.warning("[Facebook Immo] Token ou Page ID Facebook manquant. Publication ignorée.")
        return None

    # Extraction des données
    titre = bien.titre
    ville = bien.ville or "Cameroun"
    quartier = bien.quartier or ""
    prix_str = bien.prix_formate

    conditions = draft.parsed_conditions if draft else ""
    cond_txt = f" ({conditions})" if conditions else ""

    phone = ""
    if draft and draft.source_phone:
        phone = draft.source_phone
    elif hasattr(bien.proprietaire, "profil_immo"):
        phone = bien.proprietaire.profil_immo.whatsapp or bien.proprietaire.profil_immo.telephone
    if not phone:
        phone = getattr(settings, "IMMO_WHATSAPP_CONTACT", "+237 600 000 000")

    url_absolue = bien._url_absolue()

    # Description courte
    raw_desc = (draft.ai_improved_description if draft and draft.ai_improved_description else bien.description) or ""
    # Enlever mise en forme trop lourde pour Facebook
    clean_desc = raw_desc.replace("**", "").replace("##", "")
    lines = [l.strip() for l in clean_desc.splitlines() if l.strip()]
    desc_summary = " ".join(lines[:4])
    if len(desc_summary) > 280:
        desc_summary = desc_summary[:277] + "..."

    # Hashtags locaux
    v_tag = f"#{slugify(ville).replace('-', '_').title()}" if ville else "#Cameroun"
    q_tag = f"#{slugify(quartier).replace('-', '_').title()}" if quartier else ""
    hashtags = f"#EShelle #ImmobilierCameroun {v_tag} {q_tag} #LocationCameroun #Yaounde #Douala"

    message = (
        f"🏠 NOUVEAU SUR E-SHELLE IMMOBILIER !\n"
        f"✨ {titre}\n\n"
        f"📍 Quartier : {quartier}, {ville}\n"
        f"💰 Loyer / Prix : {prix_str}{cond_txt}\n\n"
        f"📝 Aperçu :\n{desc_summary}\n\n"
        f"📱 Contact direct WhatsApp démarcheur : {phone}\n"
        f"👉 Voir toutes les photos & détails certifiés : {url_absolue}\n\n"
        f"{hashtags}"
    )

    # 1. Tentative de publication avec photo locale en multipart si disponible
    photo = bien.photo_principale
    if photo and photo.image:
        try:
            image_path = photo.image.path
            if os.path.exists(image_path):
                photo_endpoint = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{page_id}/photos"
                logger.info(f"[Facebook Immo] Envoi photo locale vers Facebook Page {page_id}...")
                with open(image_path, "rb") as img_file:
                    resp = requests.post(
                        photo_endpoint,
                        data={
                            "caption": message,
                            "access_token": page_token,
                        },
                        files={"source": img_file},
                        timeout=30,
                    )
                data = resp.json()
                if resp.status_code == 200 and "id" in data:
                    post_id = str(data.get("post_id") or data.get("id"))
                    logger.info(f"[Facebook Immo] Succès publication photo: {post_id}")
                    return post_id
                else:
                    logger.warning(f"[Facebook Immo] Échec publication photo (code {resp.status_code}): {data}")
        except Exception as err:
            logger.warning(f"[Facebook Immo] Erreur lors de l'upload photo Facebook : {err}")

    # 2. Fallback publication feed texte + lien
    try:
        feed_endpoint = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{page_id}/feed"
        logger.info(f"[Facebook Immo] Envoi message feed vers Facebook Page {page_id}...")
        resp = requests.post(
            feed_endpoint,
            data={
                "message": message,
                "link": url_absolue,
                "access_token": page_token,
            },
            timeout=25,
        )
        data = resp.json()
        if resp.status_code == 200 and "id" in data:
            post_id = str(data.get("id"))
            logger.info(f"[Facebook Immo] Succès publication feed: {post_id}")
            return post_id
        else:
            logger.warning(f"[Facebook Immo] Échec feed Facebook (code {resp.status_code}): {data}")
    except Exception as err:
        logger.error(f"[Facebook Immo] Erreur communication Facebook Feed : {err}")

    return None
