"""
Commande Django : importer des leçons depuis un fichier JSON (généré par ChatGPT).

Usage :
    python manage.py import_json_lessons --file /chemin/vers/eo_a1.json
    python manage.py import_json_lessons --file /chemin/vers/ee_b1.json --dry-run

Format JSON attendu :
    {
        "skill": "eo",          # eo | ee | co | ce
        "exam_id": 26,
        "level": "A1",
        "language": "fr",
        "lessons": [
            {
                "topic": "Les avantages de la vie en ville",
                "instructions": "Présentez votre opinion...",
                "expected_points": ["Transport", "Services", "Culture"]   # EO seulement
            },
            ...
        ]
    }

    Pour EE, chaque leçon contient :
        "topic", "instructions", "min_words" (int), "sample_answer" (str)
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Importe des leçons depuis un fichier JSON généré par ChatGPT."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier JSON à importer",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afficher ce qui serait inséré sans toucher la base",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continuer même si une leçon échoue",
        )
        # Overrides optionnels (priorité sur le fichier JSON)
        parser.add_argument("--exam_id", type=int, default=None)
        parser.add_argument("--level", type=str, default=None)
        parser.add_argument("--skill", type=str, default=None, choices=["co", "ce", "eo", "ee"])
        parser.add_argument("--language", type=str, default=None)

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        dry_run: bool = options["dry_run"]
        continue_on_error: bool = options["continue_on_error"]

        if not file_path.exists():
            raise CommandError(f"Fichier introuvable : {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON invalide : {e}")

        # Paramètres — override CLI > fichier JSON
        skill = (options.get("skill") or data.get("skill") or "").strip().lower()
        exam_id = options.get("exam_id") or data.get("exam_id")
        level = (options.get("level") or data.get("level") or "").strip().upper()
        language = (options.get("language") or data.get("language") or "fr").strip().lower()
        lessons = data.get("lessons", [])

        # Validations
        if not skill:
            raise CommandError("skill manquant (eo/ee/co/ce). Ajoute-le dans le JSON ou avec --skill.")
        if not exam_id:
            raise CommandError("exam_id manquant. Ajoute-le dans le JSON ou avec --exam_id.")
        if not level:
            raise CommandError("level manquant (A1/A2/B1/B2/C1/C2). Ajoute-le dans le JSON ou avec --level.")
        if not lessons:
            raise CommandError("Aucune leçon trouvée dans 'lessons'. Vérifie le format JSON.")

        # Récupérer l'inserter
        inserter_fn = self._get_inserter(skill)

        self.stdout.write(self.style.NOTICE(
            f"\n[IMPORT] skill={skill.upper()} exam_id={exam_id} level={level} "
            f"language={language} leçons={len(lessons)} dry_run={dry_run}"
        ))

        created = 0
        failed = 0

        for i, lesson_data in enumerate(lessons, start=1):
            try:
                if dry_run:
                    topic = lesson_data.get("topic", "(sans titre)")
                    self.stdout.write(self.style.WARNING(
                        f"  [DRY #{i}] topic='{topic[:60]}' clés={list(lesson_data.keys())}"
                    ))
                    created += 1
                    continue

                lesson_obj = inserter_fn(
                    exam_id=int(exam_id),
                    level=level,
                    language=language,
                    **{f"{skill}_data": lesson_data},
                    audio_path=None,
                )
                lesson_id = getattr(lesson_obj, "id", "?")
                topic = lesson_data.get("topic", "")[:60]
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ [{skill.upper()} #{i}] id={lesson_id} level={level} — {topic}"
                ))
                created += 1

            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(
                    f"  ❌ [{skill.upper()} #{i}] ERREUR : {exc}"
                ))
                if not dry_run:
                    self.stderr.write(traceback.format_exc())
                if not continue_on_error:
                    raise CommandError(
                        f"Arrêt à la leçon #{i}. Utilise --continue-on-error pour ignorer les erreurs."
                    )

        self.stdout.write(self.style.SUCCESS(
            f"\n[IMPORT] Terminé — insérées={created}  échecs={failed}"
        ))

    @staticmethod
    def _get_inserter(skill: str):
        skill = skill.lower()
        if skill == "co":
            from ai_engine.services.insertion_service import insert_co_content
            return insert_co_content
        if skill == "ce":
            from ai_engine.services.insertion_service import insert_ce_content
            return insert_ce_content
        if skill == "eo":
            from ai_engine.services.insertion_service import insert_eo_content
            return insert_eo_content
        if skill == "ee":
            from ai_engine.services.insertion_service import insert_ee_content
            return insert_ee_content
        raise CommandError(f"Skill inconnu : '{skill}'. Choix : co, ce, eo, ee.")
