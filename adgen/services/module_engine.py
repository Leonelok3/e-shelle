"""
AdGen — Orchestrateur de modules
Fait le lien entre la campagne, l'IA, et la sauvegarde en base
"""
import logging
import re
from django.utils import timezone

logger = logging.getLogger(__name__)


class ModuleEngine:
    """Orchestre la génération complète d'une campagne."""

    def __init__(self, campaign):
        self.campaign = campaign

    def run(self):
        """
        Lance la génération AI, mappe le résultat sur AdContent,
        met à jour les stats utilisateur.
        Retourne l'objet AdContent créé.
        """
        from adgen.models import AdContent, AdUsageStat
        from adgen.services.ai_service import AdGenAIService

        # Passer le statut à "processing"
        self.campaign.status = "processing"
        self.campaign.save(update_fields=["status", "updated_at"])

        try:
            product_data = {
                "nom_produit": self.campaign.nom_produit,
                "description": self.campaign.description,
                "photo_url": self.campaign.photo_url,
                "prix": self.campaign.prix,
                "cible": self.campaign.cible,
                "pays": self.campaign.pays,
                "pays_label": self.campaign.pays_label,
                "ville": self.campaign.ville,
                "ville_label": self.campaign.ville_label,
            }

            modules = self.campaign.modules_selected or []
            try:
                service = AdGenAIService()
                result = service.generate(product_data, modules)
            except Exception as exc:
                logger.warning("[ModuleEngine] Fallback local campagne #%s: %s", self.campaign.pk, exc)
                result = self._fallback_generate(product_data, modules, str(exc))

            tokens = result.pop("_tokens_used", 0)
            raw    = result.pop("_raw", "")

            # Créer ou mettre à jour AdContent
            content, _ = AdContent.objects.update_or_create(
                campaign=self.campaign,
                defaults={
                    "titles":                result.get("titles", []),
                    "description_generated": result.get("description", ""),
                    "benefits":              result.get("benefits", []),
                    "facebook_post":         result.get("facebook", ""),
                    "instagram_post":        result.get("instagram", ""),
                    "whatsapp_message":      result.get("whatsapp", ""),
                    "hashtags":              result.get("hashtags", []),
                    "tiktok_script":         result.get("video_script", ""),
                    "chatbot_reply":         result.get("chatbot_reply", ""),
                    "raw_json":              result,
                    "tokens_used":           tokens,
                    "generated_at":          timezone.now(),
                }
            )

            # Mettre à jour les stats utilisateur
            stat, _ = AdUsageStat.objects.get_or_create(user=self.campaign.user)
            stat.campaigns_count += 1
            stat.tokens_total    += tokens
            stat.last_generation  = timezone.now()
            stat.save()

            # Campagne terminée
            self.campaign.status = "done"
            self.campaign.save(update_fields=["status", "updated_at"])

            logger.info(f"[ModuleEngine] Campagne #{self.campaign.pk} générée avec succès. Tokens: {tokens}")
            return content

        except Exception as e:
            logger.error(f"[ModuleEngine] Échec campagne #{self.campaign.pk}: {e}")
            self.campaign.status = "failed"
            self.campaign.save(update_fields=["status", "updated_at"])
            raise

    def _fallback_generate(self, product_data: dict, modules: list, error: str) -> dict:
        """Generation locale de secours pour tester AdGen sans credit API."""
        name = product_data.get("nom_produit", "Produit")
        desc = product_data.get("description", "")
        price = product_data.get("prix", "Prix a confirmer")
        target = product_data.get("cible", "clients locaux")
        city = product_data.get("ville_label") or "votre ville"
        country = product_data.get("pays_label") or "Cameroun"
        clean_desc = re.sub(r"\s+", " ", desc).strip()
        short_desc = clean_desc[:170] + ("..." if len(clean_desc) > 170 else "")
        modules = modules or ["titres", "description", "social"]
        offer_angle = self._fallback_offer_angle(name, clean_desc)
        customer_gain = self._fallback_customer_gain(name, clean_desc, target)
        price_label = self._fallback_price(price)

        result = {
            "_tokens_used": 0,
            "_raw": f"Fallback local AdGen. API indisponible: {error[:240]}",
            "generation_mode": "fallback_local",
        }

        if "titres" in modules:
            result["titles"] = [
                f"{name}: le bon choix a {city}",
                f"{name} disponible maintenant a {price_label}",
                f"Commandez {name} sans perdre le temps",
            ]

        if "description" in modules:
            result["description"] = (
                f"{name} est une offre ideale pour {target} a {city}, {country}. "
                f"{offer_angle} {customer_gain} "
                f"Disponible a {price_label}, avec une prise de contact simple et rapide sur WhatsApp. "
                "Demandez les details, confirmez la disponibilite et passez commande en quelques messages."
            )
            result["benefits"] = [
                "Offre claire pour attirer rapidement l'attention",
                "Prix visible pour faciliter la decision",
                "Message adapte aux clients locaux",
                "Contact direct pour commander ou reserver",
                "Contenu pret a publier sur WhatsApp et reseaux sociaux",
            ]

        if "social" in modules:
            result["facebook"] = (
                f"Envie de {name} a {city} ?\n\n"
                f"{offer_angle}\n\n"
                f"Prix: {price_label}. Ecrivez maintenant pour commander, reserver ou poser vos questions. "
                "Reponse rapide sur WhatsApp."
            )
            result["instagram"] = (
                f"{name}\n{offer_angle}\nPrix: {price_label}\nDisponible a {city}.\n"
                "Commande rapide par message.\n"
                "#EShelle #Cameroun #BusinessLocal #Promo #WhatsAppBusiness"
            )
            result["whatsapp"] = (
                f"Bonjour, {name} est disponible a {price_label}. "
                "Dites-moi votre quartier et la quantite souhaitee pour confirmer les details."
            )
            result["hashtags"] = ["#EShelle", "#Cameroun", "#Douala", "#BusinessLocal", "#Promo", "#WhatsAppBusiness"]

        if "tiktok" in modules:
            result["video_script"] = (
                f"0-3s: Gros plan sur {name}. Texte: \"Vous cherchez ca a {city} ?\"\n"
                f"4-12s: Montrez le produit, la texture/la qualite, puis affichez le prix {price_label}.\n"
                "13-17s: Montrez comment commander par WhatsApp.\n"
                "18-20s: CTA: \"Envoyez un message maintenant\"."
            )

        if "chatbot" in modules:
            result["chatbot_reply"] = (
                f"Oui, {name} est disponible a {price_label}. {customer_gain} "
                "Envoyez votre quartier et la quantite souhaitee, je vous aide a confirmer rapidement."
            )

        return result

    def _fallback_offer_angle(self, name: str, desc: str) -> str:
        text = f"{name} {desc}".lower()
        if any(word in text for word in ["taro", "eru", "ndole", "okok", "koki", "plat", "restaurant", "poulet"]):
            return "Un plat genereux, local et appétissant, parfait pour se faire plaisir sans compliquer la journee."
        if any(word in text for word in ["chaussure", "vetement", "robe", "mode", "sac"]):
            return "Un article qui combine style, praticite et presence, facile a porter au quotidien."
        if any(word in text for word in ["formation", "cours", "apprendre"]):
            return "Une solution pour progresser avec une offre claire, pratique et orientee resultat."
        if any(word in text for word in ["service", "devis", "travaux", "reparation"]):
            return "Un service utile pour regler un besoin concret avec un contact direct et fiable."
        return desc[:160] + ("..." if len(desc) > 160 else "") if desc else "Une offre claire, pratique et facile a commander."

    def _fallback_customer_gain(self, name: str, desc: str, target: str) -> str:
        text = f"{name} {desc}".lower()
        if any(word in text for word in ["taro", "eru", "ndole", "okok", "koki", "plat", "restaurant", "poulet"]):
            return "Le client gagne du temps, mange bien et peut commander sans longue discussion."
        if any(word in text for word in ["chaussure", "vetement", "robe", "mode", "sac"]):
            return "Le client obtient un look propre, moderne et adapte a son budget."
        return f"Le message parle directement a {target} et met en avant le benefice principal."

    def _fallback_price(self, price: str) -> str:
        value = (price or "").strip()
        if not value:
            return "prix a confirmer"
        if any(currency in value.lower() for currency in ["fcfa", "xaf", "$", "€"]):
            return value
        if re.fullmatch(r"[\d\s.,]+", value):
            return f"{value} FCFA"
        return value
