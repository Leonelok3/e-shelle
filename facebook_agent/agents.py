"""
Agents IA E-Shelle Facebook Auto-Post.
Chaque agent est spécialisé pour une section de la plateforme.
Utilise Claude claude-sonnet-4-6 pour la génération de contenu.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import anthropic
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("facebook_agent")


# ------------------------------------------------------------------ #
# Prompts système par section                                          #
# ------------------------------------------------------------------ #

SYSTEM_PROMPTS = {
    "annonces": """Tu es l'agent Facebook d'E-Shelle, la plateforme multi-services du Cameroun.
Tu crées des posts engageants pour promouvoir les annonces publiées sur e-shelle.com.
Ton style : chaleureux, direct, en français camerounais moderne.
Tu mets en avant la valeur de l'offre et incites à visiter le site.
Toujours terminer avec un appel à l'action vers e-shelle.com""",

    "immobilier": """Tu es l'agent immobilier d'E-Shelle sur Facebook.
Tu présentes des biens immobiliers (maisons, appartements, terrains) au Cameroun.
Style professionnel mais accessible, en français.
Tu mets en avant les caractéristiques clés: localisation, prix, surface.
Appel à l'action: visiter e-shelle.com/immobilier""",

    "auto": """Tu es l'agent automobile d'E-Shelle sur Facebook.
Tu présentes des véhicules disponibles à la vente au Cameroun.
Style dynamique et enthousiaste. Mets en avant: marque, modèle, année, prix, kilométrage.
Appel à l'action: voir les détails sur e-shelle.com/auto""",

    "agro": """Tu es l'agent agriculture d'E-Shelle sur Facebook.
Tu informes sur les produits agricoles, les prix du marché et les opportunités agro au Cameroun.
Style informatif et pratique, proche des agriculteurs et acheteurs.
Contexte: Cameroun, marchés locaux, agriculture durable.
Appel à l'action: e-shelle.com/agro""",

    "rencontres": """Tu es l'agent E-Shelle Love, l'app de rencontres sérieuses d'E-Shelle.
Tu crées du contenu romantique, inspirant et positif sur l'amour et les rencontres.
Style: chaleureux, romantique, bienveillant. Public: adultes 20-45 ans au Cameroun.
Tu peux partager des conseils amoureux, des citations, des témoignages fictifs positifs.
Ne jamais être vulgaire. Toujours positif et respectueux.
Appel à l'action: rejoindre E-Shelle Love sur e-shelle.com/rencontres""",

    "njangi": """Tu es l'agent Njangi d'E-Shelle sur Facebook.
Tu informes sur les tontines digitales, l'épargne communautaire et la microfinance au Cameroun.
Style: confiance, solidarité, communauté. Tu valorises l'entraide financière.
Public: adultes qui cherchent à épargner et investir ensemble.
Appel à l'action: créer ou rejoindre un groupe sur e-shelle.com/njangi""",

    "edu": """Tu es l'agent éducation d'E-Shelle sur Facebook.
Tu promeus les cours, formations et ressources éducatives disponibles sur la plateforme.
Style: motivant, professionnel, orienté réussite. Public: étudiants et parents.
Tu peux partager des conseils d'études, des infos sur les examens camerounais.
Appel à l'action: apprendre sur e-shelle.com/edu""",

    "promo": """Tu es l'agent promotions d'E-Shelle sur Facebook.
Tu annonces les offres spéciales, réductions et avantages premium de la plateforme.
Style: enthousiaste, urgent, accrocheur. Crée un sentiment d'urgence léger.
Mets en avant la valeur et les économies réalisées.
Appel à l'action: profiter de l'offre sur e-shelle.com""",

    "resto": """Tu es l'agent restaurants d'E-Shelle sur Facebook.
Tu présentes les restaurants, plats et offres gastronomiques disponibles au Cameroun.
Style: appétissant, convivial, qui donne envie. Décris les saveurs et l'ambiance.
Appel à l'action: commander ou réserver sur e-shelle.com/resto""",

    "general": """Tu es l'agent principal d'E-Shelle sur Facebook.
Tu crées du contenu engageant sur la plateforme E-Shelle et ses 17+ services.
Style: dynamique, moderne, inspirant. Tu représentes une plateforme tech africaine de référence.
Tu peux partager des actualités, tips, témoignages, et la vision d'E-Shelle.
Toujours positif et orienté communauté. Appel à l'action: e-shelle.com""",

    "services": """Tu es l'agent services d'E-Shelle sur Facebook.
Tu présentes les services disponibles: livraison gaz, pharmacie, pressing, etc.
Style: pratique, rassurant, proche du quotidien. Mets en avant la facilité et rapidité.
Appel à l'action: commander sur e-shelle.com""",

    "gaz": """Tu es l'agent gaz domestique d'E-Shelle à Douala.
Tu crées des posts simples, urgents et très pratiques pour montrer qu'un client peut trouver un dépôt de gaz proche via E-Shelle AI.
Style: terrain, direct, camerounais, orienté problème du soir, cuisine, famille, livraison et WhatsApp.
Appel à l'action: commander du gaz sur e-shelle.com/gaz/ ou demander dans le chat E-Shelle AI.""",

    "pressing": """Tu es l'agent pressing d'E-Shelle.
Tu montres comment trouver un pressing fiable, demander collecte/livraison et contacter par WhatsApp.
Style: propre, pratique, urbain, adapté aux travailleurs, étudiants et familles à Douala.
Appel à l'action: trouver un pressing sur e-shelle.com/pressing/.""",

    "sante": """Tu es l'agent santé/pharmacies d'E-Shelle.
Tu crées des posts prudents et utiles pour aider les gens à trouver pharmacies, produits santé et professionnels proches.
Style: rassurant, clair, sans diagnostic médical, toujours orienté contact professionnel.
Appel à l'action: chercher un service santé sur e-shelle.com/sante/.""",

    "jobs": """Tu es l'agent jobs d'E-Shelle.
Tu aides les jeunes, étudiants, freelances et travailleurs à découvrir des offres, stages et missions au Cameroun.
Style: motivant, concret, orienté opportunités locales.
Appel à l'action: consulter les offres sur e-shelle.com/jobs/.""",

    "business": """Tu es l'agent prestataires E-Shelle.
Tu recrutes les restaurants, pressings, dépôts de gaz, pharmacies, boutiques et services de quartier.
Style: business terrain, très clair: créer sa fiche, recevoir des clients sur WhatsApp, booster sa visibilité, payer un abonnement adapté au Cameroun.
Appel à l'action: créer sa fiche sur e-shelle.com/business/plans/.""",

    "chat_ai": """Tu es l'agent E-Shelle AI.
Tu racontes des mini-histoires africaines courtes qui montrent comment une personne tape simplement son besoin dans le chat et trouve un service.
Style: viral, narratif, TikTok/Reels compatible, 1 problème réel + 1 solution simple + CTA.
Appel à l'action: tester le chat sur e-shelle.com/chat/.""",
}

HASHTAGS_BY_SECTION = {
    "annonces": "#EShelle #Annonces #Cameroun #Vente #Achat #Marketplace #Douala #Yaoundé",
    "immobilier": "#EShelle #Immobilier #Cameroun #Maison #Appartement #Terrain #Douala #Yaoundé #LogementCameroun",
    "auto": "#EShelle #Auto #Voiture #Cameroun #Vente #Occasion #Douala #AutoCameroun",
    "agro": "#EShelle #Agriculture #Agro #Cameroun #Fermier #Marché #PrixDuMarché #AgroCameroun",
    "rencontres": "#EShelLeLove #Rencontres #Amour #Cameroun #CélibatairesAfricains #TrouverLAmour",
    "njangi": "#EShelle #Njangi #Tontine #Épargne #Cameroun #SolidaritéFinancière #MicroFinance",
    "edu": "#EShelle #Education #Cameroun #Cours #Formation #Apprendre #Étudiant #BAC #Concours",
    "promo": "#EShelle #Promo #Offre #Cameroun #BonPlan #Premium #Réduction",
    "resto": "#EShelle #Restaurant #Food #Cameroun #Gastronomie #Manger #Douala",
    "general": "#EShelle #Cameroun #Tech #Innovation #Afrique #Digital #Plateforme",
    "services": "#EShelle #Services #Cameroun #Livraison #Pratique #Quotidien",
    "gaz": "#EShelle #Gaz #Douala #Bonamoussadi #LivraisonGaz #Cameroun #ServiceLocal",
    "pressing": "#EShelle #Pressing #Douala #LingePropre #ServiceLocal #Cameroun",
    "sante": "#EShelle #Sante #Pharmacie #Douala #Cameroun #ServiceSante",
    "jobs": "#EShelle #Jobs #Emploi #Stage #Douala #Cameroun #Opportunites",
    "business": "#EShelleBusiness #Prestataires #Douala #EntrepreneurCameroun #WhatsAppBusiness #GagnerArgent",
    "chat_ai": "#EShelleAI #IntelligenceArtificielle #Douala #Cameroun #SuperAppAfricaine #TechAfrica",
}


class BaseAgent:
    """Agent de base avec génération de contenu Claude."""

    def __init__(self, section: str, rule=None):
        self.section = section
        self.rule = rule
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self.tokens_used = 0

    def _get_system_prompt(self) -> str:
        base = SYSTEM_PROMPTS.get(self.section, SYSTEM_PROMPTS["general"])
        if self.rule and self.rule.custom_instructions:
            base += f"\n\nInstructions supplémentaires: {self.rule.custom_instructions}"
        return base

    def _get_max_tokens(self) -> int:
        if self.rule:
            return min(self.rule.max_post_length // 2, 400)
        return 300

    def generate_content(self, prompt: str, context: dict = None) -> str:
        """Génère du contenu avec Claude claude-sonnet-4-6."""
        start = time.time()
        system = self._get_system_prompt()

        include_emoji = self.rule.include_emoji if self.rule else True
        include_hashtags = self.rule.include_hashtags if self.rule else True
        max_length = self.rule.max_post_length if self.rule else 500

        full_prompt = f"""{prompt}

Contraintes:
- Longueur maximale: {max_length} caractères
- {"Inclure des emojis pertinents" if include_emoji else "Pas d'emojis"}
- {"Terminer avec les hashtags: " + HASHTAGS_BY_SECTION.get(self.section, "") if include_hashtags else "Pas de hashtags"}
- Langue: Français (Cameroun)
- Ton: {self.rule.get_tone_display() if self.rule else "Amical & Chaleureux"}

Génère directement le texte du post Facebook, sans introduction ni explication."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self._get_max_tokens(),
                system=system,
                messages=[{"role": "user", "content": full_prompt}],
            )
            content = response.content[0].text.strip()
            self.tokens_used = response.usage.input_tokens + response.usage.output_tokens
            duration = int((time.time() - start) * 1000)
            logger.info(
                f"[Agent:{self.section}] Contenu généré en {duration}ms, {self.tokens_used} tokens"
            )
            return content
        except anthropic.APIError as e:
            logger.error(f"[Agent:{self.section}] Erreur Claude API: {e}")
            raise

    def run(self) -> Optional[Dict[str, Any]]:
        """À implémenter par chaque agent spécialisé."""
        raise NotImplementedError


# ------------------------------------------------------------------ #
# Agent Annonces                                                       #
# ------------------------------------------------------------------ #

class AnnoncesAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("annonces", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        """Génère un post sur les dernières annonces publiées."""
        try:
            from annonces_cam.models import Annonce
            recent = Annonce.objects.filter(
                status="publiee"
            ).select_related("categorie").order_by("-created_at")[:5]

            if not recent.exists():
                annonces_info = "Nouvelle section d'annonces avec des centaines d'offres"
            else:
                annonces_info = "\n".join([
                    f"- {a.titre} | {a.prix} FCFA | {a.ville}" for a in recent
                ])

            prompt = f"""Crée un post Facebook accrocheur pour promouvoir ces annonces récentes sur E-Shelle:

{annonces_info}

Le post doit donner envie de visiter la plateforme pour voir toutes les annonces disponibles."""

            content = self.generate_content(prompt)
            return {
                "section": "annonces",
                "content": content,
                "title": "Post Annonces Récentes",
                "link_url": "https://e-shelle.com/annonces/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[AnnoncesAgent] Erreur: {e}")
            return self._fallback_post()

    def _fallback_post(self) -> Dict[str, Any]:
        prompt = """Crée un post Facebook engageant pour promouvoir la section Annonces d'E-Shelle.com.
Parle des opportunités de vente et d'achat au Cameroun. Sois enthousiaste et invitant."""
        content = self.generate_content(prompt)
        return {
            "section": "annonces",
            "content": content,
            "title": "Post Annonces Générique",
            "link_url": "https://e-shelle.com/annonces/",
            "tokens_used": self.tokens_used,
        }


# ------------------------------------------------------------------ #
# Agent Immobilier                                                     #
# ------------------------------------------------------------------ #

class ImmobilierAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("immobilier", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        try:
            from immobilier_cameroun.models import Bien
            recent = Bien.objects.filter(
                statut="disponible"
            ).order_by("-created_at")[:3]

            if recent.exists():
                biens_info = "\n".join([
                    f"- {b.type_bien} à {b.ville} | {b.prix} FCFA | {b.surface}m²"
                    for b in recent
                ])
                prompt = f"""Crée un post Facebook professionnel pour ces biens immobiliers disponibles sur E-Shelle:

{biens_info}

Mets en avant la qualité des biens et la facilité de trouver un logement via E-Shelle."""
            else:
                prompt = """Crée un post Facebook pour promouvoir la section immobilier d'E-Shelle.
Parle de la facilité de trouver une maison, appartement ou terrain au Cameroun via la plateforme."""

            content = self.generate_content(prompt)
            return {
                "section": "immobilier",
                "content": content,
                "title": "Post Immobilier",
                "link_url": "https://e-shelle.com/immobilier/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[ImmobilierAgent] Erreur: {e}")
            prompt = """Crée un post Facebook pour la section immobilier d'E-Shelle au Cameroun.
Parle des opportunités immobilières: maisons, appartements, terrains."""
            content = self.generate_content(prompt)
            return {
                "section": "immobilier",
                "content": content,
                "title": "Post Immobilier Générique",
                "link_url": "https://e-shelle.com/immobilier/",
                "tokens_used": self.tokens_used,
            }


# ------------------------------------------------------------------ #
# Agent Automobile                                                     #
# ------------------------------------------------------------------ #

class AutoAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("auto", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        try:
            from auto_cameroun.models import Vehicule
            recent = Vehicule.objects.filter(
                statut="disponible"
            ).order_by("-created_at")[:3]

            if recent.exists():
                vehicules_info = "\n".join([
                    f"- {v.marque} {v.modele} {v.annee} | {v.prix} FCFA | {v.kilometrage}km"
                    for v in recent
                ])
                prompt = f"""Crée un post Facebook dynamique pour ces véhicules en vente sur E-Shelle:

{vehicules_info}

Donne envie d'acheter ou de vendre une voiture via la plateforme."""
            else:
                prompt = """Crée un post Facebook dynamique pour la section auto d'E-Shelle.
Parle de l'achat et la vente de véhicules au Cameroun."""

            content = self.generate_content(prompt)
            return {
                "section": "auto",
                "content": content,
                "title": "Post Automobile",
                "link_url": "https://e-shelle.com/auto/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[AutoAgent] Erreur: {e}")
            prompt = "Crée un post Facebook pour la section automobile d'E-Shelle au Cameroun."
            content = self.generate_content(prompt)
            return {
                "section": "auto",
                "content": content,
                "title": "Post Auto Générique",
                "link_url": "https://e-shelle.com/auto/",
                "tokens_used": self.tokens_used,
            }


# ------------------------------------------------------------------ #
# Agent Agriculture                                                    #
# ------------------------------------------------------------------ #

class AgroAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("agro", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        try:
            from agro.models import ProduitAgro
            recent = ProduitAgro.objects.filter(
                disponible=True
            ).order_by("-created_at")[:5]

            if recent.exists():
                produits_info = "\n".join([
                    f"- {p.nom} | {p.prix} FCFA/{p.unite}"
                    for p in recent
                ])
                prompt = f"""Crée un post Facebook informatif sur ces produits agricoles disponibles sur E-Shelle Agro:

{produits_info}

Mets en avant la fraîcheur, les prix et la disponibilité. Encourage agriculteurs et acheteurs."""
            else:
                prompt = """Crée un post Facebook sur E-Shelle Agro, la marketplace agricole du Cameroun.
Parle des opportunités pour les agriculteurs et acheteurs de produits frais."""

            content = self.generate_content(prompt)
            return {
                "section": "agro",
                "content": content,
                "title": "Post Agriculture",
                "link_url": "https://e-shelle.com/agro/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[AgroAgent] Erreur: {e}")
            prompt = "Crée un post Facebook pour E-Shelle Agro, la marketplace agricole camerounaise."
            content = self.generate_content(prompt)
            return {
                "section": "agro",
                "content": content,
                "title": "Post Agro Générique",
                "link_url": "https://e-shelle.com/agro/",
                "tokens_used": self.tokens_used,
            }


# ------------------------------------------------------------------ #
# Agent Rencontres (E-Shelle Love)                                    #
# ------------------------------------------------------------------ #

LOVE_POST_TYPES = [
    "conseil_amour",
    "citation_romantique",
    "temoignage",
    "conseil_relation",
    "promotion_app",
]


class RencontresAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("rencontres", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        from random import choice
        post_type = choice(LOVE_POST_TYPES)

        prompts_map = {
            "conseil_amour": "Crée un post Facebook avec un conseil amoureux bienveillant pour trouver l'âme sœur au Cameroun. Promeus E-Shelle Love.",
            "citation_romantique": "Crée un post Facebook avec une belle citation romantique originale sur l'amour, adapté au contexte africain. Mentionne E-Shelle Love.",
            "temoignage": "Crée un post Facebook avec un témoignage fictif et positif d'un couple qui s'est rencontré via E-Shelle Love. Sois chaleureux et authentique.",
            "conseil_relation": "Crée un post Facebook avec un conseil pour construire une relation solide et durable. Public: célibataires camerounais. Mentionne E-Shelle Love.",
            "promotion_app": "Crée un post Facebook promotionnel pour E-Shelle Love, l'app de rencontres sérieuses du Cameroun. Mets en avant les fonctionnalités (matchmaking, profils vérifiés, messagerie).",
        }

        prompt = prompts_map[post_type]
        try:
            content = self.generate_content(prompt)
            return {
                "section": "rencontres",
                "content": content,
                "title": f"Post Love — {post_type}",
                "link_url": "https://e-shelle.com/rencontres/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[RencontresAgent] Erreur: {e}")
            return None


# ------------------------------------------------------------------ #
# Agent Njangi                                                         #
# ------------------------------------------------------------------ #

class NjangiAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("njangi", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        from random import choice
        post_types = [
            "Crée un post Facebook sur les avantages de la tontine digitale E-Shelle Njangi. Explique comment épargner facilement avec ses amis et famille.",
            "Crée un post Facebook motivant sur la solidarité financière en Afrique via E-Shelle Njangi. Valorise l'entraide communautaire.",
            "Crée un post Facebook présentant E-Shelle Njangi comme solution moderne de tontine digitale au Cameroun. Mets en avant la sécurité et la simplicité.",
        ]
        prompt = choice(post_types)
        try:
            content = self.generate_content(prompt)
            return {
                "section": "njangi",
                "content": content,
                "title": "Post Njangi",
                "link_url": "https://e-shelle.com/njangi/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[NjangiAgent] Erreur: {e}")
            return None


# ------------------------------------------------------------------ #
# Agent Promotions                                                     #
# ------------------------------------------------------------------ #

class PromoAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("promo", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        from random import choice
        promos = [
            "Crée un post Facebook annonçant une offre spéciale sur les abonnements premium E-Shelle. Crée un sentiment d'urgence léger. Mets en avant les économies.",
            "Crée un post Facebook pour promouvoir les avantages de passer à E-Shelle Premium: visibilité accrue, contacts illimités, outils avancés.",
            "Crée un post Facebook engageant sur les nouveautés et améliorations récentes d'E-Shelle. Montre que la plateforme évolue constamment pour ses utilisateurs.",
        ]
        prompt = choice(promos)
        try:
            content = self.generate_content(prompt)
            return {
                "section": "promo",
                "content": content,
                "title": "Post Promotionnel",
                "link_url": "https://e-shelle.com/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[PromoAgent] Erreur: {e}")
            return None


# ------------------------------------------------------------------ #
# Agent Général E-Shelle                                              #
# ------------------------------------------------------------------ #

class GeneralAgent(BaseAgent):
    def __init__(self, rule=None):
        super().__init__("general", rule)

    def run(self) -> Optional[Dict[str, Any]]:
        from random import choice
        posts = [
            "Crée un post Facebook inspirant sur la vision d'E-Shelle: une plateforme tout-en-un pour les Camerounais. Parle des 17+ services disponibles.",
            "Crée un post Facebook qui présente E-Shelle comme la super-app africaine de référence. Sois fier et ambitieux.",
            "Crée un post Facebook avec un conseil pratique sur comment utiliser E-Shelle au quotidien pour simplifier sa vie.",
            "Crée un post Facebook célébrant la communauté E-Shelle. Remercie les utilisateurs et parle de la croissance de la plateforme.",
        ]
        prompt = choice(posts)
        try:
            content = self.generate_content(prompt)
            return {
                "section": "general",
                "content": content,
                "title": "Post Général E-Shelle",
                "link_url": "https://e-shelle.com/",
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[GeneralAgent] Erreur: {e}")
            return None


# ------------------------------------------------------------------ #
# Agents croissance Douala                                            #
# ------------------------------------------------------------------ #

class SimpleGrowthAgent(BaseAgent):
    section = "general"
    title = "Post E-Shelle"
    link_url = "https://e-shelle.com/"
    prompts = []

    def __init__(self, rule=None):
        super().__init__(self.section, rule)

    def run(self) -> Optional[Dict[str, Any]]:
        from random import choice

        prompt = choice(self.prompts)
        try:
            content = self.generate_content(prompt)
            return {
                "section": self.section,
                "content": content,
                "title": self.title,
                "link_url": self.link_url,
                "tokens_used": self.tokens_used,
            }
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Erreur: {e}")
            return None


class GazAgent(SimpleGrowthAgent):
    section = "gaz"
    title = "Post Gaz Douala"
    link_url = "https://e-shelle.com/gaz/"
    prompts = [
        "Crée un post Facebook très concret: il est tard à Douala, le gaz finit pendant la cuisine, E-Shelle aide à trouver un dépôt proche et à commander par WhatsApp.",
        "Crée un post Facebook pour expliquer comment commander du gaz à Bonamoussadi, Akwa ou Makepe via E-Shelle AI.",
        "Crée une mini-histoire réaliste d'une famille à Douala qui trouve rapidement du gaz grâce à E-Shelle.",
    ]


class RestoAgent(SimpleGrowthAgent):
    section = "resto"
    title = "Post Restaurants Douala"
    link_url = "https://e-shelle.com/resto/"
    prompts = [
        "Crée un post Facebook appétissant pour aider quelqu'un à trouver un restaurant ou maquis à Douala via E-Shelle.",
        "Crée un post de midi: faim au bureau, envie de bon plat, E-Shelle aide à trouver un resto proche.",
        "Crée une mini-histoire d'un groupe d'amis qui cherche où manger à Douala et utilise E-Shelle.",
    ]


class PressingAgent(SimpleGrowthAgent):
    section = "pressing"
    title = "Post Pressing"
    link_url = "https://e-shelle.com/pressing/"
    prompts = [
        "Crée un post Facebook pour les travailleurs de Douala qui veulent trouver un pressing fiable avec WhatsApp.",
        "Crée un post pratique: vêtements prêts pour lundi, pressing proche, collecte et livraison via E-Shelle.",
        "Crée une mini-histoire d'un client qui évite le stress du linge grâce à E-Shelle Pressing.",
    ]


class SanteAgent(SimpleGrowthAgent):
    section = "sante"
    title = "Post Santé"
    link_url = "https://e-shelle.com/sante/"
    prompts = [
        "Crée un post Facebook rassurant pour trouver une pharmacie ou un produit santé proche via E-Shelle, sans donner de conseil médical.",
        "Crée un post utile: quand on cherche une pharmacie à Douala, E-Shelle aide à trouver un contact rapidement.",
        "Crée une mini-histoire responsable sur une personne qui cherche une pharmacie de garde et utilise E-Shelle pour contacter un professionnel.",
    ]


class JobsAgent(SimpleGrowthAgent):
    section = "jobs"
    title = "Post Jobs"
    link_url = "https://e-shelle.com/jobs/"
    prompts = [
        "Crée un post Facebook motivant pour les jeunes de Douala qui cherchent un stage, un job ou une mission freelance.",
        "Crée un post pratique pour expliquer que les opportunités locales peuvent être trouvées sur E-Shelle Jobs.",
        "Crée une mini-histoire d'un étudiant qui trouve une mission grâce à E-Shelle.",
    ]


class BusinessAgent(SimpleGrowthAgent):
    section = "business"
    title = "Post Prestataires E-Shelle"
    link_url = "https://e-shelle.com/business/plans/"
    prompts = [
        "Crée un post Facebook pour convaincre un restaurant, pressing, dépôt de gaz ou pharmacie de créer sa fiche E-Shelle et recevoir des clients sur WhatsApp.",
        "Crée un post terrain pour les commerçants de Douala: visibilité, demandes reçues, WhatsApp, boosts et abonnement prestataire.",
        "Crée un post commercial pour recruter des prestataires E-Shelle avec un ton direct et orienté argent.",
    ]


class ChatAIStoryAgent(SimpleGrowthAgent):
    section = "chat_ai"
    title = "Story E-Shelle AI"
    link_url = "https://e-shelle.com/chat/"
    prompts = [
        "Crée une mini-histoire Facebook/Reels: quelqu'un tape 'je veux du gaz à Bonamoussadi' dans E-Shelle AI et trouve une solution.",
        "Crée un post narratif court: au Cameroun, on veut tout faire sur WhatsApp, mais E-Shelle AI simplifie la recherche de services.",
        "Crée un script très court pour vidéo IA: problème du quotidien à Douala, phrase tapée dans le chat, résultat immédiat, appel à tester E-Shelle.",
    ]


# ------------------------------------------------------------------ #
# Registry des agents                                                  #
# ------------------------------------------------------------------ #

AGENT_REGISTRY = {
    "annonces": AnnoncesAgent,
    "immobilier": ImmobilierAgent,
    "auto": AutoAgent,
    "agro": AgroAgent,
    "rencontres": RencontresAgent,
    "njangi": NjangiAgent,
    "promo": PromoAgent,
    "general": GeneralAgent,
    "gaz": GazAgent,
    "resto": RestoAgent,
    "pressing": PressingAgent,
    "sante": SanteAgent,
    "jobs": JobsAgent,
    "business": BusinessAgent,
    "chat_ai": ChatAIStoryAgent,
}


def get_agent(section: str, rule=None) -> Optional[BaseAgent]:
    """Retourne l'agent correspondant à une section."""
    agent_class = AGENT_REGISTRY.get(section)
    if agent_class:
        return agent_class(rule=rule)
    logger.warning(f"[AgentRegistry] Aucun agent trouvé pour la section '{section}'")
    return None


def run_agent_for_section(section: str) -> Optional[Dict[str, Any]]:
    """Lance un agent et retourne le résultat prêt pour la publication."""
    from facebook_agent.models import ContentRule

    rule = ContentRule.objects.filter(section=section, is_active=True).first()
    agent = get_agent(section, rule=rule)

    if not agent:
        return None

    try:
        result = agent.run()
        if result:
            result["tokens_used"] = agent.tokens_used
        return result
    except Exception as e:
        logger.error(f"[AgentRunner] Erreur pour section '{section}': {e}")
        return None
