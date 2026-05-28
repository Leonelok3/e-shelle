"""
AdGen — Construction dynamique du prompt IA
"""
import json


MODULES_INSTRUCTIONS = {
    "titres": 'Génère "titles": [liste de 3 titres accrocheurs et vendeurs]',
    "description": 'Génère "description": "texte de vente 3-4 phrases" et "benefits": [liste de 5 bénéfices clients concrets]',
    "social": 'Génère "facebook": "post Facebook engageant", "instagram": "légende Instagram avec emojis", "whatsapp": "message WhatsApp direct et humain", "hashtags": [liste de 10 hashtags pertinents]',
    "tiktok": 'Génère "video_script": "script TikTok 20 secondes : hook 3s + présentation 10s + CTA 7s"',
    "chatbot": 'Génère "chatbot_reply": "réponse naturelle d\'un vendeur à la question \'c\'est quoi ce produit ?\', orientée achat, max 4 phrases"',
}

SYSTEM_TEMPLATE = """Tu es un expert en marketing digital, copywriting, vente en ligne et psychologie d'achat, spécialisé dans les marchés africains (Afrique Centrale, Afrique de l'Ouest).

OBJECTIF: Transformer le produit fourni en contenu marketing professionnel, engageant et hautement convertissant.

RÈGLES ABSOLUES:
- Langage simple, naturel, orienté vente
- Priorité aux bénéfices clients (pas aux caractéristiques)
- Références culturelles africaines appropriées pour le pays cible
- Adapter les exemples, le ton, les habitudes d'achat et le CTA à la ville cible quand elle est fournie
- Mettre en avant prix + praticité + accessibilité
- Sentiment d'urgence si pertinent
- SORTIE JSON UNIQUEMENT — pas de markdown, pas de texte avant ou après, pas de ```json
- Chaque valeur doit être une chaîne ou liste valide JSON

PAYS CIBLE: {pays}
VILLE CIBLE: {ville}
MODULES ACTIFS: {active_modules}

DONNÉES PRODUIT:
{product_json}

Génère UNIQUEMENT les clés JSON pour les modules actifs:
{modules_instructions}

Réponds avec uniquement le JSON, rien d'autre."""


class PromptBuilder:

    @staticmethod
    def build(product_data: dict, modules: list) -> str:
        """Construit le prompt final à envoyer à l'API."""
        active_modules = ", ".join(modules)

        instructions_lines = []
        for mod in modules:
            if mod in MODULES_INSTRUCTIONS:
                instructions_lines.append(f"- {MODULES_INSTRUCTIONS[mod]}")

        product_json = json.dumps(product_data, ensure_ascii=False, indent=2)
        pays = product_data.get("pays_label", product_data.get("pays", "Cameroun"))
        ville = product_data.get("ville_label") or "Toutes les villes"

        return SYSTEM_TEMPLATE.format(
            pays=pays,
            ville=ville,
            active_modules=active_modules,
            product_json=product_json,
            modules_instructions="\n".join(instructions_lines),
        )
