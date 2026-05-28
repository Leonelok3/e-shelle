"""
AdGen — Orchestrateur de modules
Fait le lien entre la campagne, l'IA, et la sauvegarde en base
"""
import logging
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
                "prix": self.campaign.prix,
                "cible": self.campaign.cible,
                "pays": self.campaign.pays,
                "pays_label": self.campaign.pays_label,
                "ville": self.campaign.ville,
                "ville_label": self.campaign.ville_label,
            }

            modules = self.campaign.modules_selected or []
            service = AdGenAIService()
            result = service.generate(product_data, modules)

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
