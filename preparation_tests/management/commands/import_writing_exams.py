"""
Management command: import_writing_exams
Importe les exams Expression Écrite (EE) depuis JSON
"""

import json
from django.core.management.base import BaseCommand
from django.db import transaction
from exam.models import Exam, ExamSection, Passage, Question, Choice, Explanation


class Command(BaseCommand):
    help = "Importe les exams EE (Expression Écrite) depuis JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier JSON des exams EE",
        )
        parser.add_argument(
            "--level",
            type=str,
            default=None,
            help="Niveau de l'exam (A1-C2)",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="fr",
            help="Code langue (défaut: fr)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime les exams EE existants avant import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"]
        language = options["language"]
        clear = options["clear"]

        # Charger le JSON
        self.stdout.write("[IMPORT] Loading JSON file...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.stdout.write("[OK] JSON file loaded")
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"[ERROR] File not found: {file_path}"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("[ERROR] Invalid JSON format"))
            return

        # Supprimer les exams EE si demandé
        if clear:
            self.stdout.write("[ACTION] Clearing existing EE exams...")
            Exam.objects.filter(code__startswith="EE_").delete()
            self.stdout.write("[OK] EE exams cleared")

        exams_created = 0
        sections_created = 0
        passages_created = 0
        questions_created = 0
        choices_created = 0

        # Importer les exams
        exams_data = data.get("exams", [])
        for exam_data in exams_data:
            exam_code = exam_data.get("exam_code", f"EE_A1_FR")
            exam_name = exam_data.get("exam_name", f"Exam {exam_code}")
            level = exam_data.get("level", "A1").upper()
            section_code = exam_data.get("section_code", "ee")
            time_limit = exam_data.get("time_limit_minutes", 60)

            # Créer l'exam
            exam, created = Exam.objects.get_or_create(
                code=exam_code,
                defaults={
                    "name": exam_name,
                    "level_code": level,
                    "section_code": section_code,
                    "time_limit_minutes": time_limit,
                    "language": language,
                    "description": f"{exam_name} - {level}",
                },
            )

            status = "[OK]" if created else "[EXISTS]"
            self.stdout.write(f"  {status} Exam: {exam_name} ({exam_code})")
            exams_created += 1

            # Importer les sections
            sections_data = exam_data.get("sections", [])
            for section_data in sections_data:
                sec_code = section_data.get("section_code", "ee")
                sec_name = section_data.get("section_name", f"EE Section")
                instructions = section_data.get("instructions", "")

                # Créer la section
                exam_section, _ = ExamSection.objects.get_or_create(
                    exam=exam,
                    code=sec_code,
                    defaults={
                        "name": sec_name,
                        "instructions": instructions,
                        "description": instructions,
                    },
                )
                sections_created += 1

                # Importer les questions
                questions_data = section_data.get("questions", [])
                for q_idx, question_data in enumerate(questions_data):
                    q_num = question_data.get("question_number", q_idx + 1)
                    stem = question_data.get("stem", f"Question {q_num}")
                    q_type = question_data.get("question_type", "writing")
                    context = question_data.get("context_info", "")
                    expected = question_data.get("expected_output", "")

                    # Créer la question
                    question, _ = Question.objects.get_or_create(
                        exam_section=exam_section,
                        question_number=q_num,
                        defaults={
                            "stem": stem,
                            "question_type": q_type,
                            "context": context,
                            "section_code": sec_code,
                            "order": q_idx,
                        },
                    )
                    questions_created += 1

                    # Pour les exams écrits, créer une seule "choice" (réponse ouverte)
                    if q_type == "writing":
                        choice, _ = Choice.objects.get_or_create(
                            question=question,
                            choice_number=1,
                            defaults={
                                "text": expected or "Veuillez écrire votre réponse",
                                "is_correct": True,
                                "explanation": expected,
                            },
                        )
                        choices_created += 1

            self.stdout.write(
                f"    [IMPORT] {len(questions_data)} questions for {exam_name}"
            )

        # Résumé
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("[SUMMARY] EE Exams Import")
        self.stdout.write("=" * 60)
        self.stdout.write(f"[STAT] Exams created: {exams_created}")
        self.stdout.write(f"[STAT] Exam sections created: {sections_created}")
        self.stdout.write(f"[STAT] Passages created: {passages_created}")
        self.stdout.write(f"[STAT] Questions created: {questions_created}")
        self.stdout.write(f"[STAT] Choices created: {choices_created}")
        self.stdout.write(f"[STAT] Section: Expression Écrite (EE)")
        self.stdout.write(f"[STAT] Language: {language}")
        self.stdout.write("=" * 60)
        self.stdout.write("\n[SUCCESS] EE exams ready for students!")
