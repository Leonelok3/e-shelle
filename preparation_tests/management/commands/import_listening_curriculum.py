#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management command pour importer le curriculum de compréhension orale
depuis un fichier JSON vers la base de données Django.

Usage:
    python manage.py import_listening_curriculum --file ai_engine/learning_content/listening_curriculum_A1_fr.json
    python manage.py import_listening_curriculum --file <path> --level A1 --language fr
"""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from preparation_tests.models import (
    Exam,
    ExamSection,
    Passage,
    Question,
    Choice,
    Explanation,
    Asset,
)


class Command(BaseCommand):
    help = "Importe un curriculum de compréhension orale depuis un fichier JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin du fichier JSON à importer",
        )
        parser.add_argument(
            "--level",
            type=str,
            default="A1",
            help="Niveau CECRL (A1, A2, B1, B2, C1, C2)",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="fr",
            help="Code langue (fr, en, de, it)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime les données existantes avant import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"]
        level = options["level"]
        language = options["language"]
        clear_existing = options["clear"]

        # Valider le fichier
        if not os.path.exists(file_path):
            raise CommandError(f"❌ Fichier introuvable: {file_path}")

        if not file_path.endswith(".json"):
            raise CommandError("❌ Le fichier doit être au format JSON")

        # Charger le JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"❌ Erreur JSON: {e}")

        self.stdout.write(self.style.SUCCESS("✅ Fichier JSON chargé"))

        # Valider la structure
        if "lessons" not in data or not isinstance(data["lessons"], list):
            raise CommandError("❌ Structure JSON invalide: 'lessons' manquant")

        # Créer ou récupérer l'examen
        exam_code = f"listening_co_{level.lower()}_{language}"
        exam_name = f"Compréhension Orale {level}"

        if clear_existing:
            Exam.objects.filter(code=exam_code).delete()
            self.stdout.write(self.style.WARNING(f"🗑️  Données existantes supprimées"))

        exam, created = Exam.objects.get_or_create(
            code=exam_code,
            defaults={
                "name": exam_name,
                "language": language,
                "description": f"Curriculum de compréhension orale niveau {level} en {self._lang_name(language)}",
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Examen créé: {exam.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  Examen existant: {exam.name}"))

        # Créer la section Compréhension Orale
        section, _ = ExamSection.objects.get_or_create(
            exam=exam,
            code="co",
            defaults={"order": 1, "duration_sec": 1800},
        )
        self.stdout.write(
            self.style.SUCCESS(f"✅ Section créée: Compréhension Orale")
        )

        # Compteurs
        lesson_count = 0
        question_count = 0
        choice_count = 0

        # Importer les leçons
        for lesson_data in data["lessons"]:
            lesson_number = lesson_data.get("lesson_number", 0)
            lesson_title = lesson_data.get("title", "")

            # Créer un passage pour la leçon
            passage, _ = Passage.objects.get_or_create(
                title=f"Leçon {lesson_number}: {lesson_title}",
                defaults={"text": lesson_data.get("objective", "")},
            )

            exercises = lesson_data.get("exercises", [])

            for exercise_data in exercises:
                try:
                    # Créer la question
                    audio_script = exercise_data.get("audio_script", "")
                    question_text = exercise_data.get("question", "")

                    question = Question.objects.create(
                        section=section,
                        stem=question_text,
                        passage=passage,
                        subtype="mcq",
                        difficulty=self._map_difficulty(
                            exercise_data.get("difficulty_progression", 5)
                        ),
                    )

                    question_count += 1

                    # Ajouter les choix (options)
                    options = exercise_data.get("options", {})
                    correct_answer = exercise_data.get("correct_answer", "")

                    for option_key, option_text in options.items():
                        is_correct = option_key == correct_answer
                        Choice.objects.create(
                            question=question,
                            text=option_text,
                            is_correct=is_correct,
                        )
                        choice_count += 1

                    # Ajouter l'explication
                    explanation_text = exercise_data.get("explanation", "")
                    Explanation.objects.create(
                        question=question,
                        text_md=f"**Audio:** {audio_script}\n\n**Réponse:** {explanation_text}",
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Erreur Leçon {lesson_number}, Exercice {exercise_data.get('exercise_number')}: {e}"
                        )
                    )

            lesson_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ Leçon {lesson_number}: {len(exercises)} exercices importés"
                )
            )

        # Résumé
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(f"📊 RÉSUMÉ DE L'IMPORT"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"✅ Leçons: {lesson_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Questions: {question_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Choix: {choice_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Examen: {exam.name} ({exam.code})"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                "\n🎯 Import réussi! Le contenu est prêt pour la production.\n"
            )
        )

    @staticmethod
    def _map_difficulty(progression_value):
        """Map la difficulté (1-10) aux choix Django"""
        if progression_value <= 3:
            return "easy"
        elif progression_value <= 7:
            return "medium"
        else:
            return "hard"

    @staticmethod
    def _lang_name(lang_code):
        """Traduit les codes langue"""
        langs = {"fr": "Français", "en": "Anglais", "de": "Allemand", "it": "Italien"}
        return langs.get(lang_code, lang_code)
