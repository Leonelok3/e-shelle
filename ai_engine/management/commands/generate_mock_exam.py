from __future__ import annotations

import time
import traceback

from django.core.management.base import BaseCommand, CommandError

SECTION_CHOICES = ("co", "ce", "eo", "ee")


class Command(BaseCommand):
    help = (
        "Génère des questions d'examen blanc (mock exam) type TEF/TCF/DELF "
        "et les insère dans ExamSection → Question → Choice."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam_code", type=str, required=True,
            help="Code de l'examen (ex: TEF, tcf, DELF)"
        )
        parser.add_argument(
            "--section", type=str, required=True, choices=SECTION_CHOICES,
            help="Section : co, ce, eo, ee"
        )
        parser.add_argument(
            "--level", type=str, default="B1",
            help="Niveau CECR : A1 A2 B1 B2 C1 C2"
        )
        parser.add_argument(
            "--language", type=str, default="fr",
            help="Langue (défaut: fr)"
        )
        parser.add_argument(
            "--batches", type=int, default=4,
            help="Nombre de batches de 5 questions (défaut: 4 → 20 questions)"
        )
        parser.add_argument(
            "--duration", type=int, default=3600,
            help="Durée de la section en secondes (défaut: 3600 = 60 min)"
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Simuler sans écrire en base"
        )
        parser.add_argument(
            "--continue-on-error", action="store_true",
            help="Continuer malgré les erreurs"
        )
        parser.add_argument(
            "--retries", type=int, default=2,
            help="Tentatives par batch"
        )
        parser.add_argument(
            "--sleep", type=float, default=1.0,
            help="Pause entre batches (secondes)"
        )

    def handle(self, *args, **options):
        from preparation_tests.models import (
            Choice, Exam, ExamSection, Explanation, Passage, Question,
        )
        from ai_engine.agents.mock_exam_agent import generate_mock_exam_questions

        exam_code = options["exam_code"].strip()
        section_code = options["section"].lower()
        level = options["level"].strip().upper()
        language = options["language"].strip().lower()
        batches = max(1, int(options["batches"]))
        duration = max(60, int(options["duration"]))
        dry_run = bool(options["dry_run"])
        continue_on_error = bool(options["continue_on_error"])
        retries = max(0, int(options["retries"]))
        sleep_between = max(0.0, float(options["sleep"]))

        # Récupérer l'examen
        try:
            exam = Exam.objects.get(code__iexact=exam_code)
        except Exam.DoesNotExist:
            raise CommandError(
                f"Exam '{exam_code}' introuvable. "
                f"Disponibles: {list(Exam.objects.values_list('code', flat=True))}"
            )

        self.stdout.write(self.style.NOTICE(
            f"[MOCK] exam={exam.code} section={section_code.upper()} "
            f"level={level} batches={batches} ({batches * 5} questions) "
            f"dry_run={dry_run}"
        ))

        # Créer ou récupérer la section
        if not dry_run:
            exam_section, created = ExamSection.objects.get_or_create(
                exam=exam,
                code=section_code,
                defaults={"order": {"co": 1, "ce": 2, "eo": 3, "ee": 4}.get(section_code, 1),
                          "duration_sec": duration},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  ExamSection créée: {exam.code} - {section_code.upper()} (id={exam_section.id})"
                ))
            else:
                self.stdout.write(f"  ExamSection existante: id={exam_section.id}")
        else:
            exam_section = None

        created_count = 0
        failed_count = 0

        for batch_num in range(1, batches + 1):
            attempt = 0
            ok = False

            while attempt <= retries and not ok:
                attempt += 1
                try:
                    result = generate_mock_exam_questions(
                        section=section_code,
                        level=level,
                        language=language,
                    )

                    questions_data = result.get("questions", [])
                    passage_text = result.get("passage", "")

                    if dry_run:
                        self.stdout.write(self.style.WARNING(
                            f"  [DRY] batch#{batch_num}/{batches} → "
                            f"{len(questions_data)} questions, passage={bool(passage_text)}"
                        ))
                        created_count += len(questions_data)
                        ok = True
                        continue

                    # Créer le passage si présent (CO et CE)
                    passage_obj = None
                    if passage_text.strip():
                        passage_obj = Passage.objects.create(
                            title=f"{exam.code} {section_code.upper()} {level} – batch {batch_num}",
                            text=passage_text,
                        )

                    for q_data in questions_data:
                        q = Question.objects.create(
                            section=exam_section,
                            stem=q_data["stem"],
                            passage=passage_obj,
                            asset=None,
                            subtype="mcq" if section_code in ("co", "ce") else "text",
                            difficulty=q_data.get("difficulty", "medium"),
                        )

                        for c_data in q_data.get("choices", []):
                            if not isinstance(c_data, dict):
                                continue
                            text = str(c_data.get("text", "")).strip()
                            if not text:
                                continue
                            Choice.objects.create(
                                question=q,
                                text=text,
                                is_correct=bool(c_data.get("is_correct", False)),
                            )

                        explanation_text = q_data.get("explanation", "").strip()
                        if explanation_text:
                            Explanation.objects.create(
                                question=q,
                                text_md=explanation_text,
                            )

                        created_count += 1

                    self.stdout.write(self.style.SUCCESS(
                        f"  batch#{batch_num}/{batches} → "
                        f"+{len(questions_data)} questions insérées"
                    ))
                    ok = True

                except Exception as exc:
                    failed_count += 1
                    self.stderr.write(self.style.ERROR(
                        f"  batch#{batch_num} attempt={attempt}/{retries + 1} failed: {exc}"
                    ))
                    self.stderr.write(traceback.format_exc())

                    if attempt <= retries:
                        time.sleep(2.0)
                    elif not continue_on_error:
                        raise CommandError(
                            f"Arrêt après échec batch#{batch_num}. "
                            f"Utilise --continue-on-error pour poursuivre."
                        )

            if sleep_between > 0 and batch_num < batches:
                time.sleep(sleep_between)

        self.stdout.write(self.style.SUCCESS(
            f"[MOCK] terminé — questions créées={created_count} échecs={failed_count}"
        ))

        if not dry_run and exam_section:
            total = Question.objects.filter(section=exam_section).count()
            self.stdout.write(self.style.SUCCESS(
                f"[MOCK] Total questions dans {exam.code} {section_code.upper()}: {total}"
            ))
