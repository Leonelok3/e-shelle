#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management command pour importer les examens de compréhension orale
depuis un fichier JSON vers les modèles Exam, ExamSection, Question, Choice, Explanation.

Usage:
    python manage.py import_exams --file ai_engine/learning_content/exams_listening_fr.json
    python manage.py import_exams --file <path> --level A1 --language fr --clear
"""

import json
import os
from pathlib import Path
from django.utils.text import slugify

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from preparation_tests.models import (
    Exam,
    ExamSection,
    Question,
    Choice,
    Explanation,
)


class Command(BaseCommand):
    help = "Importe les examens de compréhension orale dans Exam & ExamSection & Question"

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
            default="",
            help="Niveau CECRL spécifique (A1, A2, B1, B2, C1, C2) - vide = tous les niveaux",
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
            help="Supprime les examens existants avant import",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options["file"]
        level_filter = options["level"]
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
        if "exams" not in data or not isinstance(data["exams"], list):
            raise CommandError("❌ Structure JSON invalide: 'exams' manquant")

        # Supprimer les examens existants si --clear
        if clear_existing:
            if level_filter:
                Exam.objects.filter(code__contains=f"CO_{level_filter}").delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"🗑️  Examens {level_filter} existants supprimés"
                    )
                )
            else:
                Exam.objects.filter(code__startswith="CO_").delete()
                self.stdout.write(
                    self.style.WARNING(f"🗑️  Tous les examens CO supprimés")
                )

        # Compteurs
        exam_count = 0
        section_count = 0
        question_count = 0
        choice_count = 0

        # Importer les examens
        for exam_data in data["exams"]:
            exam_code = exam_data.get("exam_code", "")
            exam_name = exam_data.get("exam_name", "")
            exam_level = exam_data.get("level", "A1")
            exam_language = exam_data.get("language", language)
            description = exam_data.get("description", "")

            # Filtrer par niveau si spécifié
            if level_filter and exam_level != level_filter:
                continue

            try:
                # Créer l'examen
                exam, exam_created = Exam.objects.get_or_create(
                    code=exam_code,
                    defaults={
                        "name": exam_name,
                        "language": exam_language,
                        "description": description,
                    },
                )

                if exam_created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Examen: {exam_name} ({exam_code}) créé"
                        )
                    )
                    exam_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Examen: {exam_name} ({exam_code}) existant"
                        )
                    )

                # Importer les sections
                sections = exam_data.get("sections", [])

                for section_data in sections:
                    section_code = section_data.get("section_code", "co")
                    section_name = section_data.get("section_name", "")
                    section_order = section_data.get("order", 1)
                    duration_sec = section_data.get("duration_sec", 900)

                    try:
                        # Créer ou récupérer la section
                        section, sec_created = ExamSection.objects.get_or_create(
                            exam=exam,
                            code=section_code,
                            defaults={
                                "order": section_order,
                                "duration_sec": duration_sec,
                            },
                        )

                        if sec_created:
                            section_count += 1

                        # Importer les questions (parts = groupes de questions)
                        parts = section_data.get("parts", [])
                        part_question_start = 1

                        for part_data in parts:
                            part_number = part_data.get("part_number", 0)
                            part_title = part_data.get("part_title", "")
                            questions_list = part_data.get("questions", [])

                            for question_data in questions_list:
                                try:
                                    question_number = question_data.get(
                                        "question_number", 0
                                    )
                                    stem = question_data.get("stem", "")
                                    audio_script = question_data.get(
                                        "audio_script", ""
                                    )
                                    subtype = question_data.get("subtype", "mcq")
                                    difficulty = question_data.get("difficulty", 2)

                                    # Convertir difficulty numérique en string
                                    difficulty_map = {
                                        1: "easy",
                                        2: "medium",
                                        3: "hard",
                                        "easy": "easy",
                                        "medium": "medium",
                                        "hard": "hard",
                                    }
                                    difficulty = difficulty_map.get(
                                        difficulty, "medium"
                                    )

                                    # Créer la question
                                    question = Question.objects.create(
                                        section=section,
                                        stem=stem,
                                        subtype=subtype,
                                        difficulty=difficulty,
                                    )

                                    question_count += 1

                                    # Importer les choix
                                    choices = question_data.get("choices", [])

                                    for choice_data in choices:
                                        choice_text = choice_data.get("text", "")
                                        is_correct = choice_data.get(
                                            "is_correct", False
                                        )

                                        choice = Choice.objects.create(
                                            question=question,
                                            text=choice_text,
                                            is_correct=is_correct,
                                        )

                                        choice_count += 1

                                    # Importer l'explication si présente
                                    explanation_text = question_data.get(
                                        "explanation", ""
                                    )
                                    if explanation_text:
                                        Explanation.objects.get_or_create(
                                            question=question,
                                            defaults={
                                                "text_md": explanation_text
                                            },
                                        )

                                except Exception as e:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f"      ❌ Erreur question {question_number}: {e}"
                                        )
                                    )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"    📝 {len(questions_list)} questions importés pour section {section_code}"
                            )
                        )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ Erreur section {section_code}: {e}")
                        )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Erreur examen {exam_code}: {e}"))

        # Résumé
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS(f"📊 RÉSUMÉ DE L'IMPORT"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"✅ Examens créés: {exam_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Sections créées: {section_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Questions créées: {question_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Choix créés: {choice_count}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Langue: {language}"))
        if level_filter:
            self.stdout.write(self.style.SUCCESS(f"✅ Niveau: {level_filter}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            self.style.SUCCESS(
                "\n🎯 Import réussi! Les examens sont prêts pour les étudiants.\n"
            )
        )
