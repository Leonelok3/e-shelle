"""
AdGen — Service de génération publicitaire utilisant les crédits Vertex AI
"""
import json
import logging
import os

from django.conf import settings
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AdGenAIService:
    """
    Appelle l'API d'intelligence artificielle pour générer du contenu publicitaire.
    Utilise en priorité Vertex AI (Gemini 2.5 Pro) avec les crédits Google Cloud,
    puis l'API Google AI Studio standard, et enfin Anthropic Claude en fallback.
    """
    MAX_TOKENS = 3000

    def __init__(self):
        self.key_path = getattr(settings, "GCP_VERTEX_KEY_PATH", "")
        self.client_type = None
        self.google_client = None
        self.anthropic_client = None

        # 1. Tenter d'initialiser Google GenAI avec Vertex AI (crédits GCP)
        if self.key_path and os.path.exists(self.key_path):
            try:
                from google import genai
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.key_path
                with open(self.key_path, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                project_id = key_data.get("project_id", "e-shelle")
                self.google_client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location="us-central1"
                )
                self.client_type = "vertex"
                logger.info(f"[AdGen] Initialisé avec Vertex AI (Projet: {project_id})")
            except Exception as e:
                logger.warning(f"[AdGen] Échec de l'initialisation Vertex AI: {e}")

        # 2. Tenter d'initialiser Google AI Studio (si API key configurée)
        if not self.google_client:
            google_api_key = getattr(settings, "GOOGLE_API_KEY", "")
            if google_api_key:
                try:
                    from google import genai
                    self.google_client = genai.Client(api_key=google_api_key)
                    self.client_type = "gemini_api"
                    logger.info("[AdGen] Initialisé avec Gemini API Studio")
                except Exception as e:
                    logger.warning(f"[AdGen] Échec de l'initialisation Gemini API Studio: {e}")

        # 3. Tenter d'initialiser Anthropic Claude (ancien comportement)
        if not self.google_client:
            anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            if anthropic_key:
                try:
                    import anthropic
                    self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                    self.client_type = "anthropic"
                    logger.info("[AdGen] Initialisé avec Anthropic Claude")
                except Exception as e:
                    logger.warning(f"[AdGen] Échec de l'initialisation Anthropic: {e}")

        if not self.google_client and not self.anthropic_client:
            logger.warning("[AdGen] Aucun client d'IA externe n'a pu être configuré.")

    def generate(self, product_data: dict, modules: list) -> dict:
        """
        Appelle le meilleur service d'IA disponible et retourne le contenu sous forme de dictionnaire.
        """
        prompt = PromptBuilder.build(product_data, modules)
        logger.info(f"[AdGen] Génération avec client_type={self.client_type} pour produit='{product_data.get('nom_produit')}' modules={modules}")

        raw_text = ""
        tokens_used = 0
        model_used = "Inconnu"

        if self.client_type in ["vertex", "gemini_api"] and self.google_client:
            # 1. Utiliser le modèle haut de gamme Gemini 2.5 Pro pour le meilleur rendu rédactionnel possible
            model_used = "Gemini 2.5 Pro (Vertex AI)" if self.client_type == "vertex" else "Gemini 2.5 Pro"
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.8,
                    max_output_tokens=self.MAX_TOKENS,
                )
                logger.info(f"[AdGen] Envoi de la requête à {model_used}...")
                response = self.google_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=prompt,
                    config=config
                )
                raw_text = response.text.strip()
                if response.usage_metadata:
                    tokens_used = response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count
                else:
                    tokens_used = 1500
            except Exception as e:
                logger.warning(f"[AdGen] Échec avec Gemini 2.5 Pro: {e}. Essai du modèle rapide Gemini 2.5 Flash...")
                
                # Fallback sur Gemini 2.5 Flash
                model_used = "Gemini 2.5 Flash (Vertex AI)" if self.client_type == "vertex" else "Gemini 2.5 Flash"
                try:
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                        max_output_tokens=self.MAX_TOKENS,
                    )
                    response = self.google_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=config
                    )
                    raw_text = response.text.strip()
                    if response.usage_metadata:
                        tokens_used = response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count
                    else:
                        tokens_used = 1000
                except Exception as e2:
                    logger.error(f"[AdGen] Échec de la génération avec Gemini 2.5 Flash: {e2}")
                    raise RuntimeError(f"Échec complet de la génération Gemini: {e2}")

        elif self.client_type == "anthropic" and self.anthropic_client:
            model_used = "Claude 3.5 Sonnet"
            try:
                logger.info(f"[AdGen] Envoi de la requête à Anthropic ({model_used})...")
                message = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=self.MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = message.content[0].text.strip()
                tokens_used = message.usage.input_tokens + message.usage.output_tokens
            except Exception as e:
                logger.error(f"[AdGen] Échec de la génération avec Anthropic: {e}")
                raise RuntimeError(f"Échec de génération Anthropic: {e}")
        else:
            raise RuntimeError("Aucun client IA valide n'est configuré pour la génération en ligne.")

        # Nettoyage des balises de code JSON si le modèle en a rajouté malgré la consigne
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"[AdGen] JSON malformé retourné par {model_used}: {e}\nTexte brut: {raw_text[:500]}")
            raise ValueError(f"La réponse de l'IA n'est pas un JSON valide : {e}")

        # Injecter le modèle utilisé et le mode de génération dans le résultat
        result["_tokens_used"] = tokens_used
        result["_raw"] = raw_text
        result["generation_model"] = model_used
        
        return result
