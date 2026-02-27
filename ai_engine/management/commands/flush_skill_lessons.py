"""
Commande Django : supprimer les leçons d'un skill (et leurs exercices) par niveau.

Usage :
    # Voir ce qui sera supprimé sans toucher la base
    python manage.py flush_skill_lessons --skill ce --dry-run

    # Supprimer tout le CE (tous niveaux)
    python manage.py flush_skill_lessons --skill ce

    # Supprimer uniquement CE A1
    python manage.py flush_skill_lessons --skill ce --level A1

    # Supprimer CO B2 (utile pour regénérer un niveau spécifique)
    python manage.py flush_skill_lessons --skill co --level B2
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Supprime les leçons (et exercices) d'un skill/niveau donné."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skill",
            type=str,
            required=True,
            choices=["co", "ce", "eo", "ee"],
            help="Skill à vider : co | ce | eo | ee",
        )
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Niveau CECR optionnel (A1/A2/B1/B2/C1/C2). Si absent, tous les niveaux.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche le nombre de leçons/exercices qui seraient supprimés sans toucher la base.",
        )

    def handle(self, *args, **options):
        from preparation_tests.models import CourseExercise, CourseLesson

        skill: str = options["skill"].lower()
        level: str | None = options["level"].upper() if options["level"] else None
        dry_run: bool = options["dry_run"]

        VALID_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
        if level and level not in VALID_LEVELS:
            raise CommandError(f"Niveau invalide : {level}. Choix : {', '.join(sorted(VALID_LEVELS))}")

        filters = {"section": skill}
        if level:
            filters["level"] = level

        lessons_qs = CourseLesson.objects.filter(**filters)
        lesson_count = lessons_qs.count()
        exercise_count = CourseExercise.objects.filter(lesson__in=lessons_qs).count()

        scope = f"skill={skill.upper()}" + (f" level={level}" if level else " (tous niveaux)")

        self.stdout.write(self.style.NOTICE(
            f"\n[FLUSH] {scope} — {lesson_count} leçons, {exercise_count} exercices"
        ))

        if lesson_count == 0:
            self.stdout.write(self.style.WARNING("  Aucune leçon trouvée. Rien à supprimer."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"  [DRY-RUN] {lesson_count} leçons et {exercise_count} exercices "
                f"seraient supprimés. Relance sans --dry-run pour confirmer."
            ))
            return

        # Confirmation implicite : la commande doit être lancée avec intention
        deleted_lessons, _ = lessons_qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ {deleted_lessons} leçons supprimées (exercices supprimés en cascade)."
        ))
