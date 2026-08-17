"""
AdGen — Timeline Planner Service
Gère la planification temporelle et textuelle des scènes de la publicité.
"""
import logging

logger = logging.getLogger(__name__)

class TimelinePlanner:
    """Calcule le timing précis de chaque scène et prépare les textes associés."""

    def __init__(self, campaign, duration: int = 30):
        self.campaign = campaign
        self.duration = duration if duration in [15, 30, 45, 60] else 30

    def get_timeline(self) -> dict:
        """
        Retourne la répartition temporelle (début, fin) des scènes.
        Version épurée contenant uniquement le Titre (Hook), le Prix et le CTA.
        """
        if self.duration == 15:
            return {
                "hook": (0.0, 5.0),
                "price": (9.0, 12.0),
                "cta": (0.0, 15.0)
            }
        elif self.duration == 45:
            return {
                "hook": (0.0, 15.0),
                "price": (27.0, 36.0),
                "cta": (0.0, 45.0)
            }
        elif self.duration == 60:
            return {
                "hook": (0.0, 20.0),
                "price": (38.0, 48.0),
                "cta": (0.0, 60.0)
            }
        else: # 30 secondes par défaut
            return {
                "hook": (0.0, 10.0),
                "price": (18.0, 24.0),
                "cta": (0.0, 30.0)
            }

    def get_content_data(self) -> dict:
        """
        Récupère et nettoie les textes à afficher dans chaque scène.
        Extrait les données de la campagne et du contenu généré par l'IA.
        """
        nom_produit = self.campaign.nom_produit.strip()
        description = self.campaign.description.strip()
        prix = self.campaign.prix.strip()
        ancien_prix = (self.campaign.ancien_prix or "").strip()
        whatsapp = self.campaign.cible.strip()
        ville = (self.campaign.ville_label or self.campaign.ville or "").strip()

        # Essayer de récupérer le contenu généré par l'IA (AdContent)
        titles = []
        desc_gen = ""
        benefits = []
        try:
            content = self.campaign.content
            titles = content.titles or []
            desc_gen = content.description_generated or ""
            benefits = content.benefits or []
        except Exception:
            pass

        # 1. Résolution du Hook
        # On utilise le premier titre de l'IA, sinon le nom du produit précédé d'un mot d'accroche
        hook_title = ""
        if titles:
            hook_title = titles[0]
        else:
            hook_title = f"DÉCOUVREZ {nom_produit.upper()}"
        
        # 2. Résolution de la Présentation
        # Utilise le deuxième titre de l'IA ou un extrait court de la description
        presentation_text = ""
        if len(titles) > 1:
            presentation_text = titles[1]
        elif desc_gen:
            presentation_text = desc_gen[:60] + "..." if len(desc_gen) > 60 else desc_gen
        else:
            presentation_text = description[:60] + "..." if len(description) > 60 else description

        # 3. Résolution des Bénéfices
        # Extrait les bénéfices de l'IA (jusqu'à 3 max pour l'affichage vertical)
        clean_benefits = []
        if benefits:
            clean_benefits = [b.strip().replace("✓", "").strip() for b in benefits if b.strip()]
        
        # Fallbacks si pas de bénéfices IA
        if not clean_benefits:
            # Essayer d'extraire des phrases de la description
            parts = [p.strip() for p in description.split(".") if p.strip()]
            for p in parts[:3]:
                if len(p) > 10:
                    clean_benefits.append(p[:40])
        
        # S'assurer d'avoir au moins 3 éléments
        while len(clean_benefits) < 3:
            if len(clean_benefits) == 0:
                clean_benefits.append("Qualité supérieure garantie")
            elif len(clean_benefits) == 1:
                clean_benefits.append("Satisfaction client garantie")
            else:
                clean_benefits.append("Prise de contact rapide")

        # Garder uniquement les 3 premiers
        clean_benefits = clean_benefits[:3]

        # 4. Textes additionnels pour vidéos longues (45s, 60s)
        extra_text = ""
        if len(titles) > 2:
            extra_text = titles[2]
        else:
            extra_text = "Profitez de notre offre dès aujourd'hui"

        offer_text = "OFFRE SPÉCIALE À NE PAS MANQUER !"

        return {
            "nom_produit": nom_produit,
            "hook": hook_title,
            "presentation": presentation_text,
            "benefits": clean_benefits,
            "prix": prix,
            "ancien_prix": ancien_prix,
            "whatsapp": whatsapp,
            "ville": ville,
            "extra": extra_text,
            "offer": offer_text
        }
