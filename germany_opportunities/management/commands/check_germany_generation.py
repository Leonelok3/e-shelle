from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Exécute les générateurs allemands existants et rapporte chaque résultat (appels IA réels)."

    def handle(self, *args, **options):
        from germany_opportunities import tasks as opportunities
        from GermanPrepApp import tasks as learning
        from GermanPrepApp.models import GermanLesson, GermanPastExam
        failed = []
        tasks = (
            opportunities.fetch_ausbildung_offers,
            opportunities.enrich_offers_with_ai,
            learning.ensure_german_exam_catalog,
            learning.generate_german_learning_content,
            learning.generate_german_placement_questions,
            learning.generate_german_horen_audio,
            learning.generate_german_mock_exams,
            opportunities.clean_expired_germany,
        )
        for task in tasks:
            self.stdout.write(f"DÉBUT {task.name}")
            try:
                result = task.run()
                self.stdout.write(f"RÉSULTAT {task.name}: {result}")
                if isinstance(result, dict):
                    incomplete = bool(result.get("errors") or result.get("remaining_horen_without_audio"))
                    if task == learning.generate_german_placement_questions:
                        incomplete |= result["current"] + result["generated"] < result["target"]
                    if task == learning.generate_german_mock_exams:
                        for level in learning.GERMAN_LEVELS:
                            count = GermanPastExam.objects.filter(
                                exam__level=level, exam__exam_type=result["exam_type"],
                                title__startswith="Examen blanc IA", is_active=True,
                            ).count()
                            incomplete |= count < result["target_per_level"]
                    for request in result.get("generated_requests", []):
                        after = GermanLesson.objects.filter(exam__level=request["level"], exam__exam_type=result["exam_type"]).count()
                        incomplete |= after < request["before"] + request["requested"]
                    if incomplete:
                        raise RuntimeError("Génération partielle: consulter le résultat ci-dessus")
            except Exception as exc:
                failed.append(task.name)
                self.stderr.write(f"ÉCHEC {task.name}: {exc}")
        self.stdout.write("Bourses: import DAAD absent; contrôle des données existantes uniquement.")
        if failed:
            raise CommandError("Étapes en échec: " + ", ".join(failed))
        self.stdout.write(self.style.SUCCESS("Contrôle des générateurs existants terminé."))
