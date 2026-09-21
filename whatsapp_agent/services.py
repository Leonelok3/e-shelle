import json
import random
import re
import time

from ai_engine.services.llm_service import call_llm
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone


class WhatsAppSpintaxService:
    """Moteur de resolution de Spintax simple ou imbrique pour des messages WhatsApp uniques."""

    @staticmethod
    def resoudre_spintax(texte: str) -> str:
        """
        Remplace les blocs {choix1|choix2|choix3} par un choix aleatoire.
        Supporte les Spintax imbriques: {Bonjour|{Salut|Hello}}
        """
        if not texte:
            return ""
        pattern = re.compile(r"\{([^{}]+)\}")
        while True:
            match = pattern.search(texte)
            if not match:
                break
            options = [opt.strip() for opt in match.group(1).split("|") if opt.strip()]
            choice = random.choice(options) if options else ""
            texte = texte[:match.start()] + choice + texte[match.end():]
        return texte


class WhatsAppGreetingService:
    """Generateur de salutations intelligentes et humaines.
    Evite a 100% le robotique 'Bonjour Contact' quand le nom est inconnu."""

    @staticmethod
    def salutation_naturelle(contact=None, user=None) -> str:
        heure = timezone.now().hour
        salut_base = "Bonsoir" if (heure >= 17 or heure < 5) else "Bonjour"

        prenom = ""
        if contact:
            nom_brut = (contact.nom or "").strip()
            if nom_brut and not nom_brut.lower().startswith("contact whatsapp") and not nom_brut.startswith("+"):
                prenom = nom_brut.split()[0]
        elif user:
            prenom = (getattr(user, "first_name", "") or "").strip()

        if prenom:
            return f"{salut_base} {prenom},"

        groupe = (getattr(contact, "groupe", "") or "").strip() if contact else ""
        if groupe:
            return f"{salut_base} cher membre du groupe {groupe},"

        return f"{salut_base},"


class WhatsAppService:
    """Services metier pour l'agent WhatsApp E-Shelle."""

    @staticmethod
    def envoyer_message(numero: str, message: str, template_name: str = "", template_params: list = None, template_language: str = "") -> dict:
        """
        Envoie un message via l'API Meta WhatsApp Business.
        Si un template_name est spécifié ou si le message commence par 'template:',
        envoie via un modèle approuvé par Meta (obligatoire pour initier un contact hors fenêtre 24h).
        """

        if template_name or (message and message.strip().startswith("template:")):
            tpl = template_name or message.strip().replace("template:", "").strip()
            return WhatsAppService.envoyer_template(numero, tpl, language_code=template_language or None, body_params=template_params)

        # Si un template par défaut est configuré dans Django et qu'on fait de l'outreach froid
        default_tpl = getattr(settings, "WHATSAPP_DEFAULT_TEMPLATE", "")
        if default_tpl and getattr(settings, "WHATSAPP_FORCE_TEMPLATE", False):
            return WhatsAppService.envoyer_template(numero, default_tpl, body_params=template_params)

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
            "to": WhatsAppService.normaliser_numero_meta(numero),
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

            # Si Meta indique qu'un template est obligatoire (erreur 131047 ou message hors fenêtre 24h)
            err_code = data.get("error", {}).get("code")
            if not err_code and isinstance(data.get("errors"), list) and data["errors"]:
                err_code = data["errors"][0].get("code")

            if (err_code == 131047 or "24 hours" in str(data) or "Re-engagement" in str(data)) and default_tpl:
                fallback_params = template_params or ["Client"]
                return WhatsAppService.envoyer_template(numero, default_tpl, body_params=fallback_params)

            return {"success": False, "message_id": "", "erreur": str(data)}
        except Exception as exc:
            return {"success": False, "message_id": "", "erreur": str(exc)}

    @staticmethod
    def envoyer_template(numero: str, template_name: str, language_code: str = None, body_params: list = None) -> dict:
        """
        Envoie un modèle de message validé par Meta (Template).
        Obligatoire pour contacter un prospect qui n'a pas écrit au numéro dans les dernières 24h.
        """

        if getattr(settings, "WHATSAPP_DRY_RUN", True):
            return {
                "success": True,
                "message_id": f"dryrun-tpl-{int(time.time() * 1000)}",
                "erreur": "Simulation: aucun appel Meta effectue (Template).",
            }

        if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
            return {
                "success": False,
                "message_id": "",
                "erreur": "Configuration Meta incomplete: WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID manquant.",
            }

        if language_code is None:
            language_code = "en_US" if template_name.strip() == "hello_world" else getattr(settings, "WHATSAPP_TEMPLATE_LANGUAGE", "fr")
        # Meta's sample has no body placeholders, including during campaign sends.
        if template_name.strip() == "hello_world":
            body_params = []
        template_payload = {
            "name": template_name.strip(),
            "language": {"code": language_code},
        }

        if body_params:
            template_payload["components"] = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in body_params],
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": WhatsAppService.normaliser_numero_meta(numero),
            "type": "template",
            "template": template_payload,
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
        """Genere un message court avec les fournisseurs IA configurés pour une campagne marketing."""

        salutation = f"Commence par 'Bonjour {prenom},' si c'est naturel." if prenom else ""
        prompt = f"""Tu es l'assistant marketing d'E-Shelle, marketplace africaine au Cameroun.
Genere un message WhatsApp court (max 160 caracteres), chaleureux et en francais.
Segment: {segment or "utilisateurs E-Shelle"}.
Contexte de la campagne: {contexte}.
{salutation}
Le message doit inciter a l'action. Pas d'emoji excessif. Termine par un lien si pertinent.
Reponds UNIQUEMENT avec le texte du message, rien d'autre."""

        return call_llm("Tu es un assistant marketing. Respecte le format demandé.", prompt, max_tokens=300)

    @staticmethod
    def recuperer_contacts(filtre_role="", filtre_ville="", date_depuis=None):
        """Recupere les utilisateurs ayant un numero WhatsApp exploitable."""

        User = get_user_model()
        qs = User.objects.filter(
            whatsapp__isnull=False,
            whatsapp_marketing_opt_in=True,
            whatsapp_marketing_opted_out=False,
        ).exclude(whatsapp="").order_by("-date_joined")

        if filtre_role and filtre_role != "tous":
            qs = qs.filter(role__iexact=filtre_role)

        if filtre_ville:
            # La ville existe sur CustomUser et parfois sur le profil etendu.
            qs = qs.filter(Q(ville__icontains=filtre_ville) | Q(profile__ville__icontains=filtre_ville))

        if date_depuis:
            qs = qs.filter(date_joined__date__gte=date_depuis)

        return qs.distinct()

    @staticmethod
    def personnaliser_message(template: str, user=None, contact=None) -> str:
        """Remplace les variables et resout le Spintax avec fallback sans nom intelligent."""

        salutation = WhatsAppGreetingService.salutation_naturelle(contact=contact, user=user)
        prenom = ""
        nom = ""
        ville = ""
        groupe = ""
        numero = ""

        if contact:
            nom_brut = (contact.nom or "").strip()
            if nom_brut and not nom_brut.lower().startswith("contact whatsapp") and not nom_brut.startswith("+"):
                nom = nom_brut
                prenom = nom_brut.split()[0]
            ville = (contact.ville or "").strip()
            groupe = (contact.groupe or "").strip()
            numero = contact.numero or ""
        elif user:
            nom = (user.get_full_name() or "").strip()
            prenom = (getattr(user, "first_name", "") or getattr(user, "username", "") or "").strip()
            ville = (getattr(user, "ville", "") or getattr(getattr(user, "profile", None), "ville", "") or "").strip()
            numero = getattr(user, "whatsapp", "") or ""

        texte = template or ""
        texte = texte.replace("{{salutation}}", salutation)

        if "{{prenom}}" in texte:
            if prenom:
                texte = texte.replace("{{prenom}}", prenom)
            else:
                # Si aucun prenom n'est connu, remplace 'Bonjour {{prenom}},' proprement par la salutation naturelle
                texte = re.sub(r"(Bonjour|Salut|Hello|Bonsoir)\s*\{\{prenom\}\},?", salutation, texte, flags=re.IGNORECASE)
                texte = texte.replace("{{prenom}}", "")

        texte = texte.replace("{{nom}}", nom or prenom)
        texte = texte.replace("{{ville}}", ville)
        texte = texte.replace("{{groupe}}", groupe)
        texte = texte.replace("{{numero}}", numero)

        # Nettoyage des espaces doubles
        texte = re.sub(r"[ \t]{2,}", " ", texte)
        # Resolution Spintax aleatoire unique
        return WhatsAppSpintaxService.resoudre_spintax(texte).strip()

    @staticmethod
    def personnaliser_message_contact(template: str, contact) -> str:
        """Alias specialise pour les contacts importes."""
        return WhatsAppService.personnaliser_message(template, contact=contact)

    @staticmethod
    def generer_variations_multiples_ia(segment: str, contexte: str, nb_variations: int = 5) -> list:
        """Genere plusieurs variations distinctes d'un message publicitaire via les fournisseurs IA configurés pour l'anti-spam."""
        prompt = f"""Tu es un copywriter expert en WhatsApp Marketing pour le Cameroun et l'Afrique (plateforme E-Shelle).
Genere exactement {nb_variations} variations tres differentes d'un message WhatsApp de prospection.
Segment cible: {segment or 'commercants, prestataires et utilisateurs'}
Contexte de l'offre: {contexte or 'Promotion des services E-Shelle'}

REGLES:
1. Chaque variante doit avoir un angle different (ex: 1. Question directe, 2. Opportunite de chiffre d'affaires, 3. Temoignage/Storytelling, 4. Invitation exclusive, 5. Question simple).
2. Chaque message doit etre court (120 a 240 caracteres max), percutant, chaleureux.
3. Utilise les balises quand utile: {{{{salutation}}}}, {{{{prenom}}}}, {{{{ville}}}}, {{{{groupe}}}}.
4. Utilise du Spintax {{choix1|choix2}} dans les variantes pour creer des centaines de combinaisons uniques.
5. Reponds UNIQUEMENT avec un tableau JSON valide de chaines:
["Variante 1...", "Variante 2...", "Variante 3..."]"""

        try:
            raw = call_llm("Tu es un assistant marketing. Respecte le format demandé.", prompt, max_tokens=900)
            if "```" in raw:
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                if match:
                    raw = match.group(0)
            data = json.loads(raw)
            if isinstance(data, list) and data:
                return [str(v).strip() for v in data if str(v).strip()]
        except Exception:
            pass

        # Fallback intelligent
        return [
            "{{salutation}} {Avez-vous deja pense a|Saviez-vous qu'il est possible de} developper votre activite sur WhatsApp avec E-Shelle ? Decouvrez comment nos membres multiplient leurs commandes : https://e-shelle.com",
            "{{salutation}} {En tant qu'entrepreneur|Vu votre profil actif}, nous vous offrons un acces privilegie pour recevoir des demandes de clients qualifies dans votre ville. Voulez-vous une presentation rapide ?",
            "{{salutation}} {Besoin de plus de visibilite|Vous cherchez a booster vos ventes} a {{ville}} ? Rejoignez E-Shelle des aujourd'hui. Repondez simplement OUI pour recevoir notre guide gratuit.",
            "{{salutation}} {Petite question rapide :|Connaissez-vous deja} E-Shelle ? Nous aidons les prestataires et commercants a trouver des clients sans depenser en publicite inutile. Discutons-en 2 minutes !",
            "{{salutation}} {Une opportunite a ne pas manquer :|Bonne nouvelle :} E-Shelle ouvre de nouvelles opportunites pour les vendeurs. Repondez a ce message pour decouvrir comment en profiter gratuitement.",
        ]

    @staticmethod
    def normaliser_numero(numero: str) -> str:
        """Convertit un numero vers un format E-Shelle lisible: +237..."""

        cleaned = re.sub(r"[\s().-]+", "", numero or "").strip()
        if not cleaned:
            return ""
        digits = re.sub(r"\D", "", cleaned)
        if cleaned.startswith("+") and digits:
            return f"+{digits}"
        if digits.startswith("00"):
            return f"+{digits[2:]}"
        if digits.startswith("237"):
            return f"+{digits}"
        if len(digits) >= 8:
            return f"+237{digits}"
        return digits

    @staticmethod
    def normaliser_numero_meta(numero: str) -> str:
        """Convertit un numero vers le format Cloud API: code pays sans +."""

        normalized = WhatsAppService.normaliser_numero(numero)
        return re.sub(r"\D", "", normalized)

    @staticmethod
    def deja_contacte(numero: str) -> bool:
        """Retourne vrai si ce numero a deja recu un envoi WhatsApp reussi."""

        from .models import OutreachLog

        identifiant = WhatsAppService.normaliser_numero(numero)
        return OutreachLog.objects.filter(
            canal=OutreachLog.CANAL_WHATSAPP,
            identifiant=identifiant,
            statut__in=["envoye", "livre", "lu"],
        ).exists()

    @staticmethod
    def journaliser_envoi(numero: str, message_envoi, statut="envoye"):
        """Enregistre un envoi réussi sans exposer le contenu dans les logs."""

        from .models import OutreachLog

        OutreachLog.objects.get_or_create(
            canal=OutreachLog.CANAL_WHATSAPP,
            identifiant=WhatsAppService.normaliser_numero(numero),
            defaults={
                "campagne": message_envoi.campagne,
                "message_envoi": message_envoi,
                "statut": statut,
            },
        )

    @staticmethod
    def journaliser_email(email: str, sujet: str = "", campagne=None, statut="envoye"):
        """Point d’entrée commun pour les futurs envois email marketing."""

        from .models import OutreachLog

        identifiant = (email or "").strip().lower()
        if not identifiant:
            return None
        return OutreachLog.objects.create(
            canal=OutreachLog.CANAL_EMAIL,
            identifiant=identifiant,
            campagne=campagne,
            sujet=sujet[:255],
            statut=statut,
        )

    @staticmethod
    def enregistrer_message_entrant(
        numero: str,
        texte: str,
        whatsapp_msg_id: str = "",
        profile_name: str = "",
        media_type: str = "",
        media_url: str = "",
    ):
        """
        Enregistre un message recu d'un prospect.
        Met a jour automatiquement le nom du contact a partir de son profil WhatsApp s'il etait vide.
        Cree ou met a jour la ConversationWhatsApp correspondante avec un badge non-lu.
        """
        from .models import ContactWhatsApp, ConversationWhatsApp, MessageWhatsApp

        numero_propre = WhatsAppService.normaliser_numero(numero)
        if not numero_propre:
            return None

        # Recuperation ou creation du contact
        defaults = {
            "source": ContactWhatsApp.SOURCE_API,
            "consentement_confirme": True,
            "consentement_source": "incoming_whatsapp_message",
            "consentement_le": timezone.now(),
        }
        if profile_name:
            defaults["nom"] = profile_name.strip()

        contact, created = ContactWhatsApp.objects.get_or_create(
            numero=numero_propre,
            defaults=defaults,
        )

        # Si le contact existait deja sans nom et que Meta nous donne son profil WhatsApp: on l'enrichit !
        if profile_name and (not contact.nom or contact.nom.lower().startswith("contact whatsapp") or contact.nom.startswith("+")):
            contact.nom = profile_name.strip()
            contact.save(update_fields=["nom", "mis_a_jour_le"])

        # Recuperation ou creation du fil de conversation
        conversation, conv_created = ConversationWhatsApp.objects.get_or_create(
            contact=contact,
            defaults={
                "statut": ConversationWhatsApp.STATUT_NOUVEAU,
                "priorite": ConversationWhatsApp.PRIORITE_HAUTE if any(mot in (texte or "").lower() for mot in ["prix", "combien", "demo", "interess", "achete", "commander", "oui"]) else ConversationWhatsApp.PRIORITE_NORMALE,
                "dernier_message_apercu": (texte or f"[{media_type or 'Piece jointe'}]")[:200],
                "dernier_message_le": timezone.now(),
                "non_lus_count": 1,
            },
        )

        # Evite doublons
        if whatsapp_msg_id and MessageWhatsApp.objects.filter(whatsapp_msg_id=whatsapp_msg_id).exists():
            return MessageWhatsApp.objects.get(whatsapp_msg_id=whatsapp_msg_id)

        msg = MessageWhatsApp.objects.create(
            conversation=conversation,
            direction=MessageWhatsApp.DIRECTION_ENTRANT,
            texte=texte or "",
            whatsapp_msg_id=whatsapp_msg_id,
            statut=MessageWhatsApp.STATUT_RECU,
            media_type=media_type,
            media_url=media_url,
        )

        # Detection d'intention positive automatique
        texte_lower = (texte or "").lower()
        if any(mot in texte_lower for mot in ["oui", "interess", "prix", "combien", "demo", "commander", "info", "bonjour", "salut"]):
            if conversation.statut in [ConversationWhatsApp.STATUT_NOUVEAU, ConversationWhatsApp.STATUT_EN_COURS]:
                conversation.statut = ConversationWhatsApp.STATUT_INTERESSE
                conversation.priorite = ConversationWhatsApp.PRIORITE_HAUTE

        conversation.dernier_message_apercu = (texte or f"[{media_type or 'Piece jointe'}]")[:200]
        conversation.dernier_message_le = timezone.now()
        conversation.non_lus_count = (conversation.non_lus_count or 0) + 1
        conversation.save(update_fields=["statut", "priorite", "dernier_message_apercu", "dernier_message_le", "non_lus_count", "mis_a_jour_le"])

        return msg

    @staticmethod
    def envoyer_message_conversation(conversation_id: int, texte: str, auteur=None) -> dict:
        """Envoie une reponse directe a un prospect dans une conversation."""
        from .models import ConversationWhatsApp, MessageWhatsApp

        try:
            conversation = ConversationWhatsApp.objects.select_related("contact").get(id=conversation_id)
        except ConversationWhatsApp.DoesNotExist:
            return {"success": False, "erreur": "Conversation introuvable."}

        numero = conversation.contact.numero
        result = WhatsAppService.envoyer_message(numero, texte)

        msg = MessageWhatsApp.objects.create(
            conversation=conversation,
            direction=MessageWhatsApp.DIRECTION_SORTANT,
            texte=texte,
            whatsapp_msg_id=result.get("message_id", ""),
            statut=MessageWhatsApp.STATUT_ENVOYE if result.get("success") else MessageWhatsApp.STATUT_ECHEC,
            envoye_par=auteur if auteur and auteur.is_authenticated else None,
        )

        conversation.dernier_message_apercu = f"Vous: {texte[:180]}"
        conversation.dernier_message_le = timezone.now()
        if conversation.statut == ConversationWhatsApp.STATUT_NOUVEAU:
            conversation.statut = ConversationWhatsApp.STATUT_EN_COURS
        conversation.save(update_fields=["dernier_message_apercu", "dernier_message_le", "statut", "mis_a_jour_le"])

        return {
            "success": result.get("success", False),
            "erreur": result.get("erreur", ""),
            "message_id": msg.id,
            "cree_le": msg.cree_le.strftime("%d/%m/%Y %H:%M"),
        }

    @staticmethod
    def suggerer_reponse_ia(conversation_id: int) -> str:
        """Genere une reponse commerciale persuasive adaptee a la question du prospect."""
        from .models import ConversationWhatsApp

        try:
            conversation = ConversationWhatsApp.objects.select_related("contact", "commercial_prospect").get(id=conversation_id)
        except ConversationWhatsApp.DoesNotExist:
            return ""

        historique = conversation.messages.order_by("-cree_le")[:6]
        fil_text = []
        for m in reversed(historique):
            exp = "Prospect" if m.direction == "entrant" else "E-Shelle"
            fil_text.append(f"{exp}: {m.texte}")
        historique_str = "\n".join(fil_text)

        nom_prospect = conversation.contact.nom or "le client"
        ville = conversation.contact.ville or "Cameroun"
        groupe = conversation.contact.groupe or ""

        prompt = f"""Tu es l'agent commercial IA d'E-Shelle, la plateforme camerounaise de marketplace, salons, livraisons et services digitaux.
Fil recent avec {nom_prospect} ({ville}, source: {groupe or 'contact WhatsApp'}) :
---
{historique_str}
---
Propose une reponse WhatsApp ideale :
- Courte (2 a 4 phrases).
- Chaleureuse, professionnelle et vendeuse.
- Reponds precisement au besoin exprime.
- Termine par un appel a l'action simple (question ou proposition de rendez-vous / lien).
- Pas d'emojis excessifs. En francais.
Reponds UNIQUEMENT avec le texte du message."""

        try:
            return call_llm("Tu es un assistant marketing. Respecte le format demandé.", prompt, max_tokens=350)
        except Exception:
            return f"Bonjour {conversation.contact.nom or ''}, merci pour votre message ! Nous serions ravis de vous accompagner avec nos solutions E-Shelle. Quel est le meilleur moment pour un bref echange aujourd'hui ?"


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
