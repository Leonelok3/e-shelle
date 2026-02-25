from __future__ import annotations

import inspect
import json
import time
import traceback
from typing import Any, Dict, Optional

from django.core.management.base import BaseCommand, CommandError

# Imports projet (existants dans ton code)
from ai_engine.agents.co_agent import generate_co_content
from ai_engine.services.insertion_service import insert_co_content
from ai_engine.services.tts_service import generate_audio


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"raw": value}
        except Exception:
            return {"raw": value}
    return {"raw": value}


def _extract_audio_script(co_data: Dict[str, Any]) -> str:
    candidates = [
        "audio_script",
        "script",
        "audio_text",
        "text",
        "prompt_text",
    ]
    for key in candidates:
        v = co_data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # fallback: si content_html existe, on évite un parse HTML lourd ici
    v = co_data.get("content_html")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return ""


def _call_generate(level: str, language: str, topic: Optional[str]) -> Any:
    """
    Appel robuste de generate_co_content malgré variations de signature.
    """
    sig = inspect.signature(generate_co_content)
    kwargs: Dict[str, Any] = {}

    if "level" in sig.parameters:
        kwargs["level"] = level
    if "language" in sig.parameters:
        kwargs["language"] = language
    if topic and "topic" in sig.parameters:
        kwargs["topic"] = topic
    if "locale" in sig.parameters and "language" not in kwargs:
        kwargs["locale"] = language
    if "lang" in sig.parameters and "language" not in kwargs:
        kwargs["lang"] = language

    # Essai 1: kwargs intelligents
    try:
        return generate_co_content(**kwargs)
    except TypeError:
        pass

    # Essai 2: positions minimales
    try:
        return generate_co_content(level, language)
    except TypeError:
        return generate_co_content(level=level)


def _call_tts(text: str, language: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Appel robuste de generate_audio malgré variations de signature/retour.
    Retourne un chemin audio (str) si possible.
    """
    if not text.strip():
        return None

    sig = inspect.signature(generate_audio)
    kwargs: Dict[str, Any] = {}

    if "text" in sig.parameters:
        kwargs["text"] = text
    if "script" in sig.parameters and "text" not in kwargs:
        kwargs["script"] = text

    if "language" in sig.parameters:
        kwargs["language"] = language
    elif "lang" in sig.parameters:
        kwargs["lang"] = language
    elif "locale" in sig.parameters:
        kwargs["locale"] = language

    if output_dir:
        if "output_dir" in sig.parameters:
            kwargs["output_dir"] = output_dir
        elif "out_dir" in sig.parameters:
            kwargs["out_dir"] = output_dir

    # Appel
    result = generate_audio(**kwargs) if kwargs else generate_audio(text)

    # Normalisation du retour
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for k in ("audio_path", "path", "file_path", "file", "url"):
            v = result.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _call_insert(
    exam_id: int,
    level: str,
    language: str,
    co_data: Dict[str, Any],
    audio_path: Optional[str],
) -> Any:
    """
    Appel robuste de insert_co_content malgré variations de signature.
    """
    sig = inspect.signature(insert_co_content)
    params = sig.parameters

    kwargs: Dict[str, Any] = {}
    if "exam_id" in params:
        kwargs["exam_id"] = exam_id
    if "level" in params:
        kwargs["level"] = level
    if "language" in params:
        kwargs["language"] = language
    elif "lang" in params:
        kwargs["lang"] = language
    if "co_data" in params:
        kwargs["co_data"] = co_data
    elif "data" in params:
        kwargs["data"] = co_data
    if "audio_path" in params:
        kwargs["audio_path"] = audio_path
    elif "audio" in params:
        kwargs["audio"] = audio_path

    # Essai kwargs
    try:
        return insert_co_content(**kwargs)
    except TypeError:
        # fallback signature connue: (exam_id, level, language, co_data, audio_path)
        return insert_co_content(exam_id, level, language, co_data, audio_path)


class Command(BaseCommand):
    help = "Génère du contenu CO, génère l'audio (optionnel), puis insère en base (safe + retries)."

    def add_arguments(self, parser):
        parser.add_argument("--exam_id", type=int, required=True, help="ID de l'examen cible")
        parser.add_argument("--level", type=str, default="A1", help="Niveau CECR (A1..C2)")
        parser.add_argument("--language", type=str, default="fr", help="Langue/locale (ex: fr)")
        parser.add_argument("--lessons", type=int, default=1, help="Nombre de leçons à générer")
        parser.add_argument("--topic", type=str, default="", help="Topic optionnel")
        parser.add_argument("--no-audio", action="store_true", help="Désactive la génération audio")
        parser.add_argument("--dry-run", action="store_true", help="Ne rien écrire en base")
        parser.add_argument("--continue-on-error", action="store_true", help="Continue même si une leçon échoue")
        parser.add_argument("--retries", type=int, default=2, help="Nombre de retries par leçon")
        parser.add_argument("--retry-delay", type=float, default=1.5, help="Délai entre retries (sec)")
        parser.add_argument("--sleep", type=float, default=0.0, help="Pause entre leçons (sec)")
        parser.add_argument("--output-dir", type=str, default="", help="Dossier de sortie audio (optionnel)")

    def handle(self, *args, **options):
        exam_id: int = options["exam_id"]
        level: str = options["level"].strip().upper()
        language: str = options["language"].strip().lower()
        lessons: int = max(1, int(options["lessons"]))
        topic: str = (options.get("topic") or "").strip()
        no_audio: bool = bool(options["no_audio"])
        dry_run: bool = bool(options["dry_run"])
        continue_on_error: bool = bool(options["continue_on_error"])
        retries: int = max(0, int(options["retries"]))
        retry_delay: float = max(0.0, float(options.get("retry_delay", options.get("retry-delay", 1.5))))
        sleep_between: float = max(0.0, float(options["sleep"]))
        output_dir: str = (options.get("output_dir") or "").strip()

        if exam_id <= 0:
            raise CommandError("--exam_id doit être > 0")

        created = 0
        failed = 0

        self.stdout.write(
            self.style.NOTICE(
                f"[CO] start exam_id={exam_id} level={level} language={language} lessons={lessons} "
                f"dry_run={dry_run} no_audio={no_audio}"
            )
        )

        for i in range(1, lessons + 1):
            attempt = 0
            ok = False

            while attempt <= retries and not ok:
                attempt += 1
                try:
                    # 1) Génération
                    raw = _call_generate(level=level, language=language, topic=topic or None)
                    co_data = _as_dict(raw)

                    # 2) Audio
                    audio_path: Optional[str] = None
                    if not no_audio:
                        script = _extract_audio_script(co_data)
                        if script:
                            audio_path = _call_tts(script, language=language, output_dir=output_dir or None)

                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[CO][DRY] lesson#{i} generated. "
                                f"keys={list(co_data.keys())[:8]} audio={'yes' if audio_path else 'no'}"
                            )
                        )
                        created += 1
                        ok = True
                        continue

                    # 3) Insertion DB
                    lesson_obj = _call_insert(
                        exam_id=exam_id,
                        level=level,
                        language=language,
                        co_data=co_data,
                        audio_path=audio_path,
                    )

                    lesson_id = getattr(lesson_obj, "id", None)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[CO] lesson#{i} created lesson_id={lesson_id} audio={'yes' if audio_path else 'no'}"
                        )
                    )
                    created += 1
                    ok = True

                except Exception as exc:
                    failed += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"[CO] lesson#{i} attempt={attempt}/{retries + 1} failed: {exc}"
                        )
                    )
                    self.stderr.write(traceback.format_exc())

                    if attempt <= retries:
                        time.sleep(retry_delay)
                    else:
                        if not continue_on_error:
                            raise CommandError(
                                f"Arrêt après échec lesson#{i}. "
                                f"Utilise --continue-on-error pour poursuivre."
                            )

            if sleep_between > 0 and i < lessons:
                time.sleep(sleep_between)

        self.stdout.write(
            self.style.SUCCESS(f"[CO] done created={created} failed={failed}")
        )