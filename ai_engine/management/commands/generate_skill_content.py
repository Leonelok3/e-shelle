from __future__ import annotations

import time
import traceback
from typing import Any, Dict, Optional

from django.core.management.base import BaseCommand, CommandError

SKILL_CHOICES = ("co", "ce", "ee", "eo")


def _get_agent(skill: str):
    if skill == "co":
        from ai_engine.agents.co_agent import generate_co_content
        return generate_co_content
    if skill == "ce":
        from ai_engine.agents.ce_agent import generate_ce_content
        return generate_ce_content
    if skill == "ee":
        from ai_engine.agents.ee_agent import generate_ee_content
        return generate_ee_content
    if skill == "eo":
        from ai_engine.agents.eo_agent import generate_eo_content
        return generate_eo_content
    raise ValueError(f"Unknown skill: {skill}")


def _get_inserter(skill: str):
    if skill == "co":
        from ai_engine.services.insertion_service import insert_co_content
        return insert_co_content
    if skill == "ce":
        from ai_engine.services.insertion_service import insert_ce_content
        return insert_ce_content
    if skill == "ee":
        from ai_engine.services.insertion_service import insert_ee_content
        return insert_ee_content
    if skill == "eo":
        from ai_engine.services.insertion_service import insert_eo_content
        return insert_eo_content
    raise ValueError(f"Unknown skill: {skill}")


def _call_agent(agent_fn, level: str, language: str, topic: Optional[str]) -> Dict[str, Any]:
    """Appel robuste de l'agent — gère les différentes signatures (level/language, language/level)."""
    import inspect
    sig = inspect.signature(agent_fn)
    params = sig.parameters

    # CO : generate_co_content(level, language, topic=None)
    # CE/EE/EO : generate_xx_content(language, level)
    if "level" in params and "language" in params:
        kwargs = {"level": level, "language": language}
        if topic and "topic" in params:
            kwargs["topic"] = topic
        return agent_fn(**kwargs)
    if "level" in params:
        return agent_fn(level=level)
    return agent_fn(language, level)


def _extract_audio_script(skill: str, data: Dict[str, Any]) -> str:
    """Extrait le texte à synthétiser selon le skill."""
    if skill == "co":
        for key in ("audio_script", "script", "audio_text", "text", "content_html"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    if skill == "eo":
        for key in ("instructions", "topic"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _generate_audio(text: str, language: str, output_dir: Optional[str]) -> Optional[str]:
    if not text.strip():
        return None
    try:
        from ai_engine.services.tts_service import generate_audio
        kwargs = {"text": text, "language": language}
        if output_dir:
            kwargs["output_dir"] = output_dir
        result = generate_audio(**kwargs)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for k in ("audio_path", "path", "file_path", "file", "url"):
                v = result.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
    except Exception as e:
        return None
    return None


class Command(BaseCommand):
    help = (
        "Génère du contenu pédagogique pour une compétence donnée (CO/CE/EE/EO), "
        "génère l'audio si applicable, puis insère en base."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skill",
            type=str,
            required=True,
            choices=SKILL_CHOICES,
            help="Compétence cible : co, ce, ee, eo",
        )
        parser.add_argument("--exam_id", type=int, required=True, help="ID de l'examen (Exam.id)")
        parser.add_argument("--level", type=str, default="A1", help="Niveau CECR : A1 A2 B1 B2 C1 C2")
        parser.add_argument("--language", type=str, default="fr", help="Langue : fr, en, de")
        parser.add_argument("--lessons", type=int, default=1, help="Nombre de leçons à générer")
        parser.add_argument("--topic", type=str, default="", help="Thème optionnel (CO uniquement)")
        parser.add_argument("--no-audio", action="store_true", help="Désactiver la génération TTS")
        parser.add_argument("--dry-run", action="store_true", help="Simuler sans écrire en base")
        parser.add_argument("--continue-on-error", action="store_true", help="Continuer malgré les erreurs")
        parser.add_argument("--retries", type=int, default=2, help="Tentatives par leçon")
        parser.add_argument("--retry-delay", type=float, default=2.0, help="Délai entre tentatives (sec)")
        parser.add_argument("--sleep", type=float, default=1.0, help="Pause entre leçons (sec)")
        parser.add_argument("--output-dir", type=str, default="", help="Dossier de sortie audio")

    def handle(self, *args, **options):
        skill: str = options["skill"].lower()
        exam_id: int = options["exam_id"]
        level: str = options["level"].strip().upper()
        language: str = options["language"].strip().lower()
        lessons: int = max(1, int(options["lessons"]))
        topic: str = (options.get("topic") or "").strip()
        no_audio: bool = bool(options["no_audio"])
        dry_run: bool = bool(options["dry_run"])
        continue_on_error: bool = bool(options["continue_on_error"])
        retries: int = max(0, int(options["retries"]))
        retry_delay: float = max(0.0, float(options.get("retry_delay", 2.0)))
        sleep_between: float = max(0.0, float(options["sleep"]))
        output_dir: str = (options.get("output_dir") or "").strip()

        # Skills sans audio (CE, EE)
        audio_skills = {"co", "eo"}
        use_audio = (not no_audio) and (skill in audio_skills)

        agent_fn = _get_agent(skill)
        inserter_fn = _get_inserter(skill)

        self.stdout.write(self.style.NOTICE(
            f"[{skill.upper()}] exam_id={exam_id} level={level} language={language} "
            f"lessons={lessons} dry_run={dry_run} audio={use_audio}"
        ))

        created = 0
        failed = 0

        for i in range(1, lessons + 1):
            attempt = 0
            ok = False

            while attempt <= retries and not ok:
                attempt += 1
                try:
                    # 1) Génération LLM
                    data = _call_agent(agent_fn, level=level, language=language, topic=topic or None)

                    # 2) Audio (CO et EO uniquement)
                    audio_path: Optional[str] = None
                    if use_audio:
                        script = _extract_audio_script(skill, data)
                        if script:
                            audio_path = _generate_audio(script, language, output_dir or None)

                    if dry_run:
                        self.stdout.write(self.style.WARNING(
                            f"[{skill.upper()}][DRY] lesson#{i} keys={list(data.keys())[:6]} "
                            f"audio={'yes' if audio_path else 'no'}"
                        ))
                        created += 1
                        ok = True
                        continue

                    # 3) Insertion DB
                    lesson_obj = inserter_fn(
                        exam_id=exam_id,
                        level=level,
                        language=language,
                        **{f"{skill}_data": data},
                        audio_path=audio_path,
                    )

                    lesson_id = getattr(lesson_obj, "id", "?")
                    self.stdout.write(self.style.SUCCESS(
                        f"[{skill.upper()}] lesson#{i}/{lessons} id={lesson_id} "
                        f"level={level} audio={'yes' if audio_path else 'no'}"
                    ))
                    created += 1
                    ok = True

                except Exception as exc:
                    failed += 1
                    self.stderr.write(self.style.ERROR(
                        f"[{skill.upper()}] lesson#{i} attempt={attempt}/{retries + 1} failed: {exc}"
                    ))
                    self.stderr.write(traceback.format_exc())

                    if attempt <= retries:
                        time.sleep(retry_delay)
                    elif not continue_on_error:
                        raise CommandError(
                            f"Arrêt après échec lesson#{i}. "
                            f"Utilise --continue-on-error pour poursuivre."
                        )

            if sleep_between > 0 and i < lessons:
                time.sleep(sleep_between)

        self.stdout.write(self.style.SUCCESS(
            f"[{skill.upper()}] terminé — créées={created} échecs={failed}"
        ))
