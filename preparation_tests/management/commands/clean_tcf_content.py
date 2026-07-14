from __future__ import annotations

from django.core.management.base import BaseCommand
from preparation_tests.models import CourseLesson, Exam

class Command(BaseCommand):
    help = "Nettoie les doublons de leçons TCF (garde max 5 leçons par niveau et par section)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge-eo",
            action="store_true",
            help="Supprime toutes les leçons de la section EO (Expression Orale) pour les ré-générer proprement.",
        )
        parser.add_argument(
            "--purge-ee-c2",
            action="store_true",
            help="Supprime toutes les leçons du niveau C2 de la section EE (Expression Écrite) pour les ré-générer proprement.",
        )

    def handle(self, *args, **options):
        tcf_exam = Exam.objects.filter(code="tcf").first()
        if not tcf_exam:
            self.stdout.write("Aucun examen TCF trouvé.")
            return

        if options["purge_eo"]:
            lessons_to_delete = CourseLesson.objects.filter(exams=tcf_exam, section="eo")
            count = lessons_to_delete.count()
            for lesson in lessons_to_delete:
                lesson.exercises.all().delete()
                lesson.delete()
            self.stdout.write(self.style.SUCCESS(f"Purge réussie : {count} leçons EO supprimées."))

        if options["purge_ee_c2"]:
            lessons_to_delete = CourseLesson.objects.filter(exams=tcf_exam, section="ee", level="C2")
            count = lessons_to_delete.count()
            for lesson in lessons_to_delete:
                lesson.exercises.all().delete()
                lesson.delete()
            self.stdout.write(self.style.SUCCESS(f"Purge réussie : {count} leçons EE C2 supprimées."))

        sections = ["co", "ce", "ee", "eo"]
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]

        for section in sections:
            for level in levels:
                lessons = list(
                    CourseLesson.objects.filter(
                        exams=tcf_exam,
                        section=section,
                        level=level
                    ).order_by("id")
                )

                if len(lessons) > 5:
                    to_delete = lessons[5:]
                    self.stdout.write(
                        self.style.WARNING(
                            f"Niveau {level} ({section.upper()}) : {len(lessons)} leçons. Garde 5, suppression de {len(to_delete)} doublons..."
                        )
                    )
                    for l in to_delete:
                        l.exercises.all().delete()
                        l.delete()
                else:
                    missing = 5 - len(lessons)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Niveau {level} ({section.upper()}) : {len(lessons)}/5 leçons. (Manquant : {missing})"
                        )
                    )
