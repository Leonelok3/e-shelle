#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management command pour importer le curriculum de compréhension orale
depuis un fichier JSON vers les CourseLesson et CourseExercise.

Usage:
    python manage.py import_listening_curriculum --file ai_engine/learning_content/listening_curriculum_A1_fr.json
    python manage.py import_listening_curriculum --file <path> --level A1 --language fr --clear
"""

import json
import os
from pathlib import Path
from django.utils.text import slugify

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from preparation_tests.models import CourseLesson, CourseExercise


class Command(BaseCommand):
    help = "Importe un curriculum de compréhension orale dans CourseLesson & CourseExercise"

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
            help="Supprime les leçons existantes avant import",
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

        # Supprimer les leçons existantes si --clear
        if clear_existing:
            CourseLesson.objects.filter(level=level, locale=language).delete()
            self.stdout.write(self.style.WARNING(f"🗑️  Leçons existantes supprimées"))

        # Compteurs
        lesson_count = 0
        exercise_count = 0

        # Importer les leçons
        for lesson_data in data["lessons"]:
            lesson_number = lesson_data.get("lesson_number", 0)
            lesson_title = lesson_data.get("title", "")
            lesson_obj = lesson_data.get("objective", "")
            vocab_focus = lesson_data.get("vocabulary_focus", [])

            try:
                # Créer la leçon
                slug = slugify(f"{level}-lecon-{lesson_number}-{lesson_title}")
                
                # Générer un HTML simple pour le contenu
                content_html = f"""
                <h2>{lesson_title}</h2>
                <p><strong>Objectif:</strong> {lesson_obj}</p>
                <p><strong>Vocabulaire:</strong> {', '.join(vocab_focus)}</p>
                """

                lesson, created = CourseLesson.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "title": lesson_title,
                        "level": level,
                        "section": "co",  # Compréhension Orale
                        "locale": language,
                        "content_html": content_html,
                        "order": lesson_number,
                        "is_published": True,
                    },
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Leçon {lesson_number}: {lesson_title} créée"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Leçon {lesson_number}: {lesson_title} existante"
                        )
                    )

                lesson_count += 1

                # Importer les exercices
                exercises = lesson_data.get("exercises", [])

                for exercise_data in exercises:
                    try:
                        exercise_number = exercise_data.get("exercise_number", 0)
                        question_text = exercise_data.get("question", "")
                        audio_script = exercise_data.get("audio_script", "")
                        exercise_type = exercise_data.get("type", "multiple_choice")
                        options = exercise_data.get("options", {})
                        correct_answer = exercise_data.get("correct_answer", "")
                        explanation = exercise_data.get("explanation", "")
                        difficulty_prog = exercise_data.get("difficulty_progression", 5)

                        # Mapper les options A, B, C, D
                        # Gérer les exercices vrai/faux en les convertissant en A/B
                        if exercise_type == "vrai_faux":
                            option_a = "Vrai"
                            option_b = "Faux"
                            option_c = ""
                            option_d = ""
                            # Convertir la réponse "Vrai"/"Faux" en "A"/"B"
                            correct_answer = "A" if correct_answer == "Vrai" else "B"
                        else:
                            option_a = options.get("A", "")
                            option_b = options.get("B", "")
                            option_c = options.get("C", "")
                            option_d = options.get("D", "")

                        # Créer l'exercice
                        exercise, ex_created = CourseExercise.objects.get_or_create(
                            lesson=lesson,
                            title=f"Exercice {exercise_number}",
                            defaults={
                                "instruction": audio_script,
                                "question_text": question_text,
                                "option_a": option_a,
                                "option_b": option_b,
                                "option_c": option_c or "",
                                "option_d": option_d or "",
                                "correct_option": correct_answer,
                                "summary": explanation,
                                "order": exercise_number,
                                "is_active": True,
                            },
                        )

                        if ex_created:
                            exercise_count += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"    ❌ Erreur exercice {exercise_number}: {e}"
                            )
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"    📝 {len(exercises)} exercices importés pour leçon {lesson_number}"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Erreur leçon {lesson_number}: {e}"
                    )
                )

        # Résumé
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(f"📊 RÉSUMÉ DE L'IMPORT"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"✅ Leçons créées: {lesson_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Exercices créés: {exercise_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Niveau: {level} ({language})"))
        self.stdout.write(self.style.SUCCESS(f"✅ Section: Compréhension Orale"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                "\n🎯 Import réussi! Les leçons sont prêtes pour les examens.\n"
            )
        )
