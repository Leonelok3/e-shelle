import re
import time

import anthropic
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q


class WhatsAppService:
    """Services metier pour l'agent WhatsApp E-Shelle."""

    @staticmethod
    def envoyer_message(numero: str, message: str) -> dict:
        """Envoie un message texte via l'API Meta WhatsApp Business."""

        if getattr(settings, "WHATSAPP_DRY_RUN", True):
            return {
                "success": True,
                "message_id": f"dryrun-{int(time.time() * 1000)}",
                "erreur": "Simulation: aucun appel Meta effectue.",
            }

        if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
            return {
                "success": False,
                "message_id": "",
                "erreur": "Configuration Meta incomplete: WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID manquant.",
            }

        payload = {
            "messaging_product": "whatsapp",
            "to": WhatsAppService.normaliser_numero(numero),
            "type": "text",
            "text": {"body": message, "preview_url": False},
        }
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(settings.WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
            data = response.json()
            if response.status_code == 200 and data.get("messages"):
                return {"success": True, "message_id": data["messages"][0]["id"], "erreur": ""}
            return {"success": False, "message_id": "", "erreur": str(data)}
        except Exception as exc:
            return {"success": False, "message_id": "", "erreur": str(exc)}

    @staticmethod
    def generer_message_ia(segment: str, contexte: str, prenom: str = "") -> str:
        """Genere un message court avec Claude pour une campagne marketing."""

        client = anthropic.Anthropic(api_key=getattr(settings, "ANTHROPIC_API_KEY", ""))
        salutation = f"Commence par 'Bonjour {prenom},' si c'est naturel." if prenom else ""
        prompt = f"""Tu es l'assistant marketing d'E-Shelle, marketplace africaine au Cameroun.
Genere un message WhatsApp court (max 160 caracteres), chaleureux et en francais.
Segment: {segment or "utilisateurs E-Shelle"}.
Contexte de la campagne: {contexte}.
{salutation}
Le message doit inciter a l'action. Pas d'emoji excessif. Termine par un lien si pertinent.
Reponds UNIQUEMENT avec le texte du message, rien d'autre."""

        msg = client.messages.create(
            model=getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    @staticmethod
    def recuperer_contacts(filtre_role="", filtre_ville="", date_depuis=None):
        """Recupere les utilisateurs ayant un numero WhatsApp exploitable."""

        User = get_user_model()
        qs = User.objects.filter(whatsapp__isnull=False).exclude(whatsapp="").order_by("-date_joined")

        if filtre_role and filtre_role != "tous":
            qs = qs.filter(role__iexact=filtre_role)

        if filtre_ville:
            # La ville existe sur CustomUser et parfois sur le profil etendu.
            qs = qs.filter(Q(ville__icontains=filtre_ville) | Q(profile__ville__icontains=filtre_ville))

        if date_depuis:
            qs = qs.filter(date_joined__date__gte=date_depuis)

        return qs.distinct()

    @staticmethod
    def personnaliser_message(template: str, user) -> str:
        """Remplace les variables simples dans le message de campagne."""

        prenom = (getattr(user, "first_name", "") or getattr(user, "username", "") or "").strip()
        ville = (getattr(user, "ville", "") or getattr(getattr(user, "profile", None), "ville", "") or "").strip()
        return (
            template.replace("{{prenom}}", prenom)
            .replace("{{nom}}", (getattr(user, "last_name", "") or "").strip())
            .replace("{{ville}}", ville)
        )

    @staticmethod
    def normaliser_numero(numero: str) -> str:
        """Convertit un numero vers le format attendu par Meta, sans espaces."""

        cleaned = re.sub(r"[\s().-]+", "", numero or "")
        return cleaned


AI_PRESETS = {
    "promo_resto": {
        "label": "Promo resto",
        "segment": "clients restaurants",
        "contexte": "Promotion d'un restaurant partenaire E-Shelle avec commande rapide via WhatsApp.",
    },
    "relance_client": {
        "label": "Relance client",
        "segment": "clients inactifs",
        "contexte": "Relancer un utilisateur qui n'a pas utilise E-Shelle recemment.",
    },
    "nouveau_service": {
        "label": "Nouveau service",
        "segment": "utilisateurs E-Shelle",
        "contexte": "Annonce d'un nouveau service disponible sur E-Shelle.",
    },
    "premium": {
        "label": "Message premium",
        "segment": "clients premium",
        "contexte": "Valoriser une offre premium avec benefice clair et appel a l'action.",
    },
    "vendeurs": {
        "label": "Campagne vendeurs",
        "segment": "vendeurs et partenaires",
        "contexte": "Encourager les vendeurs a publier leurs offres et suivre leurs prospects.",
    },
}
