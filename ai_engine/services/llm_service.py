import logging
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client

logger = logging.getLogger(__name__)

def call_llm(system_prompt: str, user_prompt: str, model: str = "gemini-3.6-flash") -> str:
    """
    Appelle OpenAI en priorité. Gemini reste disponible en secours.
    """
    try:
        from ai_engine.services.openai_adapter import call_openai
        return call_openai(system_prompt, user_prompt)
    except Exception as openai_error:
        logger.warning(f"[call_llm] OpenAI indisponible, tentative Gemini: {openai_error}")

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
