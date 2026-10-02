from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from preparation_tests.models import CourseExercise, CourseLesson, Exam, ExamSection
from preparation_tests.services.listening_material import seed_listening_explanation


LEVEL_THEMES = {
    "B2": [
        "télétravail et intégration professionnelle",
        "logement et installation au Canada",
        "formation continue et reconversion",
        "mobilité urbaine durable",
        "santé communautaire",
        "participation citoyenne",
        "services publics numériques",
        "entrepreneuriat immigrant",
        "conciliation famille-travail",
        "transport régional",
        "bénévolat et réseautage",
        "sécurité alimentaire",
    ],
    "C1": [
        "reconnaissance des diplômes",
        "intelligence artificielle au travail",
        "politiques d'intégration francophone",
        "transition écologique",
        "universités et recherche appliquée",
        "santé publique et prévention",
        "gouvernance des données",
        "médiation interculturelle",
        "emploi qualifié et productivité",
        "logement abordable",
        "financement de l'innovation",
        "participation démocratique",
    ],
    "C2": [
        "éthique algorithmique",
        "souveraineté linguistique",
        "diplomatie migratoire",
        "justice sociale et institutions",
        "mémoire collective",
        "innovation scientifique responsable",
        "philosophie du droit",
        "géopolitique de la francophonie",
        "épistémologie des sciences",
        "transmission culturelle",
        "régulation économique",
        "responsabilité environnementale",
    ],
}

SECTION_META = {
    "co": ("Compréhension orale", "CO"),
    "ce": ("Compréhension écrite", "CE"),
    "ee": ("Expression écrite", "EE"),
    "eo": ("Expression orale", "EO"),
}


class Command(BaseCommand):
    help = "Seed deterministic TCF B2/C1/C2 lessons and exercises for CO, CE, EE and EO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--levels",
            default="B2,C1,C2",
            help="Comma-separated CECR levels to seed. Default: B2,C1,C2.",
        )
        parser.add_argument(
            "--lessons-per-section",
            type=int,
            default=6,
            help="Lessons to create per section and level. Default: 6.",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=1,
            help="Batch number. Use 2, 3, ... to add new lessons without duplicating batch 1.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        levels = [level.strip().upper() for level in options["levels"].split(",") if level.strip()]
        lessons_per_section = max(1, int(options["lessons_per_section"]))
        batch = max(1, int(options["batch"]))
        exam = self._ensure_tcf_exam()
        self._attach_existing_french_lessons(exam)

        created_lessons = 0
        updated_lessons = 0
        created_exercises = 0
        updated_exercises = 0

        for level in levels:
            themes = LEVEL_THEMES.get(level)
            if not themes:
                self.stdout.write(self.style.WARNING(f"Niveau ignoré: {level}"))
                continue

            for section in ["co", "ce", "ee", "eo"]:
                selected_themes = self._themes_for_batch(themes, batch, lessons_per_section)
                for index, theme in enumerate(selected_themes, start=1):
                    lesson, was_created = self._upsert_lesson(exam, level, section, index, theme, batch)
                    created_lessons += int(was_created)
                    updated_lessons += int(not was_created)

                    count = 5 if section in ["co", "ce"] else 3
                    for order in range(1, count + 1):
                        _, ex_created = self._upsert_exercise(lesson, section, level, theme, order)
                        created_exercises += int(ex_created)
                        updated_exercises += int(not ex_created)

        self.stdout.write(
            self.style.SUCCESS(
                "TCF seed OK: "
                f"{created_lessons} leçons créées, {updated_lessons} mises a jour, "
                f"{created_exercises} exercices créés, {updated_exercises} mis a jour."
            )
        )

    def _ensure_tcf_exam(self) -> Exam:
        exam, _ = Exam.objects.update_or_create(
            code="tcf",
            defaults={
                "name": "TCF Canada",
                "language": "fr",
                "description": "Préparation TCF Canada: CO, CE, EE, EO et examens blancs.",
            },
        )
        durations = {"co": 2100, "ce": 3600, "ee": 3600, "eo": 720}
        for order, code in enumerate(["co", "ce", "ee", "eo"], start=1):
            ExamSection.objects.update_or_create(
                exam=exam,
                code=code,
                defaults={"order": order, "duration_sec": durations[code]},
            )
        return exam

    def _attach_existing_french_lessons(self, exam: Exam) -> None:
        lessons = CourseLesson.objects.filter(
            locale="fr",
            section__in=["co", "ce", "ee", "eo"],
            is_published=True,
        )
        for lesson in lessons.iterator():
            lesson.exams.add(exam)

    def _themes_for_batch(self, themes: list[str], batch: int, lessons_per_section: int) -> list[str]:
        offset = ((batch - 1) * lessons_per_section) % len(themes)
        return [themes[(offset + idx) % len(themes)] for idx in range(lessons_per_section)]

    def _upsert_lesson(self, exam: Exam, level: str, section: str, index: int, theme: str, batch: int):
        title_long, code = SECTION_META[section]
        prefix = "tcf-advanced" if batch == 1 else f"tcf-advanced-batch{batch}"
        slug = f"{prefix}-{section}-{level.lower()}-{index}"
        title = f"TCF {level} - {code} - {theme.title()}"
        content = self._lesson_content(level, section, theme)
        lesson, created = CourseLesson.objects.update_or_create(
            slug=slug,
            defaults={
                "exam": exam,
                "section": section,
                "level": level,
                "title": title,
                "locale": "fr",
                "content_html": content,
                "order": 800 + index,
                "is_published": True,
            },
        )
        lesson.exams.add(exam)
        return lesson, created

    def _lesson_content(self, level: str, section: str, theme: str) -> str:
        title_long, code = SECTION_META[section]
        if section == "co":
            body = (
                "Écoute active: repère d'abord la situation, puis l'opinion implicite, "
                "les connecteurs logiques et les nuances de certitude. En examen TCF, "
                "ne cherche pas à tout mémoriser: note mentalement qui parle, pourquoi, "
                "et quelle conséquence est annoncée."
            )
        elif section == "ce":
            body = (
                "Lecture efficace: commence par le titre et la conclusion, puis scanne "
                "les chiffres, concessions et reformulations. Les distracteurs du TCF "
                "reprennent souvent des mots du texte mais changent l'intention."
            )
        elif section == "ee":
            body = (
                "Production écrite: construis une réponse avec une thèse claire, deux "
                "arguments développés et une conclusion utile. Varie les connecteurs, "
                "précise les exemples et relis les accords."
            )
        else:
            body = (
                "Expression orale: annonce ton plan en une phrase, développe avec des "
                "exemples concrets, puis termine par une prise de position nette. La "
                "fluidité compte autant que la richesse lexicale."
            )
        return (
            f"<h2>{title_long} - niveau {level}</h2>"
            f"<p><strong>Thème:</strong> {theme}.</p>"
            f"<p>{body}</p>"
            "<ul>"
            "<li>Objectif: comprendre la consigne et repondre sous contrainte de temps.</li>"
            "<li>Méthode: identifier les mots-clés, l'intention et le piège principal.</li>"
            "<li>Évaluation: précision, cohérence, correction linguistique et niveau CECR.</li>"
            "</ul>"
        )

    def _upsert_exercise(self, lesson: CourseLesson, section: str, level: str, theme: str, order: int):
        # Never overwrite a validated document revision with the generic seed.
        protected = lesson.exercises.filter(order=order, is_active=True).exclude(document_text="").first()
        if protected:
            return protected, False
        if section == "co":
            data = self._co_data(level, theme, order)
        elif section == "ce":
            data = self._ce_data(level, theme, order)
        elif section == "ee":
            data = self._ee_data(level, theme, order)
        else:
            data = self._eo_data(level, theme, order)

        return CourseExercise.objects.update_or_create(
            lesson=lesson,
            order=order,
            defaults={
                "title": data["title"],
                "instruction": data["instruction"],
                "question_text": data["question_text"],
                "document_text": data["instruction"].split(":", 1)[1].strip() if section == "co" else "",
                "option_a": data["option_a"],
                "option_b": data["option_b"],
                "option_c": data.get("option_c", ""),
                "option_d": data.get("option_d", ""),
                "correct_option": data["correct_option"],
                "summary": data["summary"],
                "is_active": True,
            },
        )

    def _co_data(self, level: str, theme: str, order: int) -> dict:
        scripts = [
            (
                "Lors d'une réunion municipale, une responsable explique que le projet avance, "
                "mais que son acceptation dépendra surtout de la capacité à rassurer les habitants."
            ),
            (
                "Un conseiller d'orientation affirme que la formation courte n'est pas une solution "
                "miracle, même si elle facilite l'entrée dans certains secteurs en tension."
            ),
            (
                "Dans une chronique radio, l'intervenante reconnaît les coûts du programme, "
                "tout en soulignant que l'inaction serait plus coûteuse à long terme."
            ),
            (
                "Un employeur indique qu'il valorise l'expérience internationale, à condition que "
                "le candidat sache l'adapter aux normes professionnelles locales."
            ),
            (
                "Une étudiante explique que la difficulté principale n'est pas le volume de travail, "
                "mais la nécessité de justifier chaque opinion avec précision."
            ),
        ]
        correct = "B"
        return {
            "title": f"CO {level} - inférence {order}",
            "instruction": f"Script d'écoute ({theme}): {scripts[order - 1]}",
            "question_text": "Quelle idée principale faut-il retenir de cet extrait ?",
            "option_a": "La situation est simple et ne présente aucune tension.",
            "option_b": "La décision dépend d'une condition ou d'une nuance importante.",
            "option_c": "Le locuteur rejette totalement la proposition évoquée.",
            "option_d": "Le locuteur se limite à donner une information administrative.",
            "correct_option": correct,
            "summary": seed_listening_explanation(scripts[order - 1]),
        }

    def _ce_data(self, level: str, theme: str, order: int) -> dict:
        text = (
            f"Document {order} - {theme}. Une enquête récente montre que les usagers acceptent "
            "plus facilement une réforme lorsqu'elle est accompagnée d'explications concrètes, "
            "d'un calendrier réaliste et d'un mécanisme de recours. Les critiques ne portent pas "
            "sur l'objectif général, mais sur la transparence de la mise en œuvre."
        )
        return {
            "title": f"CE {level} - document {order}",
            "instruction": text,
            "question_text": "Selon le document, quel élément provoque surtout les réserves ?",
            "option_a": "Le refus de tout changement collectif.",
            "option_b": "L'absence de transparence dans l'application.",
            "option_c": "La disparition complète du calendrier.",
            "option_d": "Le manque d'intérêt pour le sujet.",
            "correct_option": "B",
            "summary": "Le texte précise que les critiques portent surtout sur la transparence de la mise en œuvre.",
        }

    def _ee_data(self, level: str, theme: str, order: int) -> dict:
        tasks = [
            "Rédigez un message argumenté à une association locale pour proposer une amélioration concrète.",
            "Écrivez un texte d'opinion en présentant deux arguments et un exemple personnel ou social.",
            "Rédigez une réponse formelle à une institution en défendant une position nuancée.",
        ]
        return {
            "title": f"EE {level} - production {order}",
            "instruction": (
                f"Thème: {theme}. Longueur conseillée: "
                f"{180 if level == 'B2' else 230 if level == 'C1' else 280} a "
                f"{230 if level == 'B2' else 300 if level == 'C1' else 360} mots. "
                "Structure attendue: introduction, arguments, exemple, conclusion."
            ),
            "question_text": tasks[(order - 1) % len(tasks)],
            "option_a": "Production libre",
            "option_b": "Correction IA",
            "correct_option": "A",
            "summary": "La correction IA doit évaluer la clarté, la cohérence, la richesse lexicale et la correction grammaticale.",
        }

    def _eo_data(self, level: str, theme: str, order: int) -> dict:
        tasks = [
            "Présentez votre point de vue sur cette situation et justifiez-le.",
            "Convainquez un interlocuteur sceptique en donnant des exemples précis.",
            "Comparez deux solutions possibles et choisissez la plus efficace.",
        ]
        expected = [
            "annoncer une position claire",
            "développer au moins deux arguments",
            "illustrer avec un exemple concret",
            "conclure avec une recommandation",
        ]
        return {
            "title": f"EO {level} - simulation {order}",
            "instruction": (
                f"Thème: {theme}. Préparation: 2 minutes. Réponse: "
                f"{2 if level == 'B2' else 3} a {3 if level == 'B2' else 4} minutes. "
                "Parlez de façon structurée et naturelle."
            ),
            "question_text": tasks[(order - 1) % len(tasks)],
            "option_a": "Production orale",
            "option_b": "Évaluation IA",
            "correct_option": "A",
            "summary": json.dumps(expected, ensure_ascii=False),
        }
