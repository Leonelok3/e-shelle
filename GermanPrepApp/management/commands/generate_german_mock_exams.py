"""
Commande Django : génération d'examens blancs allemands.

Les sujets sont construits depuis les leçons et exercices déjà présents dans
GermanPrepApp, puis sauvegardés comme fichiers HTML téléchargeables via
GermanPastExam. Cette commande sert d'agent automatique quotidien: elle garde
au moins N examens blancs par niveau/examen sans dépendre d'un appel IA externe.

Usage :
    python manage.py generate_german_mock_exams
    python manage.py generate_german_mock_exams --level B1 --target 3 --questions 30
"""
from __future__ import annotations

import html
from collections import defaultdict

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from GermanPrepApp.models import GermanExam, GermanExercise, GermanPastExam


SKILL_ORDER = ["HOREN", "LESEN", "GRAMMATIK", "WORTSCHATZ", "SCHREIBEN", "SPRECHEN"]
SKILL_LABELS = {
    "HOREN": "Hören - Compréhension orale",
    "LESEN": "Lesen - Compréhension écrite",
    "GRAMMATIK": "Grammatik - Grammaire",
    "WORTSCHATZ": "Wortschatz - Vocabulaire",
    "SCHREIBEN": "Schreiben - Expression écrite",
    "SPRECHEN": "Sprechen - Expression orale",
}
GOETHE_DURATIONS = {
    "A1": "65 minutes",
    "A2": "80 minutes",
    "B1": "165 minutes",
    "B2": "180 minutes",
    "C1": "190 minutes",
    "C2": "200 minutes",
}


def _select_exercises(exam: GermanExam, limit: int) -> list[GermanExercise]:
    exercises = list(
        GermanExercise.objects.filter(lesson__exam=exam)
        .select_related("lesson", "lesson__exam")
        .order_by("lesson__skill", "lesson__order", "id")
    )
    if len(exercises) <= limit:
        return exercises

    buckets: dict[str, list[GermanExercise]] = defaultdict(list)
    for exercise in exercises:
        buckets[exercise.lesson.skill].append(exercise)

    selected: list[GermanExercise] = []
    per_skill = max(1, limit // max(1, len([s for s in SKILL_ORDER if buckets.get(s)])))
    for skill in SKILL_ORDER:
        selected.extend(buckets.get(skill, [])[:per_skill])

    if len(selected) < limit:
        selected_ids = {item.id for item in selected}
        selected.extend(item for item in exercises if item.id not in selected_ids)

    return selected[:limit]


def _render_mock_exam_html(exam: GermanExam, exercises: list[GermanExercise], number: int) -> str:
    generated_at = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
    title = f"Examen blanc {number} - {exam.title}"
    duration = GOETHE_DURATIONS.get(exam.level, "90 minutes")

    grouped: dict[str, list[GermanExercise]] = defaultdict(list)
    for exercise in exercises:
        grouped[exercise.lesson.skill].append(exercise)

    sections = []
    question_number = 1
    for skill in SKILL_ORDER:
        skill_exercises = grouped.get(skill, [])
        if not skill_exercises:
            continue

        rows = []
        for exercise in skill_exercises:
            rows.append(
                f"""
                <article class="question">
                  <h3>Question {question_number}</h3>
                  <p class="lesson">Leçon source: {html.escape(exercise.lesson.title)}</p>
                  <p>{html.escape(exercise.question_text)}</p>
                  <ol type="A">
                    <li>{html.escape(exercise.option_a)}</li>
                    <li>{html.escape(exercise.option_b)}</li>
                    <li>{html.escape(exercise.option_c)}</li>
                    <li>{html.escape(exercise.option_d)}</li>
                  </ol>
                </article>
                """
            )
            question_number += 1

        sections.append(
            f"""
            <section>
              <h2>{html.escape(SKILL_LABELS.get(skill, skill))}</h2>
              {''.join(rows)}
            </section>
            """
        )

    corrections = []
    for idx, exercise in enumerate(exercises, start=1):
        corrections.append(
            f"""
            <tr>
              <td>{idx}</td>
              <td>{html.escape(exercise.correct_option)}</td>
              <td>{html.escape(exercise.explanation or "Correction à revoir dans la leçon associée.")}</td>
            </tr>
            """
        )

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; line-height: 1.5; margin: 32px; }}
    header {{ border-bottom: 3px solid #ffce00; margin-bottom: 24px; padding-bottom: 16px; }}
    h1 {{ margin: 0 0 8px; color: #111827; }}
    h2 {{ margin-top: 28px; color: #102b4e; }}
    .meta {{ color: #475569; margin: 4px 0; }}
    .question {{ break-inside: avoid; border-bottom: 1px solid #e5e7eb; padding: 12px 0; }}
    .question h3 {{ margin-bottom: 4px; }}
    .lesson {{ color: #64748b; font-size: 13px; margin-top: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; vertical-align: top; }}
    th {{ background: #f8fafc; text-align: left; }}
    .page-break {{ break-before: page; margin-top: 36px; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p class="meta">Niveau: {html.escape(exam.level)} | Type: {html.escape(exam.get_exam_type_display())}</p>
    <p class="meta">Durée conseillée: {duration} | Questions: {len(exercises)}</p>
    <p class="meta">Généré automatiquement le {generated_at}</p>
  </header>
  <p><strong>Consigne:</strong> répondez sans consulter les corrections. Pour Hören, utilisez les audios disponibles dans les leçons correspondantes lorsque l'examen blanc renvoie vers une leçon orale.</p>
  {''.join(sections)}
  <section class="page-break">
    <h2>Corrigé</h2>
    <table>
      <thead><tr><th>Question</th><th>Réponse</th><th>Explication</th></tr></thead>
      <tbody>{''.join(corrections)}</tbody>
    </table>
  </section>
</body>
</html>
"""


class Command(BaseCommand):
    help = "Génère des examens blancs allemands téléchargeables depuis les exercices existants."

    def add_arguments(self, parser):
        parser.add_argument("--level", type=str, default=None, help="Filtrer par niveau CECR.")
        parser.add_argument("--exam_type", type=str, default="GOETHE", help="Type d'examen à traiter.")
        parser.add_argument("--target", type=int, default=2, help="Nombre minimal d'examens blancs par examen.")
        parser.add_argument("--questions", type=int, default=40, help="Nombre maximal de questions par sujet.")
        parser.add_argument("--replace", action="store_true", help="Supprimer les examens blancs IA existants avant génération.")
        parser.add_argument("--continue-on-error", action="store_true", help="Continuer si un examen échoue.")

    def handle(self, *args, **options):
        level = options["level"].upper() if options["level"] else None
        exam_type = options["exam_type"].upper()
        target = max(1, options["target"])
        questions = max(5, options["questions"])
        replace = options["replace"]
        continue_on_error = options["continue_on_error"]

        exams = GermanExam.objects.filter(is_active=True, exam_type=exam_type).order_by("level", "title")
        if level:
            exams = exams.filter(level=level)

        created = 0
        skipped = 0
        failed = 0

        for exam in exams:
            try:
                if replace:
                    exam.past_exams.filter(title__startswith="Examen blanc IA").delete()

                existing = exam.past_exams.filter(is_active=True, title__startswith="Examen blanc IA").count()
                if existing >= target:
                    skipped += 1
                    self.stdout.write(f"{exam.title}: {existing}/{target} examens blancs déjà prêts.")
                    continue

                exercises = _select_exercises(exam, questions)
                if len(exercises) < 5:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"{exam.title}: pas assez d'exercices ({len(exercises)})."))
                    continue

                for number in range(existing + 1, target + 1):
                    title = f"Examen blanc IA {number} - {exam.title}"
                    content = _render_mock_exam_html(exam, exercises, number)
                    filename = f"{slugify(title).lower()}.html"
                    past_exam = GermanPastExam.objects.create(exam=exam, title=title, is_active=True)
                    past_exam.file.save(filename, ContentFile(content.encode("utf-8")), save=True)
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"{exam.title}: créé {title}"))
            except Exception as exc:
                failed += 1
                if continue_on_error:
                    self.stdout.write(self.style.WARNING(f"{exam.title}: erreur {exc}"))
                else:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Examens blancs terminés: {created} créé(s), {skipped} ignoré(s), {failed} échec(s)."
            )
        )
