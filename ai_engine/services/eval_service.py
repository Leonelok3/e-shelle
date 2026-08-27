import os
import json
import logging
from django.conf import settings
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client
from ai_engine.services.openai_adapter import call_openai_json

logger = logging.getLogger(__name__)

# Langue par défaut = "de" pour préserver le comportement historique (GermanPrepApp)
_LANGUAGE_ADJ_FEM = {
    "de": "allemande",
    "fr": "française",
    "en": "anglaise",
    "it": "italienne",
}
_LANGUAGE_ADJ_MASC = {
    "de": "allemand",
    "fr": "français",
    "en": "anglais",
    "it": "italien",
}
_LANGUAGE_PHRASES = {
    "de": "d'allemand",
    "fr": "de français",
    "en": "d'anglais",
    "it": "d'italien",
}
_LANGUAGE_CERT_BODIES = {
    "de": "Goethe-Institut, telc, TestDaF",
    "fr": "France Éducation International (TEF, TCF), DELF/DALF",
    "en": "IELTS, TOEFL, Cambridge",
    "it": "CILS, CELI, PLIDA",
}


def _language_key(language: str) -> str:
    key = (language or "de").lower()
    return key if key in _LANGUAGE_ADJ_FEM else "de"


def transcribe_audio(audio_path: str, language: str = "de") -> str:
    """
    Transcrit un fichier audio. OpenAI est utilisé en priorité, Gemini en secours.
    """
    logger.info(f"[eval_service] Transcription audio ({language}) : {audio_path}...")

    lang_key = _language_key(language)
    lang_adj_fem = _LANGUAGE_ADJ_FEM[lang_key]
    lang_adj_masc = _LANGUAGE_ADJ_MASC[lang_key]

    if getattr(settings, "OPENAI_API_KEY", ""):
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            transcription_kwargs = {
                "model": getattr(settings, "OPENAI_TRANSCRIBE_MODEL", "whisper-1"),
                "prompt": f"Transcription en langue {lang_adj_fem}. Ne traduis pas.",
            }
            if lang_key in {"fr", "en"}:
                transcription_kwargs["language"] = lang_key
            with open(audio_path, "rb") as audio_file:
                response = openai_client.audio.transcriptions.create(
                    file=audio_file,
                    **transcription_kwargs,
                )
            transcript = (response.text or "").strip()
            if transcript:
                logger.info(f"[eval_service] Transcription OpenAI réussie : {transcript[:100]}...")
                return transcript
        except Exception as openai_error:
            logger.warning(f"[eval_service] OpenAI transcription indisponible, tentative Gemini: {openai_error}")

    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI: {err}")

    # Récupérer l'extension du fichier pour le mime type
    _, ext = os.path.splitext(audio_path)
    ext = ext.lower()

    if ext == ".ogg":
        mime_type = "audio/ogg"
    elif ext == ".mp3":
        mime_type = "audio/mp3"
    elif ext in (".m4a", ".mp4"):
        mime_type = "audio/mp4"
    elif ext in (".wav", ".webm"):
        mime_type = "audio/webm"
    else:
        mime_type = "audio/webm" # défaut

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    system_prompt = (
        f"Tu es un transcripteur professionnel spécialisé dans la langue {lang_adj_fem}. "
        f"Écoute attentivement l'audio fourni et transcris-le fidèlement en texte {lang_adj_masc}. "
        "Ne traduis pas. N'ajoute aucune introduction, commentaire ou explication. "
        "Retourne uniquement la transcription brute."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                f"Transcris cet audio {lang_adj_masc}."
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0, # Pour une transcription déterministe
            )
        )
        transcript = response.text.strip()
        logger.info(f"[eval_service] Transcription réussie : {transcript[:100]}...")
        return transcript
    except Exception as e:
        logger.error(f"[eval_service] Échec de la transcription : {e}")
        raise

def evaluate_eo(transcript: str, topic: str, instructions: str, level: str, expected_points: list, language: str = "de") -> dict:
    """
    Évalue la transcription d'une expression orale.
    Retourne un dictionnaire structuré contenant le score, le feedback et les suggestions.
    """
    logger.info(f"[eval_service] Évaluation Expression Orale ({language} · Niveau {level})...")

    lang_key = _language_key(language)
    lang_phrase = _LANGUAGE_PHRASES[lang_key]
    cert_bodies = _LANGUAGE_CERT_BODIES[lang_key]

    system_prompt = (
        f"Tu es un examinateur expert et un enseignant senior {lang_phrase} chevronné ({cert_bodies}). "
        f"Tu évalues la prestation orale d'un candidat francophone préparant l'examen de niveau {level}. "
        "Ton ton doit être extrêmement professionnel, bienveillant, constructif et hautement pédagogique.\n\n"
        "Évalue rigoureusement les critères suivants : Clarté/Prononciation, Grammaire, Vocabulaire, et Cohérence/Pertinence.\n\n"
        "Tu dois obligatoirement renvoyer un objet JSON valide contenant :\n"
        "- 'score' (nombre entier de 0 à 100)\n"
        "- 'feedback' (une évaluation globale détaillée en français, structurée avec des retours bienveillants mais exigeants sur la syntaxe, la fluidité et le respect de la consigne, en expliquant ce qui est bon et ce qui doit être corrigé)\n"
        "- 'points_covered' (tableau de chaînes de caractères listant les points de la consigne ou compétences clés que l'étudiant a validés avec succès)\n"
        "- 'suggestions' (tableau de conseils d'amélioration très concrets, rédigés en français, par exemple des astuces de prononciation, de grammaire ou de structure de phrases pour le niveau ciblé)\n"
        "- 'criteria' (dictionnaire contenant les notes sur 100 pour : 'pronunciation', 'grammar', 'vocabulary', 'coherence')\n\n"
        "Ne renvoie rien d'autre que l'objet JSON brut."
    )

    user_prompt = (
        f"Sujet de l'épreuve : {topic}\n"
        f"Instructions : {instructions}\n"
        f"Transcription de l'enregistrement de l'élève : \"{transcript}\"\n"
    )

    try:
        return call_openai_json(system_prompt, user_prompt, temperature=0.2)
    except Exception as openai_error:
        logger.warning(f"[eval_service] OpenAI EO indisponible, tentative Gemini: {openai_error}")

    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI: {err}")

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2,
        )
    )
    return json.loads(response.text)

def evaluate_ee(text: str, topic: str, instructions: str, level: str, language: str = "de") -> dict:
    """
    Évalue une expression écrite.
    Retourne un dictionnaire structuré contenant le score, le feedback en français,
    la liste des erreurs identifiées avec corrections, et la version entièrement corrigée.
    """
    logger.info(f"[eval_service] Évaluation Expression Écrite ({language} · Niveau {level})...")

    lang_key = _language_key(language)
    lang_phrase = _LANGUAGE_PHRASES[lang_key]
    cert_bodies = _LANGUAGE_CERT_BODIES[lang_key]

    system_prompt = (
        f"Tu es un examinateur expert et un professeur senior {lang_phrase} ({cert_bodies}). "
        f"Tu évalues l'expression écrite d'un candidat francophone préparant un examen de niveau {level}. "
        "Ton analyse doit être digne d'un véritable enseignant : rigoureuse, bienveillante, de qualité premium, pédagogique et structurée.\n\n"
        "Tu devez obligatoirement renvoyer un objet JSON valide contenant :\n"
        "- 'score' (nombre entier de 0 à 100. Sois juste et exigeant selon les critères officiels du Cadre européen commun de référence pour les langues - CECRL)\n"
        "- 'feedback' (une évaluation globale détaillée et rédigée en français, expliquant les points forts du texte et les axes majeurs de progression)\n"
        "- 'corrected_version' (le texte complet de l'étudiant, entièrement corrigé des fautes de grammaire, d'orthographe, de déclinaisons, de choix des mots, et reformulé de manière fluide et naturelle pour le niveau visé)\n"
        "- 'errors' (un tableau d'objets décrivant chaque erreur trouvée. Chaque objet doit avoir la structure exacte : "
        "{'original': 'le fragment erroné exact', 'correction': 'le fragment corrigé', 'rule': 'explication claire et pédagogique de la règle de grammaire/orthographe/vocabulaire violée, rédigée en français'})\n"
        "- 'criteria' (dictionnaire contenant les notes sur 100 pour : 'grammar', 'spelling', 'vocabulary', 'coherence')\n\n"
        "Ne renvoie rien d'autre que l'objet JSON brut."
    )

    user_prompt = (
        f"Sujet de l'épreuve : {topic}\n"
        f"Instructions : {instructions}\n"
        f"Texte rédigé par l'élève : \"{text}\"\n"
    )

    try:
        return call_openai_json(system_prompt, user_prompt, temperature=0.2)
    except Exception as openai_error:
        logger.warning(f"[eval_service] OpenAI EE indisponible, tentative Gemini: {openai_error}")

    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI: {err}")

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2,
        )
    )
    return json.loads(response.text)
