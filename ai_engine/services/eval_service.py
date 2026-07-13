import os
import json
import logging
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str, language: str = "de") -> str:
    """
    Transcrit un fichier audio en texte à l'aide de Gemini (via Vertex AI).
    """
    logger.info(f"[eval_service] Transcription audio : {audio_path}...")
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
        "Tu es un transcripteur professionnel spécialisé dans la langue allemande. "
        "Écoute attentivement l'audio fourni et transcris-le fidèlement en texte allemand. "
        "Ne traduis pas. N'ajoute aucune introduction, commentaire ou explication. "
        "Retourne uniquement la transcription brute."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                "Transcris cet audio allemand."
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

def evaluate_eo(transcript: str, topic: str, instructions: str, level: str, expected_points: list) -> dict:
    """
    Évalue la transcription d'une expression orale en allemand.
    Retourne un dictionnaire structuré contenant le score, le feedback et les suggestions.
    """
    logger.info(f"[eval_service] Évaluation Expression Orale (Niveau {level})...")
    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI: {err}")

    system_prompt = (
        "Tu es un examinateur expert et un enseignant senior d'allemand chevronné (Goethe-Institut, telc, TestDaF). "
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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"[eval_service] Échec de l'évaluation EO : {e}")
        raise

def evaluate_ee(text: str, topic: str, instructions: str, level: str) -> dict:
    """
    Évalue une expression écrite en allemand.
    Retourne un dictionnaire structuré contenant le score, le feedback en français,
    la liste des erreurs identifiées avec corrections, et la version entièrement corrigée.
    """
    logger.info(f"[eval_service] Évaluation Expression Écrite (Niveau {level})...")
    client, err = get_vertex_client()
    if err or not client:
        raise RuntimeError(f"Impossible d'initialiser le client Vertex AI: {err}")

    system_prompt = (
        "Tu es un examinateur expert et un professeur senior d'allemand (Goethe-Institut, telc, TestDaF). "
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
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"[eval_service] Échec de l'évaluation EE : {e}")
        raise
