import logging
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client

logger = logging.getLogger(__name__)

def call_llm(system_prompt: str, user_prompt: str, model: str = "gemini-2.5-flash") -> str:
    """
    Appelle le modèle Gemini de Google (via Vertex AI) avec un prompt système et utilisateur.
    """
    logger.info(f"[call_llm] Appel de {model}...")
    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI : {err}")

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"[call_llm] Erreur lors de l'appel à Gemini: {e}")
        raise
