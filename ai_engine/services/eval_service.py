import os
import re
import json
import logging
from django.conf import settings
from google.genai import types
from e_shelle_ai.services.tools.google_media_generator import get_vertex_client, get_genai_studio_client
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


def _parse_json_safely(text: str) -> dict:
    """
    Extrait et décode un dictionnaire JSON depuis une réponse brute LLM,
    même si elle est entourée de blocs de code markdown (```json ... ```)
    ou de commentaires supplémentaires.
    """
    if not text:
        raise ValueError("Réponse IA vide")
    cleaned = text.strip()
    # Retirer les délimiteurs markdown éventuels
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _call_gemini_eval_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """
    Appelle l'API Google Gemini via Google AI Studio (clé gratuite).
    Tente les modèles rapides disponibles (gemini-flash-latest, gemini-3.6-flash).
    """
    candidate_models = ["gemini-flash-latest", "gemini-3.6-flash"]

    studio_client, _ = get_genai_studio_client()
    if not studio_client:
        # Tenter Vertex AI uniquement si AI Studio n'a pas pu s'initialiser
        studio_client, _ = get_vertex_client()

    if not studio_client:
        raise RuntimeError("Client Google Gemini non disponible")

    last_error = None
    for model in candidate_models:
        try:
            response = studio_client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            if response and response.text:
                parsed = _parse_json_safely(response.text)
                logger.info(f"[eval_service] Gemini succès ({model})")
                return parsed
        except Exception as e:
            last_error = e
            logger.warning(f"[eval_service] Gemini ({model}) indisponible : {e}")
            continue

    raise RuntimeError(f"Tous les modèles Gemini ont échoué : {last_error}")


def _call_anthropic_eval_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    """
    Appel optionnel à Claude / Anthropic en cas de secours.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY non configurée")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2500,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text
    return _parse_json_safely(text)


def _evaluate_ee_heuristic_fallback(text: str, topic: str, instructions: str, level: str, language: str = "fr") -> dict:
    """
    Évaluateur linguistique déterministe de secours en cas d'indisponibilité
    temporaire des services IA distants (OpenAI, Gemini, Claude).
    Analyse la longueur, la ponctuation, le vocabulaire et les fautes récurrentes
    pour toujours fournir une correction utile et pédagogique.
    """
    words = text.strip().split()
    word_count = len(words)
    errors = []

    corrections_connues = [
        (r"\bsuir\b", "suis", "Faute d'orthographe sur le verbe être (je suis)"),
        (r"\binteresse\b", "intéressé(e)", "Manque d'accents sur le participe passé"),
        (r"\binteressant\b", "intéressant", "Manque d'accents"),
        (r"\btres\b", "très", "Accent grave manquant sur le mot 'très'"),
        (r"\bca\b", "ça", "C cédille manquant pour le pronom démonstratif"),
        (r"\bdeja\b", "déjà", "Accents manquants sur 'déjà'"),
        (r"\bmeme\b", "même", "Accent circonflexe manquant sur 'même'"),
        (r"\bbcp\b", "beaucoup", "Abbréviation proscrite dans un examen officiel"),
        (r"\bsvp\b", "s'il vous plaît", "Formule de politesse à écrire en toutes lettres"),
    ]

    corrected = text
    for pattern, corr, rule in corrections_connues:
        if re.search(pattern, corrected, flags=re.IGNORECASE):
            orig_match = re.search(pattern, corrected, flags=re.IGNORECASE)
            orig_str = orig_match.group(0) if orig_match else pattern
            errors.append({
                "original": orig_str,
                "correction": corr,
                "rule": rule,
            })
            corrected = re.sub(pattern, corr, corrected, flags=re.IGNORECASE)

    # Première lettre en majuscule si oubliée
    if corrected and not corrected[0].isupper():
        errors.append({
            "original": corrected[0],
            "correction": corrected[0].upper(),
            "rule": "Une phrase doit toujours commencer par une majuscule",
        })
        corrected = corrected[0].upper() + corrected[1:]

    # Ponctuation finale
    if corrected and corrected[-1] not in ".!?":
        errors.append({
            "original": "(fin de phrase)",
            "correction": ".",
            "rule": "Il convient de terminer vos phrases par un signe de ponctuation",
        })
        corrected += "."

    # Calcul du score basé sur les critères CECR
    # Longueur attendue typique : ~100 à 250 mots
    if word_count < 20:
        base_score = 40
        feedback_len = "Votre texte est beaucoup trop court pour permettre une évaluation complète selon les critères officiels. Développez davantage vos arguments."
    elif word_count < 60:
        base_score = 55
        feedback_len = "Texte compréhensible mais concis. Enrichissez vos paragraphes avec des exemples concrets et des connecteurs logiques."
    elif word_count < 150:
        base_score = 70
        feedback_len = "Bon développement général. Veillez à structurer clairement votre argumentation (introduction, arguments, conclusion)."
    else:
        base_score = 80
        feedback_len = "Très bon volume de rédaction. Le sujet est traité en profondeur."

    penalty = min(len(errors) * 5, 25)
    final_score = max(20, min(100, base_score - penalty))

    return {
        "score": final_score,
        "feedback": f"{feedback_len} Une relecture attentive de la grammaire et de l'orthographe est conseillée.",
        "corrected_version": corrected,
        "errors": errors,
        "criteria": {
            "grammar": max(30, min(100, final_score - 5)),
            "spelling": max(30, min(100, final_score - penalty)),
            "vocabulary": max(40, min(100, final_score + 5)),
            "coherence": max(40, min(100, final_score)),
        },
        "word_count": word_count,
    }


def _evaluate_eo_heuristic_fallback(transcript: str, topic: str, instructions: str, level: str, expected_points: list, language: str = "fr") -> dict:
    """
    Évaluateur oral déterministe de secours.
    """
    words = transcript.strip().split()
    word_count = len(words)

    if word_count < 15:
        score = 45
        feedback = "L'enregistrement est court. Essayez d'exprimer vos idées avec des phrases complètes et de développer votre point de vue."
    elif word_count < 40:
        score = 65
        feedback = "Prestation encourageante. Vous répondez au sujet, mais veillez à soigner la prononciation et la variété du vocabulaire."
    else:
        score = 75
        feedback = "Bonne aisance à l'oral. Le débit est régulier et les éléments demandés sont abordés de façon claire."

    return {
        "score": score,
        "feedback": feedback,
        "points_covered": expected_points[:2] if expected_points else ["Participation orale enregistrée"],
        "suggestions": [
            "Pensez à utiliser des connecteurs logiques (d'abord, en outre, enfin)",
            "Soignez la clarté de l'articulation et les liaisons",
            "Structurez vos réponses avec une introduction et une conclusion claires",
        ],
        "criteria": {
            "pronunciation": score,
            "grammar": max(40, score - 5),
            "vocabulary": max(40, score),
            "coherence": max(40, score + 5),
        },
    }


def _normalize_ee_dict(result: dict, text: str) -> dict:
    """
    S'assure que le résultat EE contient tous les champs requis par le template et le JS.
    """
    if not isinstance(result, dict):
        result = {}

    score = result.get("score")
    try:
        score = float(score) if score is not None else 50.0
    except (ValueError, TypeError):
        score = 50.0
    score = max(0.0, min(100.0, score))

    feedback = str(result.get("feedback") or "").strip()
    corrected = str(result.get("corrected_version") or "").strip() or text

    raw_errors = result.get("errors") or []
    norm_errors = []
    if isinstance(raw_errors, list):
        for err in raw_errors:
            if isinstance(err, dict):
                orig = err.get("original") or err.get("word") or ""
                corr = err.get("correction") or ""
                rule = err.get("rule") or err.get("explanation") or err.get("type") or ""
                norm_errors.append({
                    "original": orig,
                    "correction": corr,
                    "rule": rule,
                })
            elif isinstance(err, str):
                norm_errors.append({
                    "original": "",
                    "correction": err,
                    "rule": "",
                })

    criteria = result.get("criteria")
    if not isinstance(criteria, dict):
        criteria = {
            "grammar": score,
            "spelling": score,
            "vocabulary": score,
            "coherence": score,
        }

    word_count = len(text.strip().split())

    return {
        "score": score,
        "feedback": feedback,
        "corrected_version": corrected,
        "errors": norm_errors,
        "criteria": criteria,
        "word_count": word_count,
    }


def _normalize_eo_dict(result: dict, transcript: str) -> dict:
    """
    S'assure que le résultat EO contient tous les champs requis.
    """
    if not isinstance(result, dict):
        result = {}

    score = result.get("score")
    try:
        score = float(score) if score is not None else 50.0
    except (ValueError, TypeError):
        score = 50.0
    score = max(0.0, min(100.0, score))

    feedback = str(result.get("feedback") or "").strip()
    points_covered = result.get("points_covered")
    if not isinstance(points_covered, list):
        points_covered = [str(points_covered)] if points_covered else []

    suggestions = result.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = [str(suggestions)] if suggestions else []

    criteria = result.get("criteria")
    if not isinstance(criteria, dict):
        criteria = {
            "pronunciation": score,
            "grammar": score,
            "vocabulary": score,
            "coherence": score,
        }

    return {
        "score": score,
        "transcript": transcript,
        "feedback": feedback,
        "points_covered": points_covered,
        "suggestions": suggestions,
        "criteria": criteria,
    }


def transcribe_audio(audio_path: str, language: str = "de") -> str:
    """
    Transcrit un fichier audio. OpenAI est utilisé en priorité, Gemini en secours.
    """
    logger.info(f"[eval_service] Transcription audio ({language}) : {audio_path}...")

    lang_key = _language_key(language)
    lang_adj_fem = _LANGUAGE_ADJ_FEM[lang_key]
    lang_adj_masc = _LANGUAGE_ADJ_MASC[lang_key]

    # 1. Tentative OpenAI Whisper si clé disponible
    if getattr(settings, "OPENAI_API_KEY", ""):
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30.0, max_retries=0)
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
            logger.warning(f"[eval_service] OpenAI transcription indisponible : {openai_error}")

    # 2. Secours Google Gemini (Audio multimodale)
    _, ext = os.path.splitext(audio_path)
    ext = ext.lower()
    if ext == ".ogg":
        mime_type = "audio/ogg"
    elif ext == ".mp3":
        mime_type = "audio/mp3"
    elif ext in (".m4a", ".mp4"):
        mime_type = "audio/mp4"
    elif ext == ".wav":
        mime_type = "audio/wav"
    elif ext == ".webm":
        mime_type = "audio/webm"
    else:
        mime_type = "audio/webm"

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    system_prompt = (
        f"Tu es un transcripteur professionnel spécialisé dans la langue {lang_adj_fem}. "
        f"Écoute attentivement l'audio fourni et transcris-le fidèlement en texte {lang_adj_masc}. "
        "Ne traduis pas. N'ajoute aucune introduction, commentaire ou explication. "
        "Retourne uniquement la transcription brute."
    )

    candidate_models = ["gemini-flash-latest", "gemini-3.6-flash"]
    clients = []
    studio_client, _ = get_genai_studio_client()
    if studio_client:
        clients.append(("AI Studio", studio_client))
    vertex_client, _ = get_vertex_client()
    if vertex_client:
        clients.append(("Vertex AI", vertex_client))

    for client_name, client in clients:
        for model in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                        f"Transcris cet audio {lang_adj_masc}."
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.0,
                    )
                )
                if response and response.text:
                    transcript = response.text.strip()
                    logger.info(f"[eval_service] Transcription Gemini ({client_name}/{model}) réussie : {transcript[:100]}...")
                    return transcript
            except Exception as e:
                logger.warning(f"[eval_service] Échec transcription Gemini {client_name}/{model} : {e}")

    logger.error("[eval_service] Impossible de transcrire l'audio avec les fournisseurs configurés.")
    return ""


def evaluate_eo(transcript: str, topic: str, instructions: str, level: str, expected_points: list, language: str = "de", *, require_ai: bool = False) -> dict:
    """
    Évalue la transcription d'une expression orale avec chaîne de repli robuste.
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

    # 1. Tentative OpenAI
    if getattr(settings, "OPENAI_API_KEY", ""):
        try:
            raw = call_openai_json(system_prompt, user_prompt, temperature=0.2)
            return _normalize_eo_dict(raw, transcript)
        except Exception as openai_error:
            logger.warning(f"[eval_service] OpenAI EO indisponible, repli Gemini : {openai_error}")

    # 2. Tentative Google Gemini (AI Studio + Vertex multi-modèles)
    try:
        raw = _call_gemini_eval_json(system_prompt, user_prompt, temperature=0.2)
        return _normalize_eo_dict(raw, transcript)
    except Exception as gemini_error:
        logger.warning(f"[eval_service] Gemini EO indisponible, repli Claude/Heuristique : {gemini_error}")

    # 3. Tentative Claude / Anthropic
    try:
        raw = _call_anthropic_eval_json(system_prompt, user_prompt, temperature=0.2)
        return _normalize_eo_dict(raw, transcript)
    except Exception as claude_error:
        logger.warning(f"[eval_service] Claude EO indisponible : {claude_error}")

    if require_ai:
        raise RuntimeError("La correction IA est temporairement indisponible.")

    # 4. Repli linguistique déterministe
    logger.info("[eval_service] Utilisation du repli déterministe pour Expression Orale")
    raw = _evaluate_eo_heuristic_fallback(transcript, topic, instructions, level, expected_points, language)
    return _normalize_eo_dict(raw, transcript)


def evaluate_ee(text: str, topic: str, instructions: str, level: str, language: str = "de", *, require_ai: bool = False) -> dict:
    """
    Évalue une expression écrite avec chaîne de secours robuste (OpenAI -> Gemini -> Claude -> Heuristique).
    Garantit un retour JSON valide et normalisé dans tous les cas.
    """
    logger.info(f"[eval_service] Évaluation Expression Écrite ({language} · Niveau {level})...")

    lang_key = _language_key(language)
    lang_phrase = _LANGUAGE_PHRASES[lang_key]
    cert_bodies = _LANGUAGE_CERT_BODIES[lang_key]

    system_prompt = (
        f"Tu es un examinateur expert et un professeur senior {lang_phrase} ({cert_bodies}). "
        f"Tu évalues l'expression écrite d'un candidat francophone préparant un examen de niveau {level}. "
        "Ton analyse doit être digne d'un véritable enseignant : rigoureuse, bienveillante, de qualité premium, pédagogique et structurée.\n\n"
        "Tu dois obligatoirement renvoyer un objet JSON valide contenant :\n"
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

    # 1. Tentative OpenAI
    if getattr(settings, "OPENAI_API_KEY", ""):
        try:
            raw = call_openai_json(system_prompt, user_prompt, temperature=0.2)
            return _normalize_ee_dict(raw, text)
        except Exception as openai_error:
            logger.warning(f"[eval_service] OpenAI EE indisponible, tentative Gemini : {openai_error}")

    # 2. Tentative Google Gemini (AI Studio Developer API + Vertex, multi-modèles)
    try:
        raw = _call_gemini_eval_json(system_prompt, user_prompt, temperature=0.2)
        return _normalize_ee_dict(raw, text)
    except Exception as gemini_error:
        logger.warning(f"[eval_service] Gemini EE indisponible, repli Claude/Heuristique : {gemini_error}")

    # 3. Tentative Claude / Anthropic
    try:
        raw = _call_anthropic_eval_json(system_prompt, user_prompt, temperature=0.2)
        return _normalize_ee_dict(raw, text)
    except Exception as claude_error:
        logger.warning(f"[eval_service] Claude EE indisponible : {claude_error}")

    if require_ai:
        raise RuntimeError("La correction IA est temporairement indisponible.")

    # 4. Repli linguistique déterministe (toujours opérationnel)
    logger.info("[eval_service] Utilisation du repli linguistique déterministe pour Expression Écrite")
    raw = _evaluate_ee_heuristic_fallback(text, topic, instructions, level, language)
    return _normalize_ee_dict(raw, text)
