import json
import re
from typing import Any

import requests
from requests.exceptions import RequestException
from django.conf import settings


import os
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client pour Gemini (anciennement Ollama), utilisant Google GenAI sur Vertex AI ou API REST."""

    def __init__(self, model: str | None = None) -> None:
        self.key_path = getattr(settings, "GCP_VERTEX_KEY_PATH", "")
        self.model = model or "gemini-2.5-flash"
        self.timeout = getattr(settings, "OLLAMA_TIMEOUT", 60)

    def generate(self, prompt: str, system: str = '', temperature: float = 0.7) -> str:
        # 1. Attempt using Vertex AI SDK
        if self.key_path and os.path.exists(self.key_path):
            try:
                from google import genai
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.key_path
                with open(self.key_path, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                project_id = key_data.get("project_id", "e-shelle")
                
                client = genai.Client(
                    vertexai=True,
                    project=project_id,
                    location="us-central1"
                )
                
                # Combine system instructions if provided
                full_prompt = prompt
                if system:
                    full_prompt = f"System Instructions: {system}\n\nUser Prompt: {prompt}"
                
                logger.info(f"Generating content via Vertex Gemini model {self.model}...")
                response = client.models.generate_content(
                    model=self.model,
                    contents=full_prompt
                )
                return response.text.strip()
            except Exception as e:
                logger.warning(f"Failed to generate text via Vertex GenAI Client: {e}. Trying REST fallback...")

        # 2. Attempt using REST API fallback
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                contents = [{"parts": [{"text": prompt}]}]
                payload = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature}
                }
                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}
                
                logger.info(f"Generating content via REST Gemini model {self.model}...")
                res = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                res.raise_for_status()
                res_data = res.json()
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e2:
                logger.warning(f"REST Gemini fallback failed: {e2}")

        # 3. Last fallback: use the local hardcoded fallback
        logger.warning("All Gemini generation attempts failed. Using static fallback text.")
        return self._fallback_text(prompt, system)

    def _fallback_text(self, prompt: str, system: str) -> str:
        if 'Découpe le scénario' in prompt:
            return '''[
  {"order": 1, "title": "Scène 1", "description": "Une scène d’introduction captivante.", "narration": "Une voix off présente le contexte et le personnage principal.", "duration_seconds": 6.0},
  {"order": 2, "title": "Scène 2", "description": "Le personnage découvre un enjeu important.", "narration": "Le récit progresse avec une tension croissante.", "duration_seconds": 6.0},
  {"order": 3, "title": "Scène 3", "description": "Une décision cruciale est prise.", "narration": "Le protagoniste prend un tournant décisif.", "duration_seconds": 6.0},
  {"order": 4, "title": "Scène 4", "description": "Un obstacle important apparaît.", "narration": "La tension monte et les émotions sont fortes.", "duration_seconds": 6.0},
  {"order": 5, "title": "Scène 5", "description": "La solution commence à émerger.", "narration": "Le protagoniste trouve une piste pour avancer.", "duration_seconds": 6.0},
  {"order": 6, "title": "Scène 6", "description": "La conclusion offre une résolution forte.", "narration": "Le récit se termine sur une note inspirante.", "duration_seconds": 6.0}
]'''
        if 'Transforme ces scènes' in prompt:
            return '''[
  {"order": 1, "image_prompt": "Cinematic photorealistic scene of an emotional introduction, wide angle, high quality", "negative_prompt": "blurry, low quality, text, logo"},
  {"order": 2, "image_prompt": "Cinematic photorealistic scene of a character discovering a challenge, moody lighting, detailed background", "negative_prompt": "blurry, low quality, text, logo"},
  {"order": 3, "image_prompt": "Cinematic photorealistic scene of a decisive moment, dramatic composition, sharp focus", "negative_prompt": "blurry, low quality, text, logo"},
  {"order": 4, "image_prompt": "Cinematic photorealistic scene of rising tension and challenge, atmospheric light", "negative_prompt": "blurry, low quality, text, logo"},
  {"order": 5, "image_prompt": "Cinematic photorealistic scene of a breakthrough, hopeful mood, rich detail", "negative_prompt": "blurry, low quality, text, logo"},
  {"order": 6, "image_prompt": "Cinematic photorealistic scene of a strong resolution, cinematic style, golden hour lighting", "negative_prompt": "blurry, low quality, text, logo"}
]'''
        return (
            'Titre : Histoire de test locale\n\n'
            'Synopsis : Une histoire courte générée en mode de secours pour tester le flux local.\n\n'
            'Une jeune personne se trouve confrontée à un défi inattendu.\n'
            'Elle découvre une force intérieure et avance vers une solution.\n\n'
            'Le récit se termine sur une note inspirante et émotive.\n'
        )


def extract_json(text: str) -> Any:
    """Extrait un objet ou tableau JSON d'une réponse LLM parfois entourée de texte."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'```$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'(\{.*\}|\[.*\])', cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))
